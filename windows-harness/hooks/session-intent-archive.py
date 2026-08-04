#!/usr/bin/env python3
"""SessionEnd: archive this logical session's intent core into forgetforge.

Cross-platform port of session-intent-archive.sh (macOS/Linux keep the .sh; Windows uses this).
No-op when forgetforge (the memory plugin CLI) is not installed — which is the case for a
clean distribution, so this hook is inert until you add that plugin. Never deletes the core.
"""
import json
import os
import subprocess
import sys
from shutil import which


def main() -> None:
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            return
    except (ValueError, AttributeError):
        return

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from session_intent_paths import resolve_sid, _cli_value
    except Exception:
        return

    sid = resolve_sid(hook_data=data)
    if not sid:
        return
    core = _cli_value(sid, "core")
    if not core or not os.path.isfile(core) or os.path.getsize(core) == 0:
        return
    if not which("forgetforge"):
        return  # memory plugin not installed — nothing to archive

    try:
        subprocess.run(
            ["forgetforge", "store", f"session-intent-{sid}", "--content-file", core,
             "--importance", "0.6", "--node-type", "session", "--session-id", sid,
             "--expire-days", "90"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        # Keep the intent-patterns ledger's mistake nodes fresh (idempotent; fail-open).
        sync = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forgetforge-sync.py")
        if os.path.isfile(sync):
            subprocess.run([sys.executable, sync],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except OSError:
        pass


if __name__ == "__main__":
    main()
