#!/usr/bin/env python3
"""Keep Codex Desktop model picks consistent in config.toml.

Codex Desktop often writes only `model = "grok-composer-2.5-fast"` when the user
selects Composer in the picker. Without `model_provider = "grok_hermes"` the
ChatGPT backend returns HTTP 400. This hook patches config.toml on session start
and before prompt submit.

Default behavior: normal Codex Desktop sessions start on GPT. The merged catalog
stays available so the picker can still show Grok; only the provider/proxy are
swapped when a Grok model is explicitly selected.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

CONFIG = Path.home() / ".codex" / "config.toml"
CATALOG = Path.home() / ".codex" / "grok-hermes-catalog.json"
DEFAULT_MODEL = "gpt-5.6-sol"
STALE_GROK_SELECTION_SECONDS = 300

GROK_MODEL_PREFIXES = ("grok-", "xai-grok", "local-grok")
OPENAI_MODEL_PREFIXES = ("gpt-", "codex-", "o1", "o3", "o4")
GROK_PROVIDERS = {"grok_hermes", "xai"}
EXEC_SOURCES = {"exec"}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--default-openai",
        action="store_true",
        help="Reset stale Grok picker state to the default GPT model on session start.",
    )
    return parser.parse_args()


def _read_event() -> dict:
    if sys.stdin.isatty():
        return {}
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _event_value(event: dict, key: str) -> str | None:
    stack: list[dict] = [event]
    seen: set[int] = set()
    while stack:
        current = stack.pop()
        current_id = id(current)
        if current_id in seen:
            continue
        seen.add(current_id)
        value = current.get(key)
        if isinstance(value, str):
            return value
        for nested in current.values():
            if isinstance(nested, dict):
                stack.append(nested)
    return None


def _should_default_openai(args: argparse.Namespace, event: dict) -> bool:
    if not args.default_openai:
        return False
    if os.environ.get("CODEX_KEEP_GROK_DEFAULT") == "1":
        return False
    hook_event = _event_value(event, "hook_event_name")
    if hook_event and hook_event != "SessionStart":
        return False
    source = _event_value(event, "source")
    if source in EXEC_SOURCES:
        return False
    try:
        age_seconds = time.time() - CONFIG.stat().st_mtime
    except OSError:
        return False
    if age_seconds < STALE_GROK_SELECTION_SECONDS:
        return False
    return True


def _load_grok_slugs() -> set[str]:
    try:
        import json

        data = json.loads(CATALOG.read_text())
    except (OSError, json.JSONDecodeError):
        return set()
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        return set()
    slugs: set[str] = set()
    for model in models:
        if isinstance(model, dict) and model.get("provider") in {"grok_hermes", "xai"}:
            slug = model.get("slug")
            if isinstance(slug, str) and slug:
                slugs.add(slug)
    return slugs


def _catalog_preserves_default_fast_tier() -> bool:
    try:
        data = json.loads(CATALOG.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        return False
    for model in models:
        if not isinstance(model, dict) or model.get("slug") != DEFAULT_MODEL:
            continue
        speed_tiers = model.get("additional_speed_tiers")
        service_tiers = model.get("service_tiers")
        return (
            isinstance(speed_tiers, list)
            and "fast" in speed_tiers
            and isinstance(service_tiers, list)
            and any(
                isinstance(tier, dict) and tier.get("id") == "priority"
                for tier in service_tiers
            )
        )
    return False


def _is_grok_model(model: str, grok_slugs: set[str]) -> bool:
    if model in grok_slugs:
        return True
    return any(model.startswith(prefix) for prefix in GROK_MODEL_PREFIXES)


def _is_openai_model(model: str) -> bool:
    return any(model.startswith(prefix) for prefix in OPENAI_MODEL_PREFIXES)


def _get_model(text: str) -> str | None:
    match = re.search(r'^model\s*=\s*"([^"]+)"\s*$', text, re.MULTILINE)
    return match.group(1) if match else None


def _upsert_line(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf'^{re.escape(key)}\s*=.*$', re.MULTILINE)
    line = f'{key} = "{value}"'
    if pattern.search(text):
        return pattern.sub(line, text, count=1)
    # Insert after the first `model = ...` line when possible.
    model_match = re.search(r'^model\s*=.*$', text, re.MULTILINE)
    if model_match:
        insert_at = model_match.end()
        return text[:insert_at] + "\n" + line + text[insert_at:]
    return line + "\n" + text


def _remove_line(text: str, key: str) -> str:
    pattern = re.compile(rf'^{re.escape(key)}\s*=.*\n?', re.MULTILINE)
    return pattern.sub("", text)


def _get_value(text: str, key: str) -> str | None:
    match = re.search(rf'^{re.escape(key)}\s*=\s*"([^"]+)"\s*$', text, re.MULTILINE)
    return match.group(1) if match else None


def main() -> int:
    args = _parse_args()
    event = _read_event()

    if not CONFIG.exists():
        return 0

    original = CONFIG.read_text()
    text = original
    model = _get_model(text)
    if not model:
        return 0

    grok_slugs = _load_grok_slugs()
    changed = False

    if _is_grok_model(model, grok_slugs) and _should_default_openai(args, event):
        text = _upsert_line(text, "model", DEFAULT_MODEL)
        model = DEFAULT_MODEL
        changed = True

    if _is_grok_model(model, grok_slugs):
        # --- Grok model active: set up Grok proxy chain ---
        if _get_value(text, "model_provider") != "grok_hermes":
            text = _upsert_line(text, "model_provider", "grok_hermes")
            changed = True
        catalog_path = str(CATALOG)
        if _get_value(text, "model_catalog_json") != catalog_path:
            text = _upsert_line(text, "model_catalog_json", catalog_path)
            changed = True

    elif _is_openai_model(model):
        # --- OpenAI model active: keep OpenAI inference, keep merged picker list ---
        # The desktop proxy only injects custom model rows into /codex/models and
        # forwards the rest; model_provider keeps GPT requests on OpenAI.
        if _get_value(text, "model_provider") != "openai":
            text = _upsert_line(text, "model_provider", "openai")
            changed = True
        # Keep the merged picker catalog so Grok remains selectable, but only
        # when it preserves GPT Fast tier metadata. Otherwise Codex hides /fast.
        catalog_path = str(CATALOG)
        if _catalog_preserves_default_fast_tier():
            if _get_value(text, "model_catalog_json") != catalog_path:
                text = _upsert_line(text, "model_catalog_json", catalog_path)
                changed = True
        elif _get_value(text, "model_catalog_json") == catalog_path:
            text = _remove_line(text, "model_catalog_json")
            changed = True

    if changed and text != original:
        CONFIG.write_text(text)
        sys.stderr.write(
            f"[sync-grok-model-config] patched {CONFIG} for model={model}\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
