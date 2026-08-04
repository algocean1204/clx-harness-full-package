#!/usr/bin/env python3
"""Codex UserPromptSubmit adapter for the shared one-core session intent."""

import json
import os
import sys

MAX_CORE_BYTES = 2560


GRANT_NOTE = ""     # set below; owner approvals must reach the model on this surface too


def emit(additional_context=None):
    if GRANT_NOTE:
        additional_context = (GRANT_NOTE + "\n\n" + additional_context
                              if additional_context else GRANT_NOTE)
    if not additional_context:
        print("{}")
        return
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": additional_context,
                }
            },
            ensure_ascii=False,
        )
    )


try:
    data = json.load(sys.stdin)
    if not isinstance(data, dict):
        raise ValueError

    claude_hooks = os.path.expanduser("~/.claude/hooks")
    sys.path.insert(0, claude_hooks)

    # Owner grant: this is Codex's UserPromptSubmit, the same trusted seam Claude uses, and the
    # guard it shares (~/.claude/hooks/guard-destructive.py) already consumes the ledger — so
    # minting must work here too, or the core rule would describe a flow this surface cannot do.
    try:
        from clx_grant import capture

        GRANT_NOTE = capture(data.get("prompt") or "")
    except Exception:
        GRANT_NOTE = ""

    from session_intent_paths import resolve

    _directory, core, _unused = resolve(hook_data=data)
    if not core:
        emit()
    elif not os.path.isfile(core):
        emit(
            f"SESSION-INTENT: no core yet — create {core} as <=1.5KB state-only "
            "workflow + session-only overrides + live State/DoD; keep it current and "
            "do not end while any DoD item is unmet"
        )
    else:
        with open(core, "rb") as handle:
            raw = handle.read(MAX_CORE_BYTES + 1)
        if len(raw) > MAX_CORE_BYTES:
            emit(
                f"SESSION-INTENT: {core} exceeds the 2.5KB injection budget — "
                "compress it before the routed step"
            )
        else:
            intent = raw.decode("utf-8").strip()
            emit(
                f"SESSION-INTENT core (this session → {core}; state-only; keep it current "
                f"when requirements change and read it before the routed step):\n{intent}"
                if intent
                else None
            )
except Exception:
    emit()
