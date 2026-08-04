#!/usr/bin/env python3
"""SessionStart(source=compact): deterministically restore what compaction may have dropped.

PreCompact only ASKS the summarizer to keep the session core verbatim — instruction-based,
so a summary can silently lose it. This hook runs right after compaction and re-states the
session-intent core plus any owner standing block whose marker is missing, based on a string
check rather than a judgment. Other SessionStart sources (startup/resume) get nothing: the
normal per-prompt injection already covers them.

Fail-open: any error exits 0 with no output.
"""
import json
import os
import sys


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(data, dict) or data.get("source") != "compact":
        return 0

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    core_text = ""
    # Assemble everything in memory and emit ONCE: a failure half-way through must leave no
    # partial owner context on stdout (fail-open means no output, not some output).
    out = []
    try:
        from session_intent_paths import resolve

        _d, core, _u = resolve(hook_data=data)
        if (core and not os.path.islink(core) and os.path.isfile(core)
                and os.path.getsize(core) <= 400_000):
            with open(core, encoding="utf-8-sig") as fh:
                core_text = fh.read(400_000).strip()
            if core_text:
                out.append(
                    "POST-COMPACTION RESTORE — session-intent core re-stated verbatim "
                    f"(source {core}); treat the summary as lossy where it disagrees:"
                )
                out.append(core_text)
                out.append("")
    except Exception:
        core_text, out = "", []

    try:
        import standing_blocks

        text = standing_blocks.render(
            standing_blocks.missing_from(core_text),
            "OWNER STANDING CONTEXT restored after compaction (private):",
        )
        sid = data.get("session_id") or ""
        if text:
            out.append(text)
            # re-arm so the NEXT prompt does not repeat what this restore just put back
            standing_blocks.clear_sent(sid)
            standing_blocks.mark_sent(sid)
        else:
            standing_blocks.clear_sent(sid)
    except Exception:
        pass

    if out:
        sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
