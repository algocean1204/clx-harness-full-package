#!/usr/bin/env python3
"""Build an immutable, project-scoped Grok delegate home from curated skills."""

from __future__ import annotations

import argparse
import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from clx_host import require_posix  # noqa: E402

# fcntl does not exist on Windows; a bare import here died three frames deep with no
# hint that only THIS feature is unavailable.
require_posix('clx-grok-runtime.py')

import fcntl
import glob
import hashlib
import json
import os
import shutil
import stat
import tempfile
import uuid
from pathlib import Path
from typing import NoReturn

# tomllib is 3.11+, and this hook ships to machines whose python3 is the stock 3.9 — a bare import
# made it die with ImportError before it could report anything. The stub keeps every existing
# `except (..., tomllib.TOMLDecodeError)` intact and degrades to the same "config drifted" path.
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - depends on the host interpreter
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        import types

        _NoTomlError = type("TOMLDecodeError", (ValueError,), {})

        def _no_toml(_text):
            raise _NoTomlError("no TOML parser on this Python (needs 3.11 or tomli)")

        tomllib = types.SimpleNamespace(TOMLDecodeError=_NoTomlError, loads=_no_toml)


SNAPSHOT_FORMAT = b"2"
NATIVE_SKILLS = {
    "check-work",
    "code-review",
    "create-skill",
    "docx",
    "help",
    "imagine",
    "pptx",
    "xlsx",
}


def fail(message: str) -> NoReturn:
    raise SystemExit(f"clx-grok-runtime: {message}")


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    digest.update(SNAPSHOT_FORMAT)
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode()
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            fail(f"skill tree contains a symlink: {path}")
        if stat.S_ISDIR(info.st_mode):
            kind, data = b"d", b""
        elif stat.S_ISREG(info.st_mode):
            kind, data = b"f", path.read_bytes()
        else:
            fail(f"skill tree contains an unsupported entry: {path}")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(kind)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def normalized_tree_digest(root: Path, home: Path) -> str:
    digest = hashlib.sha256()
    prefix = str(home).encode()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode()
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            fail(f"native skill contains a symlink: {path}")
        if stat.S_ISDIR(info.st_mode):
            kind, data = b"d", b""
        elif stat.S_ISREG(info.st_mode):
            kind, data = b"f", path.read_bytes().replace(prefix, b"__GROK_HOME__")
        else:
            fail(f"native skill contains an unsupported entry: {path}")
        for value in (relative, kind, data):
            digest.update(len(value).to_bytes(8, "big"))
            digest.update(value)
    return digest.hexdigest()


def bundled_contract(root: Path, *, exact: bool) -> dict[str, object]:
    manifest_path = root / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_checksums = manifest["checksums"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        fail(f"bundled manifest is invalid: {root}")
    if set(manifest) != {"version", "checksums"} or not isinstance(manifest["version"], str) or not isinstance(manifest_checksums, dict):
        fail(f"bundled manifest schema drifted: {root}")
    for relative, expected_hash in manifest_checksums.items():
        if not isinstance(relative, str) or not isinstance(expected_hash, str) or len(expected_hash) != 64:
            fail(f"bundled checksum entry is invalid: {relative}")
    checksums = {
        relative: expected_hash
        for relative, expected_hash in manifest_checksums.items()
        if not relative.startswith("skills/")
    }
    expected = set(checksums)
    actual: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] == "skills":
            continue
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
            fail(f"bundled tree contains an unsupported entry: {path}")
        if stat.S_ISREG(info.st_mode) and path != manifest_path:
            actual.add(relative.as_posix())
    if exact and actual != expected:
        fail(f"bundled file set drifted: {root}")
    if not expected.issubset(actual):
        fail(f"bundled manifest references missing files: {root}")
    for relative, expected_hash in checksums.items():
        path = root / relative
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            fail(f"bundled checksum mismatch: {relative}")
    return {"version": manifest["version"], "checksums": checksums}


