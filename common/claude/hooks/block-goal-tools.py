#!/usr/bin/env python3
"""Block create_goal/update_goal so agents cannot set token budgets."""

from __future__ import annotations

import json
import sys

BLOCKED = frozenset({"create_goal", "update_goal"})
MESSAGE = (
    "Blocked by ~/.claude/hooks/block-goal-tools.py: create_goal and update_goal are "
    "disabled globally. User policy is unlimited tokens. Continue the task directly "
    "without goal tools. User manages goals via Claude Code (/goal, /ralph-loop). Hook: ~/.claude/hooks/block-goal-tools.py"
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print("{}", file=sys.stdout)
        return 0

    if not isinstance(payload, dict):  # valid JSON but not an object (null/list/number) → fail safe
        print("{}", file=sys.stdout)
        return 0

    tool_name = str(payload.get("tool_name", ""))
    if tool_name not in BLOCKED:
        print("{}", file=sys.stdout)
        return 0

    hook_event = payload.get("hook_event_name", "PreToolUse")
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": hook_event,
                    "permissionDecision": "deny",
                },
                "systemMessage": MESSAGE,
            }
        ),
        file=sys.stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
