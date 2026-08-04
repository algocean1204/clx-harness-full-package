#!/usr/bin/env bash
# Back up custom Claude Code config assets to ~/Documents/agents-backup/claude.
# Idempotent: re-run any time after adding/editing rules, skills, hooks, or router.
# Excludes secrets, caches, logs, sessions, history — custom assets only.
set -euo pipefail

SRC="$HOME/.claude"
DEST="$HOME/Documents/agents-backup/claude"
LOCKER=${CLX_RESOURCE_LOCK_BIN:-"$(cd "$(dirname "$0")" && pwd -P)/clx-resource-lock.py"}
DEST_REAL=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$DEST")
if [ "${CLX_RESOURCE_LOCK_HELD:-}" != "claude-config-backup:$DEST_REAL" ]; then
  exec "$LOCKER" \
    --kind claude-config-backup --path "$DEST" --timeout 120 -- "$0" "$@"
fi

# Custom assets to back up (everything else — secrets/runtime — is excluded by omission).
ITEMS=(
  CLAUDE.md
  settings.json
  figma-mcp.json
  rules
  guides
  skills
  hooks
  agents
  commands
)

mkdir -p "$DEST"

# Fail closed BEFORE copying: cp -aL materializes symlink targets, so every file
# reachable through the ITEMS trees (nested links included) must resolve inside the
# cross-platform config ITEM trees — never the whole roots (auth.json/.credentials
# live directly under them) and never outside (~/.ssh keys etc.).
python3 - "$SRC" "$HOME" "${ITEMS[@]}" <<'PY'
import os, sys
# realpath-normalize the bases: $HOME may itself be a symlinked path (/var -> /private/var)
src, home = (os.path.realpath(p) for p in sys.argv[1:3])
items = sys.argv[3:]
cross = ("rules", "guides", "skills", "skills-disabled", "hooks", "agents", "commands", "prompts")
allowed = tuple(os.path.join(src, i) for i in items) + tuple(
    os.path.join(home, plat, n) for plat in (".claude", ".codex") for n in cross
)
def ok(real):
    return any(real == a or real.startswith(a + os.sep) for a in allowed)
bad, seen = [], set()
def check(p):
    real = os.path.realpath(p)
    if not ok(real):
        bad.append(f"{p} -> {real}")
for item in items:
    top = os.path.join(src, item)
    if os.path.isfile(top):
        check(top)
        continue
    for dirpath, dirnames, filenames in os.walk(top, followlinks=True):
        real_dir = os.path.realpath(dirpath)
        if real_dir in seen:          # symlink cycle guard
            dirnames[:] = []
            continue
        seen.add(real_dir)
        if not ok(real_dir):
            bad.append(f"{dirpath} -> {real_dir}")
            dirnames[:] = []
            continue
        for name in filenames:
            check(os.path.join(dirpath, name))
if bad:
    print("backup-config: ABORT — content escapes safe config scope:", file=sys.stderr)
    for line in bad[:20]:
        print("  " + line, file=sys.stderr)
    raise SystemExit(1)
PY

# Clean rebuild so deletions propagate; manifest is regenerated below.
find "$DEST" -mindepth 1 -maxdepth 1 ! -name 'BACKUP_MANIFEST.txt' -exec rm -rf {} +

for item in "${ITEMS[@]}"; do
  if [ -e "$SRC/$item" ]; then
    # -L resolves symlinks so the backup is self-contained (claude skills symlink into codex).
    # zz-* are hooks-selftest live-tree fixtures (may be dangling symlinks mid-test): excluding
    # them keeps a concurrent selftest from flipping this copy to the raw-symlink fallback.
    rsync -aL --exclude='zz-*' "$SRC/$item" "$DEST/" 2>/dev/null || cp -a "$SRC/$item" "$DEST/"
  fi
done

# The clone is materialized for its target account during restore.
python3 "$SRC/hooks/home-tokenize.py" "$HOME" "$DEST"

# Copied source trees may contain interpreter bytecode or agent work notes.
find "$DEST" -type d \( -name '__pycache__' -o -name '.codex-briefs' -o -name '.grok-briefs' \) \
  -prune -exec rm -rf {} +
find "$DEST" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

{
  echo "# Claude Code config backup"
  echo "generated: $(date '+%Y-%m-%d %H:%M:%S %z')"
  echo "source:    $SRC"
  echo "items:     ${ITEMS[*]}"
  echo
  echo "## Tree"
  (cd "$DEST" && find . -not -path '*/.git/*' | sort)
} > "$DEST/BACKUP_MANIFEST.txt"

echo "✓ Claude config backed up → $DEST"
