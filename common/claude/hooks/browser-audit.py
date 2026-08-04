#!/usr/bin/env python3
"""Session-isolated, privacy-preserving browser work ledger and hook gate."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


SCHEMA_VERSION = 1
DEFAULT_RETENTION_DAYS = 10
DATE_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:authorization|cookie|password|passwd|token|secret|api[_-]?key)\s*[:=]\s*\S+"),
    re.compile(r"\b(?:gh[pousr]_|github_pat_|xai-|sk-(?:proj-)?|hf_)[A-Za-z0-9_-]{10,}"),
)
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")


class AuditError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def root_path() -> Path:
    value = os.environ.get("CLX_BROWSER_AUDIT_ROOT")
    return Path(value).expanduser() if value else Path.home() / ".claude/browser-audit"


def ensure_root(root: Path) -> None:
    if root.is_symlink():
        raise AuditError(f"audit root must not be a symlink: {root}")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    active = root / ".active"
    if active.is_symlink():
        raise AuditError(f"active directory must not be a symlink: {active}")
    active.mkdir(mode=0o700, exist_ok=True)
    os.chmod(active, 0o700)
    index = root / "README.md"
    if not index.exists():
        content = (
            "# Browser audit runtime\n\n"
            "Local-only, privacy-preserving records live at "
            "`YYYY-MM-DD/<session-id>/<action-id>/`.\n"
            "Each action contains plan.json, events.jsonl, result.json, and ROLLBACK.md.\n"
            "URL queries/fragments, credentials, cookies, and response bodies are never logged.\n"
            "Non-symlink date directories older than 10 days are pruned automatically.\n"
        )
        try:
            private_write(index, content, exclusive=True)
        except FileExistsError:
            pass


def safe_id(value: str, label: str) -> str:
    if not SAFE_ID.fullmatch(value or ""):
        raise AuditError(f"invalid {label}: use 1-128 letters, numbers, dot, underscore, or hyphen")
    return value


def resolve_session(explicit: str | None = None, data: dict | None = None) -> str:
    candidates = [explicit]
    if isinstance(data, dict):
        candidates.extend(data.get(key) for key in ("session_id", "thread_id", "conversation_id"))
    candidates.extend(os.environ.get(key) for key in (
        "CLX_BROWSER_AUDIT_SESSION", "CODEX_THREAD_ID", "CLAUDE_SESSION_ID", "CMUX_SURFACE_ID"
    ))
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return safe_id(candidate.strip(), "session id")
    raise AuditError("browser work has no stable session id")


def sanitize_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "[invalid-url]"
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return value
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def sanitize_text(value: object, limit: int = 2000) -> str:
    text = str(value).replace("\x00", "")
    text = URL_PATTERN.sub(lambda match: sanitize_url(match.group(0)), text)
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text[:limit]


def private_write(path: Path, content: str, exclusive: bool = False) -> None:
    flags = os.O_WRONLY | os.O_CREAT | (os.O_EXCL if exclusive else os.O_TRUNC)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        os.write(fd, content.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def write_json(path: Path, value: dict, exclusive: bool = False) -> None:
    private_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n", exclusive)


def read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise AuditError(f"missing or unsafe audit file: {path}")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise AuditError(f"invalid audit object: {path}")
    return value


def append_event(action_dir: Path, event: str, **fields: object) -> None:
    value = {"timestamp": now_iso(), "event": event}
    value.update(fields)
    line = json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"
    path = action_dir / "events.jsonl"
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "a", encoding="utf-8", closefd=False) as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
            fcntl.flock(handle, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def active_path(root: Path, session: str) -> Path:
    return root / ".active" / f"{safe_id(session, 'session id')}.json"


def current_action(root: Path, session: str) -> tuple[Path, dict]:
    active = read_json(active_path(root, session))
    relative = active.get("action_dir")
    if not isinstance(relative, str):
        raise AuditError("active record has no action directory")
    action = root / relative
    resolved_root = root.resolve()
    try:
        resolved_action = action.resolve(strict=True)
    except FileNotFoundError as exc:
        raise AuditError("active action directory is missing") from exc
    if resolved_root not in resolved_action.parents or action.is_symlink():
        raise AuditError("active action escapes the audit root")
    return action, active


def prune(root: Path, days: int) -> list[str]:
    if days < 1:
        raise AuditError("retention days must be at least 1")
    ensure_root(root)
    cutoff = date.today() - timedelta(days=days)
    removed: list[str] = []
    for child in root.iterdir():
        if child.is_symlink() or not child.is_dir() or not DATE_DIR.fullmatch(child.name):
            continue
        try:
            day = date.fromisoformat(child.name)
        except ValueError:
            continue
        if day < cutoff:
            shutil.rmtree(child)
            removed.append(child.name)
    for marker in (root / ".active").glob("*.json"):
        try:
            active = read_json(marker)
            relative = active.get("action_dir", "")
            if not isinstance(relative, str) or not (root / relative).is_dir():
                marker.unlink()
        except (AuditError, OSError, json.JSONDecodeError):
            continue
    return removed


def begin(args: argparse.Namespace) -> None:
    root = root_path()
    ensure_root(root)
    prune(root, args.retention_days)
    session = resolve_session(args.session)
    marker = active_path(root, session)
    if marker.exists() or marker.is_symlink():
        raise AuditError("this session already has an active browser action; finish it first")
    action_id = datetime.now().strftime("%H%M%S") + "-" + secrets.token_hex(4)
    day = date.today().isoformat()
    action_dir = root / day / session / action_id
    action_dir.mkdir(mode=0o700, parents=True)
    plan = {
        "schema_version": SCHEMA_VERSION,
        "action_id": action_id,
        "session_id": session,
        "created_at": now_iso(),
        "state": "planned",
        "purpose": sanitize_text(args.purpose),
        "method": sanitize_text(args.method),
        "target": sanitize_text(args.target),
        "expected_change": sanitize_text(args.expected_change),
        "owned_resources": [sanitize_text(value) for value in args.owned_resource],
        "rollback_steps": [sanitize_text(value) for value in args.rollback_step],
        "verification": sanitize_text(args.verification),
        "retention_days": args.retention_days,
    }
    write_json(action_dir / "plan.json", plan, exclusive=True)
    rollback = "# Browser action rollback\n\n" + "\n".join(
        f"{index}. {step}" for index, step in enumerate(plan["rollback_steps"], 1)
    ) + f"\n\nVerification: {plan['verification']}\n"
    private_write(action_dir / "ROLLBACK.md", rollback, exclusive=True)
    append_event(action_dir, "plan_created", method=plan["method"], target=plan["target"])
    relative = str(action_dir.relative_to(root))
    write_json(marker, {"action_dir": relative, "action_id": action_id, "created_at": plan["created_at"]}, exclusive=True)
    print(json.dumps({"action_id": action_id, "action_dir": str(action_dir)}, ensure_ascii=False))


def finish(args: argparse.Namespace) -> None:
    root = root_path()
    ensure_root(root)
    session = resolve_session(args.session)
    action_dir, _ = current_action(root, session)
    result = {
        "schema_version": SCHEMA_VERSION,
        "action_id": read_json(action_dir / "plan.json")["action_id"],
        "session_id": session,
        "finished_at": now_iso(),
        "status": sanitize_text(args.status),
        "actual_change": sanitize_text(args.actual_change),
        "rollback_status": sanitize_text(args.rollback_status),
        "verification": sanitize_text(args.verification),
    }
    write_json(action_dir / "result.json", result, exclusive=True)
    append_event(action_dir, "finished", status=result["status"], rollback_status=result["rollback_status"])
    active_path(root, session).unlink()
    print(json.dumps({"action_dir": str(action_dir), "status": result["status"]}, ensure_ascii=False))


def note(args: argparse.Namespace) -> None:
    root = root_path()
    ensure_root(root)
    session = resolve_session(args.session)
    action_dir, _ = current_action(root, session)
    append_event(action_dir, "note", detail=sanitize_text(args.detail))


def canonical_digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_wrapper(path: Path, expected_sha_file: Path) -> dict:
    """Validate a browser wrapper by reading bytes only; never execute or source it."""
    if path.is_symlink() or not path.is_file():
        raise AuditError(f"wrapper must be a regular non-symlink file: {path}")
    mode = stat.S_IMODE(path.stat().st_mode)
    if not mode & 0o111:
        raise AuditError(f"wrapper is not executable: {path}")
    if mode & 0o022:
        raise AuditError(f"wrapper is group/world writable: {path}")
    if expected_sha_file.is_symlink() or not expected_sha_file.is_file():
        raise AuditError(f"expected SHA file is missing or unsafe: {expected_sha_file}")
    expected_match = re.match(r"^([0-9a-fA-F]{64})(?:\s|$)", expected_sha_file.read_text().strip())
    if not expected_match:
        raise AuditError("expected SHA file has no SHA-256 digest")
    source_bytes = path.read_bytes()
    actual = hashlib.sha256(source_bytes).hexdigest()
    expected = expected_match.group(1).lower()
    if actual != expected:
        raise AuditError(f"wrapper hash mismatch: expected {expected}, got {actual}")
    source = source_bytes.decode("utf-8", errors="replace")
    forbidden = re.search(
        r"osascript|\bpkill\b|\bkillall\b|REAL_PROFILE|\bln\s+-[^\n]*s|"
        r"Library/Application Support/Google/Chrome|--profile-directory",
        source,
        re.IGNORECASE,
    )
    if forbidden:
        raise AuditError(f"wrapper contains forbidden capability: {forbidden.group(0)}")
    if not re.search(r"(?:^|[;\n])\s*exit\s+125(?:\s|$)", source):
        raise AuditError("wrapper must fail closed with exit 125")
    return {"path": str(path), "sha256": actual, "mode": oct(mode), "execution_count": 0}


def command_head(command: str) -> str:
    segment = re.split(r"(?:&&|\|\||[;|\n])", command, maxsplit=1)[0].strip()
    try:
        import shlex
        tokens = shlex.split(segment)
    except ValueError:
        return ""
    while tokens and (re.fullmatch(r"[A-Za-z_]\w*=.*", tokens[0]) or Path(tokens[0]).name in {
        "env", "command", "noglob", "nocorrect", "timeout", "nohup"
    }):
        head = Path(tokens.pop(0)).name if tokens else ""
        if head in {"timeout"} and tokens and re.fullmatch(r"\d+(?:\.\d+)?[smh]?", tokens[0]):
            tokens.pop(0)
        while head == "env" and tokens and (tokens[0].startswith("-") or "=" in tokens[0]):
            tokens.pop(0)
    return Path(tokens[0]).name.lower() if tokens else ""


def classify_browser(data: dict) -> str | None:
    tool_name = str(data.get("tool_name", ""))
    lower = tool_name.lower()
    tool_input = data.get("tool_input")
    compact_input = json.dumps(tool_input, ensure_ascii=False, default=str).lower()
    if "claude-in-chrome" in lower or "google chrome" in compact_input and "computer-use" in lower:
        return "regular-chrome"
    if "browser" in lower or "playwright" in lower:
        return "isolated-browser"
    if "computer-use" in lower and any(word in compact_input for word in ("browser", "chromium")):
        return "isolated-browser"
    if lower not in {"bash", "shell", "exec_command"}:
        return None
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    if not isinstance(command, str):
        return None
    head = command_head(command)
    command_lower = command.lower()
    direct_chrome = head in {"google chrome", "chrome", "google-chrome", "chromium", "chromium-browser"}
    open_chrome = head == "open" and "google chrome" in command_lower
    if direct_chrome or open_chrome:
        if "--user-data-dir" not in command_lower or "library/application support/google/chrome" in command_lower:
            return "regular-chrome"
        return "isolated-browser"
    if head == "chrome-cdp":
        return "regular-chrome"
    if head in {"playwright", "browse"} or re.search(r"\b(?:npx|pnpm|yarn|bunx)\s+(?:exec\s+)?playwright\b", command_lower):
        return "isolated-browser"
    return None


def safe_target(tool_input: object) -> str:
    if not isinstance(tool_input, dict):
        return ""
    for key in ("url", "target", "uri", "path"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return sanitize_text(value, 500)
    return ""


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))


def hook(phase: str) -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    if not isinstance(data, dict):
        return
    classification = classify_browser(data)
    if classification is None:
        return
    try:
        session = resolve_session(data=data)
    except AuditError as exc:
        if phase == "pre":
            deny(f"browser-audit: blocked — {exc}; a stable per-session ledger is required")
        return
    root = root_path()
    ensure_root(root)
    try:
        action_dir, _ = current_action(root, session)
    except AuditError:
        if phase == "pre":
            deny(
                "browser-audit: blocked — create the detailed plan first with "
                f"browser-audit.py begin --session {session} ..."
            )
        return
    tool_name = sanitize_text(data.get("tool_name", ""), 300)
    tool_input = data.get("tool_input")
    if classification == "regular-chrome":
        append_event(action_dir, "tool_denied", tool=tool_name, reason="regular Chrome is immutable")
        if phase == "pre":
            deny("browser-audit: blocked — the user's regular Chrome/profile/session is immutable; use an isolated unsigned profile")
        return
    fields = {
        "tool": tool_name,
        "target": safe_target(tool_input),
        "input_sha256": canonical_digest(tool_input),
    }
    if phase == "pre":
        append_event(action_dir, "tool_pre", **fields)
    else:
        result = data.get("tool_result", data.get("tool_response"))
        append_event(
            action_dir,
            "tool_post",
            **fields,
            result_sha256=canonical_digest(result),
            is_error=bool(result.get("is_error")) if isinstance(result, dict) else False,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("begin")
    start.add_argument("--session")
    start.add_argument("--purpose", required=True)
    start.add_argument("--method", required=True)
    start.add_argument("--target", required=True)
    start.add_argument("--expected-change", required=True)
    start.add_argument("--owned-resource", action="append", default=[])
    start.add_argument("--rollback-step", action="append", required=True)
    start.add_argument("--verification", required=True)
    start.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS)
    done = sub.add_parser("finish")
    done.add_argument("--session")
    done.add_argument("--status", required=True, choices=("success", "failed", "aborted"))
    done.add_argument("--actual-change", required=True)
    done.add_argument("--rollback-status", required=True)
    done.add_argument("--verification", required=True)
    memo = sub.add_parser("note")
    memo.add_argument("--session")
    memo.add_argument("--detail", required=True)
    clean = sub.add_parser("prune")
    clean.add_argument("--days", type=int, default=DEFAULT_RETENTION_DAYS)
    wrapper = sub.add_parser("validate-wrapper")
    wrapper.add_argument("--path", type=Path, required=True)
    wrapper.add_argument("--expected-sha-file", type=Path, required=True)
    sub.add_parser("hook-pre")
    sub.add_parser("hook-post")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "begin":
            begin(args)
        elif args.command == "finish":
            finish(args)
        elif args.command == "note":
            note(args)
        elif args.command == "prune":
            print(json.dumps({"removed": prune(root_path(), args.days)}))
        elif args.command == "validate-wrapper":
            print(json.dumps(validate_wrapper(args.path, args.expected_sha_file)))
        elif args.command == "hook-pre":
            hook("pre")
        elif args.command == "hook-post":
            hook("post")
    except OSError as exc:
        # Still fail closed (rule 10: no browser action without an audit trail), but say why —
        # on this machine the usual cause is a full disk, not a policy denial.
        print(f"browser-audit: audit store unwritable ({exc}) — browser actions stay blocked "
              "until the ledger is writable (check disk space)", file=sys.stderr)
        return 2
    except (AuditError, json.JSONDecodeError) as exc:
        print(f"browser-audit: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
