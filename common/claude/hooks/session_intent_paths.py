#!/usr/bin/env python3
"""Single source of truth for per-logical-session SESSION_INTENT paths.

Key = full UUID session_id (hook payload preferred). Fallback: UUID basename of
transcript_path only. No cwd/hash/unknown/short-UUID/shared-seed keying.

Resume may reuse the same session_id, so UUID directories under ROOT are retained
as small recovery state (SessionEnd archives into forgetforge but does not delete
or GC the on-disk core). cwd-keyed and _legacy* dirs are recovery-only.

CLI:
  python3 session_intent_paths.py --session-id UUID [core|detail|dir|sid]
  python3 session_intent_paths.py --transcript PATH [core|detail|dir|sid]
  printf '%s' '{"session_id":"..."}' | python3 session_intent_paths.py --from-stdin [core|detail|dir|sid]

``detail`` remains a backward-compatible selector but intentionally prints an
empty value: one logical session has exactly one canonical state file, core.md.

Prints the path (or sid) on success; empty stdout when no valid SID (exit 0).
"""
import json
import os
import re
import sys

ROOT = os.path.expanduser("~/.claude/session-intent")
LEGACY = os.path.expanduser("~/.claude/SESSION_INTENT.md")
LEGACY_DETAIL = os.path.expanduser("~/.claude/SESSION_DETAIL.md")

# Full UUID only (8-4-4-4-12). Short fragments and "unknown" never key a path.
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)


def is_full_uuid(s):
    return bool(s and isinstance(s, str) and UUID_RE.match(s.strip()))


def sid_from_transcript(path):
    """Return only a UUID transcript basename (after stripping one extension)."""
    if not path or not isinstance(path, str):
        return None
    path = path.rstrip("/")
    base = os.path.basename(path)
    stem = base.rsplit(".", 1)[0] if "." in base else base
    if is_full_uuid(stem):
        return stem.strip().lower()
    return None


def resolve_sid(session_id=None, transcript_path=None, hook_data=None):
    """Return a validated full UUID, or None. Prefer session_id over transcript."""
    if isinstance(hook_data, dict):
        if session_id is None:
            session_id = hook_data.get("session_id")
        if transcript_path is None:
            transcript_path = hook_data.get("transcript_path")
    if is_full_uuid(session_id):
        return session_id.strip().lower()
    return sid_from_transcript(transcript_path)


def resolve(session_id=None, transcript_path=None, hook_data=None):
    """Return (dir, core.md, None) or (None, None, None) if no valid SID."""
    sid = resolve_sid(session_id, transcript_path, hook_data)
    if not sid:
        return None, None, None
    d = os.path.join(ROOT, sid)
    return d, os.path.join(d, "core.md"), None


def _cli_which(args):
    for a in args:
        if a in ("core", "detail", "dir", "sid"):
            return a
    return "core"


def _cli_value(sid, which):
    if not sid:
        return ""
    d = os.path.join(ROOT, sid)
    return {
        "sid": sid,
        "dir": d,
        "core": os.path.join(d, "core.md"),
        "detail": "",
    }.get(which, os.path.join(d, "core.md"))


if __name__ == "__main__":
    argv = sys.argv[1:]
    which = _cli_which(argv)
    session_id = None
    transcript_path = None
    hook_data = None

    if "--from-stdin" in argv:
        try:
            hook_data = json.load(sys.stdin)
            if not isinstance(hook_data, dict):
                hook_data = None
        except Exception:
            hook_data = None
    if "--session-id" in argv:
        i = argv.index("--session-id")
        if i + 1 < len(argv):
            session_id = argv[i + 1]
    if "--transcript" in argv:
        i = argv.index("--transcript")
        if i + 1 < len(argv):
            transcript_path = argv[i + 1]

    # Backward-compat: bare first arg that looks like a full UUID is treated as SID
    # (not a cwd — cwd keying is deliberately gone).
    positional = [
        a for a in argv
        if not a.startswith("-") and a not in ("core", "detail", "dir", "sid")
        and a != session_id and a != transcript_path
    ]
    if session_id is None and positional and is_full_uuid(positional[0]):
        session_id = positional[0]

    sid = resolve_sid(session_id, transcript_path, hook_data)
    sys.stdout.write(_cli_value(sid, which))
