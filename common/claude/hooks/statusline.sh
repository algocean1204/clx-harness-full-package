#!/bin/bash
# statusLine: model | cwd | context% (colored saturation warning) | ponytail badge
input=$(cat)
line=$(printf %s "$input" | python3 -c "
import sys, json, os
d = json.load(sys.stdin)
m = d.get('model', {}).get('display_name', '')
c = d.get('workspace', {}).get('current_dir', '') or ''
h = os.path.expanduser('~')
c = '~' + c[len(h):] if c.startswith(h) else c
pct = (d.get('context_window') or {}).get('used_percentage')
ctx = ''
if isinstance(pct, (int, float)):
    color = '10' if pct < 60 else ('11' if pct < 80 else '9')  # green / yellow / red at hallucination-risk zone
    ctx = f' | \x1b[38;5;{color}mctx {pct:.0f}%\x1b[0m'
print(f'{m} | {c}{ctx}', end='')" 2>/dev/null)
pt=$(ls "$HOME"/.claude/plugins/cache/ponytail/ponytail/*/hooks/ponytail-statusline.sh 2>/dev/null | sort -V | tail -1)
if [ -n "$pt" ]; then
  printf '%s %s' "$line" "$(bash "$pt" 2>/dev/null)"
else
  printf '%s' "$line"
fi
