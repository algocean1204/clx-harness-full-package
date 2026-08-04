#!/bin/bash
# Prune EPHEMERAL worklog entries older than 14 days from repo-local .reports/WORKLOG.md
# files (report-policy skill). IMPORTANT reports live in git and are never touched.
set -euo pipefail
CUTOFF=$(date -v-14d '+%Y-%m-%d' 2>/dev/null || date -d '14 days ago' '+%Y-%m-%d')

# Where to look for repos. This used to be the author's own two directories, hardcoded — on
# anyone else's machine the find matched nothing and the prune silently did nothing forever.
# `$HOME/Documents` is the generic default; set CLX_REPORT_ROOTS (colon-separated) to point
# somewhere else. Missing roots are skipped, so a wrong guess costs nothing.
IFS=':' read -r -a _roots <<< "${CLX_REPORT_ROOTS:-$HOME/Documents}"
_existing=()
for _r in "${_roots[@]}"; do [ -d "$_r" ] && _existing+=("$_r"); done
[ ${#_existing[@]} -eq 0 ] && exit 0

# -type f: a WORKLOG.md that is a SYMLINK would be written through to wherever it points, and a
# directory by that name would crash the rewrite. -print0 with `read -d ''`: `find` emits
# newline-terminated records, so a directory name containing a newline split one path into two and
# aborted the run. Vendored trees are not the user's to rewrite — the same exclusion the write-time
# hook already applies, so the two stop disagreeing about who owns third-party code.
{ find "${_existing[@]}" -maxdepth 8 -type f -path '*/.reports/WORKLOG.md' \
    -not -path '*/node_modules/*' -not -path '*/vendor/*' -not -path '*/third_party/*' \
    -not -path '*/.venv/*' -not -path '*/venv/*' -not -path '*/site-packages/*' \
    -not -path '*/dist/*' -not -path '*/build/*' -print0 2>/dev/null || true; } \
| while IFS= read -r -d '' f; do
  python3 - "$f" "$CUTOFF" <<'EOF'
import re, sys
path, cutoff = sys.argv[1], sys.argv[2]
# Every filesystem error is caught and reported, never raised: under `set -euo pipefail` one
# unreadable or read-only WORKLOG killed the while-subshell, so every repo `find` had not reached
# yet was skipped — silently, with exit 0. One bad file must cost one file.
try:
    text = open(path, encoding="utf-8", errors="replace").read()
    parts = re.split(r"(?m)^(?=## \d{4}-\d{2}-\d{2})", text)
    head, entries = parts[0], parts[1:]
    kept = [e for e in entries
            if (m := re.match(r"## (\d{4}-\d{2}-\d{2})", e)) and m.group(1) >= cutoff]
    if len(kept) != len(entries):
        open(path, "w", encoding="utf-8").write(head + "".join(kept))
        print(f"report-prune: {path} {len(entries)}->{len(kept)} entries")
except OSError as exc:
    print(f"report-prune: SKIPPED {path} — {exc.strerror}", file=sys.stderr)
EOF
done
exit 0