def merge_tree(source: Path, destination: Path) -> None:
    for path in sorted(source.rglob("*"), key=lambda item: item.relative_to(source).as_posix()):
        relative = path.relative_to(source)
        target = destination / relative
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            fail(f"session state contains a symlink: {path}")
        if stat.S_ISDIR(info.st_mode):
            target.mkdir(parents=True, exist_ok=True)
        elif stat.S_ISREG(info.st_mode):
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and target.read_bytes() != path.read_bytes():
                fail(f"session archive collision: {relative}")
            elif not target.exists():
                shutil.copy2(path, target)
        else:
            fail(f"session state contains an unsupported entry: {path}")


def merge_sessions(source: Path, destination: Path) -> None:
    for entry in source.iterdir():
        target = destination / entry.name
        if entry.name == "session_search.sqlite" and entry.is_file() and not entry.is_symlink():
            if not target.exists() or entry.stat().st_mtime_ns > target.stat().st_mtime_ns:
                shutil.copy2(entry, target)
            continue
        if entry.is_symlink() or not entry.is_dir() or not entry.name.startswith("%2F"):
            fail(f"unexpected session-root entry: {entry}")
        target.mkdir(parents=True, exist_ok=True)
        for child in entry.iterdir():
            child_target = target / child.name
            if child.name == "prompt_history.jsonl" and child.is_file() and not child.is_symlink():
                existing = child_target.read_text(encoding="utf-8").splitlines() if child_target.exists() else []
                for line in child.read_text(encoding="utf-8").splitlines():
                    if line not in existing:
                        existing.append(line)
                child_target.write_text("\n".join(existing) + "\n", encoding="utf-8")
                continue
            try:
                uuid.UUID(child.name)
            except (ValueError, AttributeError):
                fail(f"unexpected project-session entry: {child}")
            if child.is_symlink() or not child.is_dir():
                fail(f"invalid UUID session entry: {child}")
            child_target.mkdir(parents=True, exist_ok=True)
            merge_tree(child, child_target)


def validate_sessions_tree(root: Path) -> None:
    for entry in root.iterdir():
        if entry.name == "session_search.sqlite" and entry.is_file() and not entry.is_symlink():
            continue
        if entry.is_symlink() or not entry.is_dir() or not entry.name.startswith("%2F"):
            fail(f"unexpected stable session-root entry: {entry}")
        for child in entry.iterdir():
            if child.name == "prompt_history.jsonl" and child.is_file() and not child.is_symlink():
                continue
            try:
                uuid.UUID(child.name)
            except (ValueError, AttributeError):
                fail(f"unexpected stable project-session entry: {child}")
            if child.is_symlink() or not child.is_dir():
                fail(f"invalid stable UUID session entry: {child}")


def stabilize_sessions(runtime_parent: Path) -> Path:
    stable = runtime_parent / "state" / "sessions"
    stable.mkdir(parents=True, exist_ok=True)
    for generation in runtime_parent.iterdir():
        if not generation.is_dir() or len(generation.name) != 20:
            continue
        sessions = generation / "home" / ".grok" / "sessions"
        if sessions.is_symlink():
            if sessions.resolve(strict=True) != stable.resolve(strict=True):
                fail(f"runtime sessions link drifted: {generation}")
            continue
        if sessions.is_dir():
            merge_sessions(sessions, stable)
            shutil.rmtree(sessions)
        elif sessions.exists():
            fail(f"runtime sessions entry is invalid: {generation}")
        sessions.parent.mkdir(parents=True, exist_ok=True)
        sessions.symlink_to(stable, target_is_directory=True)
    validate_sessions_tree(stable)
    return stable


