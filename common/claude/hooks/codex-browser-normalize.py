#!/usr/bin/env python3
"""Put ~/.codex/config.toml back to the isolated in-app browser after a `codex exec` run.

Measured cause, not a guess: config.toml's mtime tracks each `codex exec`, and after every run
`BROWSER_USE_AVAILABLE_BACKENDS` is back to "chrome,iab" with the CHROME instruction line
restored. Core rule 10 forbids automating the user's real Chrome, so the setting has to come back
to "iab" or config-doctor fails and — worse — a later session inherits a Chrome-capable Codex.

Idempotent, exit 0 when nothing needed changing. Touches ONLY those two settings; every other
line, including comments, is written back byte-for-byte.
"""
import os
import sys

PATH = os.path.expanduser("~/.codex/config.toml")
BAD = 'BROWSER_USE_AVAILABLE_BACKENDS = "chrome,iab"'
GOOD = 'BROWSER_USE_AVAILABLE_BACKENDS = "iab"'
DROP = "NODE_REPL_INSTRUCTIONS_USE_CASE_CHROME"


def main():
    if not os.path.isfile(PATH):
        print("codex-browser-normalize: no ~/.codex/config.toml — nothing to do")
        return 0
    try:
        with open(PATH, encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError as exc:
        print(f"codex-browser-normalize: cannot read config ({exc})", file=sys.stderr)
        return 2

    out, fixed, dropped = [], 0, 0
    for line in lines:
        if line.startswith(DROP):
            dropped += 1
            continue
        if BAD in line:
            out.append(line.replace('"chrome,iab"', '"iab"'))
            fixed += 1
            continue
        out.append(line)

    if not fixed and not dropped:
        print("codex-browser-normalize: already isolated (iab)")
        return 0
    tmp = PATH + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.writelines(out)
        os.replace(tmp, PATH)
    except OSError as exc:
        print(f"codex-browser-normalize: cannot write config ({exc})", file=sys.stderr)
        return 2
    print(f"codex-browser-normalize: backends→iab ×{fixed}, chrome instruction dropped ×{dropped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
