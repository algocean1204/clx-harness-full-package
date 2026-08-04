#!/usr/bin/env python3
"""statusLine: model | cwd | context% | ponytail badge.

Cross-platform port of statusline.sh (macOS/Linux keep the .sh; Windows uses this).
The ponytail badge is itself a bash script, so it is appended only when bash is present
(macOS/Linux/WSL); on plain Windows the core status line renders and the badge is skipped.
"""
import glob
import json
import os
import subprocess
import sys
from shutil import which


def main() -> None:
    try:
        d = json.load(sys.stdin)
        if not isinstance(d, dict):
            d = {}
    except (ValueError, AttributeError):
        d = {}

    model = (d.get("model") or {}).get("display_name", "")
    cwd = (d.get("workspace") or {}).get("current_dir", "") or ""
    home = os.path.expanduser("~")
    if cwd.startswith(home):
        cwd = "~" + cwd[len(home):]

    ctx = ""
    pct = (d.get("context_window") or {}).get("used_percentage")
    if isinstance(pct, (int, float)):
        color = "10" if pct < 60 else ("11" if pct < 80 else "9")  # green / yellow / red
        ctx = f" | \x1b[38;5;{color}mctx {pct:.0f}%\x1b[0m"

    line = f"{model} | {cwd}{ctx}"

    badge = ""
    bash = which("bash")
    if bash:
        # version-key sort to match the mac side's `sort -V` (lexicographic breaks at 4.9 vs 4.10)
        cands = sorted(glob.glob(os.path.join(
            home, ".claude", "plugins", "cache", "ponytail", "ponytail",
            "*", "hooks", "ponytail-statusline.sh")),
            key=lambda p: [int(t) if t.isdigit() else 0
                           for t in p.split(os.sep)[-3].split(".")])
        if cands:
            try:
                badge = subprocess.run([bash, cands[-1]], capture_output=True,
                                       text=True, check=False).stdout.strip()
            except OSError:
                badge = ""

    sys.stdout.write(line + (" " + badge if badge else ""))


if __name__ == "__main__":
    main()