def validate_snapshot(
    root: Path,
    rows: list[tuple[str, Path, str]],
    expected_agent: str,
    expected_sandbox: bytes,
    expected_native: dict[str, str],
    expected_bundled: dict[str, object],
    stable_sessions: Path,
) -> None:
    ready = root / ".ready"
    if not ready.is_file() or ready.read_text(encoding="utf-8").strip() != root.name:
        fail(f"runtime snapshot is incomplete: {root}")
    grok_home = root / "home" / ".grok"
    try:
        runtime_config = tomllib.loads((grok_home / "config.toml").read_text(encoding="utf-8"))
        runtime_agent = Path(runtime_config["agent"]["definition"]).resolve(strict=True)
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError):
        fail(f"runtime configuration drifted: {root}")
    if runtime_agent != (grok_home / "agents" / "clx-delegate.md").resolve(strict=True):
        fail(f"runtime agent path escaped its immutable home: {root}")
    all_off = {"skills": False, "rules": False, "agents": False, "mcps": False, "hooks": False}
    expected_config = {
        "models": {"default": "grok-4.5"},
        "agent": {"definition": str(runtime_agent)},
        "sandbox": {"profile": "clx-delegate"},
        "compat": {"cursor": all_off, "claude": all_off},
        "marketplace": {
            "official_marketplace_auto_installed": True,
            "sources": [{"name": "xAI Official", "git": "https://github.com/xai-org/plugin-marketplace.git"}],
        },
        "mcp_servers": {
            "notion": {"url": "https://mcp.notion.com/mcp", "enabled": False},
            "figma": {"url": "https://mcp.figma.com/mcp", "enabled": False},
        },
    }
    runtime_marketplace = runtime_config.get("marketplace")
    if not isinstance(runtime_marketplace, dict):
        fail(f"runtime marketplace configuration drifted: {root}")
    if runtime_marketplace.pop("default_skills_installs_purged", None) not in (None, True):
        fail(f"runtime skill initialization marker drifted: {root}")
    if runtime_config != expected_config:
        fail(f"runtime isolation contract drifted: {root}")
    if runtime_agent.read_text(encoding="utf-8") != expected_agent:
        fail(f"runtime agent content drifted: {root}")
    if (grok_home / "sandbox.toml").read_bytes() != expected_sandbox:
        fail(f"runtime sandbox content drifted: {root}")
    expected_skills = {name for name, _source, _digest in rows}
    skills_root = grok_home / "skills"
    actual_skills = {path.name for path in skills_root.iterdir()}
    if actual_skills != expected_skills | set(expected_native):
        fail(f"runtime skill discovery set drifted: {root}")
    for name in actual_skills:
        skill = skills_root / name
        if skill.is_symlink() or not skill.is_dir() or not (skill / "SKILL.md").is_file():
            fail(f"runtime skill entry is invalid: {name}")
    for name, expected_hash in expected_native.items():
        if normalized_tree_digest(skills_root / name, grok_home) != expected_hash:
            fail(f"runtime native skill content drifted: {name}")
    if bundled_contract(grok_home / "bundled", exact=True) != expected_bundled:
        fail(f"runtime bundled contract drifted: {root}")
    agents = list((grok_home / "agents").iterdir())
    if len(agents) != 1 or agents[0].name != "clx-delegate.md" or agents[0].is_symlink():
        fail(f"runtime agent discovery set drifted: {root}")
    hooks = grok_home / "hooks"
    if (hooks.exists() or hooks.is_symlink()) and (
        hooks.is_symlink() or not hooks.is_dir() or any(hooks.iterdir())
    ):
        fail(f"runtime hooks directory is not empty: {root}")
    for forbidden in ("plugins", "rules", "commands", "installed-plugins", ".mcp.json", "mcp.json"):
        if (grok_home / forbidden).exists() or (grok_home / forbidden).is_symlink():
            fail(f"forbidden runtime discovery surface exists: {forbidden}")
    sessions = grok_home / "sessions"
    if not sessions.is_symlink() or sessions.resolve(strict=True) != stable_sessions.resolve(strict=True):
        fail(f"runtime sessions are not project-stable: {root}")
    for name, _source, expected in rows:
        skill = root / "home" / ".grok" / "skills" / name
        if not (skill / "SKILL.md").is_file() or tree_digest(skill) != expected:
            fail(f"runtime skill snapshot drifted: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("sandbox", type=Path)
    parser.add_argument("intent", type=Path)
    parser.add_argument("repo", type=Path)
    parser.add_argument("model_override", choices=("0", "1"))
    args = parser.parse_args()

    try:
        config_path = args.config.resolve(strict=True)
        sandbox_path = args.sandbox.resolve(strict=True)
        intent = args.intent.resolve(strict=True)
        repo = args.repo.resolve(strict=True)
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        sandbox = tomllib.loads(sandbox_path.read_text(encoding="utf-8"))
        agent_path = Path(config["agent"]["definition"]).resolve(strict=True)
        agent_text = agent_path.read_text(encoding="utf-8")
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        fail(f"configuration or path error: {exc}")

    if args.model_override == "0" and config.get("models", {}).get("default") != "grok-4.5":
        fail("grok-4.5 is not the configured default model")
    expected_lock = f"grok-repo:{repo}"
    try:
        lock_fd = int(os.environ["CLX_RESOURCE_LOCK_FD"])
        lock_info = os.fstat(lock_fd)
    except (KeyError, ValueError, OSError):
        fail("an inherited grok-repo lock fd is required")
    if os.environ.get("CLX_RESOURCE_LOCK_HELD") != expected_lock:
        fail("the canonical grok-repo lock is not held")
    lock_digest = hashlib.sha256(f"grok-repo\0{repo}".encode()).hexdigest()
    lock_path = Path(f"/tmp/cluxion-resource-locks-{os.getuid()}") / f"{lock_digest}.lock"
    try:
        expected_lock_info = lock_path.stat()
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, BlockingIOError):
        fail("the canonical grok-repo flock is unavailable")
    if (lock_info.st_dev, lock_info.st_ino) != (expected_lock_info.st_dev, expected_lock_info.st_ino):
        fail("the inherited grok-repo lock inode is invalid")
    profiles = sandbox.get("profiles", {})
    profile = profiles.get("clx-delegate")
    read_only_profile = profiles.get("clx-delegate-read-only")
    if not isinstance(profile, dict) or profile.get("extends") != "workspace":
        fail("clx-delegate sandbox profile drifted")
    try:
        denied = [Path(item).resolve(strict=True) for item in profile["deny"]]
    except (KeyError, OSError, TypeError):
        fail("clx-delegate deny path is invalid")
    if denied != [intent]:
        fail("clx-delegate deny path drifted")
    if not isinstance(read_only_profile, dict) or read_only_profile.get("extends") != "read-only":
        fail("clx-delegate read-only sandbox profile drifted")
    try:
        read_only_denied = [Path(item).resolve(strict=True) for item in read_only_profile["deny"]]
    except (KeyError, OSError, TypeError):
        fail("clx-delegate read-only deny path is invalid")
    if read_only_denied != [intent]:
        fail("clx-delegate read-only deny path drifted")
    if not all(
        phrase in agent_text
        for phrase in (
            "prompt_mode: minimal",
            "discover_skills: false",
            "Do not preload or enumerate skills",
            "Output Korean to the user",
            "No AI attribution",
        )
    ):
        fail("clx-delegate agent contract drifted")

    manifest_path = config_path.parent / "clx-skill-links.tsv"
    try:
        manifest_data = manifest_path.read_bytes()
        raw_rows = [line.split("\t") for line in manifest_data.decode().splitlines() if line]
    except (OSError, UnicodeError):
        fail("curated skill manifest is unreadable")
    if not raw_rows or any(len(row) != 2 for row in raw_rows):
        fail("curated skill manifest must contain valid rows")
    names = [row[0] for row in raw_rows]
    if len(set(names)) != len(names) or "clx-grok-call" in names:
        fail("curated skill names are duplicated or recursive")

    source_home = config_path.parent.parent
    live_skills = config_path.parent / "skills"
    rows: list[tuple[str, Path, str]] = []
    for name, relative in raw_rows:
        matches = [Path(item).resolve(strict=True) for item in glob.glob(str(source_home / relative))]
        if len(matches) != 1 or not (matches[0] / "SKILL.md").is_file():
            fail(f"skill source must resolve exactly once: {name}")
        source = matches[0]
        live = live_skills / name
        try:
            info = live.lstat()
        except OSError as exc:
            fail(f"curated link is missing: {name}: {exc}")
        if not stat.S_ISLNK(info.st_mode) or live.resolve(strict=True) != source:
            fail(f"curated link target drifted: {name}")
        rows.append((name, source, tree_digest(source)))

    native_sources: dict[str, tuple[Path, str]] = {}
    for name in NATIVE_SKILLS:
        source = live_skills / name
        if source.is_symlink() or not (source / "SKILL.md").is_file():
            fail(f"trusted Grok native skill is unavailable: {name}")
        native_sources[name] = (source, normalized_tree_digest(source, config_path.parent))
    bundled_source = config_path.parent / "bundled"
    expected_bundled = bundled_contract(bundled_source, exact=False)

    repo_key = hashlib.sha256(str(repo).encode()).hexdigest()[:12]
    runtime_parent = config_path.parent / "clx-delegates" / repo_key
    stable_sessions_path = runtime_parent / "state" / "sessions"
    runtime_sandbox_data = f'''[profiles.clx-delegate]
extends = "workspace"
read_write = [{json.dumps(str(stable_sessions_path))}]
deny = [{json.dumps(str(intent))}]

[profiles.clx-delegate-read-only]
extends = "read-only"
read_write = [{json.dumps(str(stable_sessions_path))}]
deny = [{json.dumps(str(intent))}]
'''.encode()

    digest = hashlib.sha256()
    for data in (
        config_path.read_bytes(),
        sandbox_path.read_bytes(),
        agent_text.encode(),
        manifest_data,
        str(repo).encode(),
        runtime_sandbox_data,
    ):
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    for name, source, content_hash in rows:
        for value in (name, str(source), content_hash):
            data = value.encode()
            digest.update(len(data).to_bytes(8, "big"))
            digest.update(data)
    for name, (source, content_hash) in sorted(native_sources.items()):
        for value in (name, str(source), content_hash):
            data = value.encode()
            digest.update(len(data).to_bytes(8, "big"))
            digest.update(data)
    bundled_data = json.dumps(expected_bundled, sort_keys=True, separators=(",", ":")).encode()
    digest.update(len(bundled_data).to_bytes(8, "big"))
    digest.update(bundled_data)
    key = digest.hexdigest()[:20]
    runtime = runtime_parent / key
    runtime_parent.mkdir(parents=True, exist_ok=True)
    build_lock = (runtime_parent / ".build.lock").open("a+b")
    os.chmod(runtime_parent / ".build.lock", 0o600)
    fcntl.flock(build_lock.fileno(), fcntl.LOCK_EX)
    for orphan in runtime_parent.glob(".*.tmp-*"):
        if orphan.is_symlink() or orphan.is_file():
            orphan.unlink()
        elif orphan.is_dir():
            shutil.rmtree(orphan)
    stable_sessions = stabilize_sessions(runtime_parent)

    if runtime.exists():
        validate_snapshot(
            runtime,
            rows,
            agent_text,
            runtime_sandbox_data,
            {name: content_hash for name, (_source, content_hash) in native_sources.items()},
            expected_bundled,
            stable_sessions,
        )
    else:
        temp = Path(tempfile.mkdtemp(prefix=f".{key}.tmp-", dir=runtime_parent))
        try:
            grok_home = temp / "home" / ".grok"
            skills = grok_home / "skills"
            agents = grok_home / "agents"
            skills.mkdir(parents=True)
            agents.mkdir()
            (grok_home / "sessions").symlink_to(stable_sessions, target_is_directory=True)
            for name, source, expected in rows:
                destination = skills / name
                shutil.copytree(source, destination, symlinks=False)
                if tree_digest(destination) != expected:
                    fail(f"skill changed while snapshotting: {name}")
            for name, (source, expected) in native_sources.items():
                destination = skills / name
                shutil.copytree(source, destination, symlinks=False)
                for copied in destination.rglob("*"):
                    if copied.is_file():
                        data = copied.read_bytes().replace(
                            str(config_path.parent).encode(),
                            str(runtime / "home" / ".grok").encode(),
                        )
                        copied.write_bytes(data)
                if normalized_tree_digest(destination, runtime / "home" / ".grok") != expected:
                    fail(f"native skill changed while snapshotting: {name}")
            bundled = grok_home / "bundled"
            bundled.mkdir()
            shutil.copy2(bundled_source / "manifest.json", bundled / "manifest.json")
            for relative in expected_bundled["checksums"]:
                source = bundled_source / relative
                destination = bundled / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            if bundled_contract(bundled, exact=True) != expected_bundled:
                fail("bundled content changed while snapshotting")
            copied_agent = agents / "clx-delegate.md"
            copied_agent.write_text(agent_text, encoding="utf-8")
            runtime_agent = runtime / "home" / ".grok" / "agents" / "clx-delegate.md"
            runtime_config = f'''[models]
default = "grok-4.5"

[agent]
definition = "{runtime_agent}"

[sandbox]
profile = "clx-delegate"

[compat.cursor]
skills = false
rules = false
agents = false
mcps = false
hooks = false

[compat.claude]
skills = false
rules = false
agents = false
mcps = false
hooks = false

[marketplace]
official_marketplace_auto_installed = true

[[marketplace.sources]]
name = "xAI Official"
git = "https://github.com/xai-org/plugin-marketplace.git"

[mcp_servers.notion]
url = "https://mcp.notion.com/mcp"
enabled = false

[mcp_servers.figma]
url = "https://mcp.figma.com/mcp"
enabled = false
'''
            (grok_home / "config.toml").write_text(runtime_config, encoding="utf-8")
            (grok_home / "sandbox.toml").write_bytes(runtime_sandbox_data)
            (temp / ".ready").write_text(key + "\n", encoding="utf-8")
            try:
                temp.rename(runtime)
            except FileExistsError:
                shutil.rmtree(temp)
                validate_snapshot(
                    runtime,
                    rows,
                    agent_text,
                    runtime_sandbox_data,
                    {name: content_hash for name, (_source, content_hash) in native_sources.items()},
                    expected_bundled,
                    stable_sessions,
                )
        except BaseException:
            if temp.exists():
                shutil.rmtree(temp)
            raise

    # Runtime generations are reproducible caches; retain only the current one so
    # obsolete snapshots cannot preserve dead temporary paths or stale behavior.
    completed = sorted(
        (
            path
            for path in runtime_parent.iterdir()
            if path.is_dir()
            and len(path.name) == 20
            and all(character in "0123456789abcdef" for character in path.name)
            and (path / ".ready").is_file()
        ),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    # ponytail: also keep the newest previous generation — an in-flight delegate may
    # still be running from it; per-generation refcounting is the upgrade if overlaps grow.
    newest_other = next((path for path in completed if path != runtime), None)
    retained = {runtime} | ({newest_other} if newest_other is not None else set())
    for stale in completed:
        if stale in retained:
            continue
        shutil.rmtree(stale)

    runtime_home = runtime / "home"
    print(f"{runtime_home}\t{key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
