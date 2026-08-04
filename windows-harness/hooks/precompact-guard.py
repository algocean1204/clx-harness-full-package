#!/usr/bin/env python3
"""PreCompact: inject importance-based double-pass compaction instructions.

Cross-platform port of precompact-guard.sh (macOS/Linux keep the .sh; Windows uses this).
Reads the hook JSON on stdin and, when this session has a session-intent core, appends it
verbatim to the MUST-KEEP set via the shared session_intent_paths helper (same dir).
"""
import json
import os
import sys

PASS1 = """COMPACTION GUARD (double-pass, fidelity over speed):
PASS 1 — extract MUST-KEEP verbatim before summarizing: (a) the active task spec incl.
locked quantities and enumerated items with completion state N/N, (b) user decisions and
approvals with their reasons, (c) exact file paths + key line refs touched this session,
(d) claims not yet verified (mark UNVERIFIED), (e) open blockers, (f) architecture/config
invariants established this session."""

PASS2 = """PASS 2 — re-scan the original once more: anything referenced later in the conversation but
missing from your summary gets added back. Prefer dropping process narration and raw tool
logs over specs, decisions, and numbers. Never compress away failures or corrections.
After compaction, treat recalled line numbers and old claims as stale — re-verify via
rg/Read before acting on them."""


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
        if not isinstance(data, dict):
            data = None
    except ValueError:
        data = None

    print(PASS1)

    core = sid = None
    if data is not None:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            from session_intent_paths import resolve_sid, _cli_value
            sid = resolve_sid(hook_data=data)
            core = _cli_value(sid, "core") if sid else None
        except Exception:
            core = sid = None

    if core and os.path.isfile(core) and os.path.getsize(core) > 0:
        print(f"(g) this session's session-intent lean core only (SID {sid}; path {core}; "
              f"never another SID) — keep verbatim:")
        with open(core, encoding="utf-8") as fh:
            print(fh.read())

    print(PASS2)


if __name__ == "__main__":
    main()
