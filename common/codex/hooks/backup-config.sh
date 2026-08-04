#!/usr/bin/env bash
# Back up custom Codex config assets to ~/Documents/agents-backup/codex.
# Idempotent: re-run any time after adding/editing rules, skills, hooks, profiles, or router.
# Excludes secrets (auth.json), caches, logs, sessions, sqlite, history — custom assets only.
set -euo pipefail

SRC="$HOME/.codex"
DEST="$HOME/Documents/agents-backup/codex"
LOCKER=${CLX_RESOURCE_LOCK_BIN:-"$HOME/.claude/hooks/clx-resource-lock.py"}
DEST_REAL=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$DEST")
if [ "${CLX_RESOURCE_LOCK_HELD:-}" != "codex-config-backup:$DEST_REAL" ]; then
  exec "$LOCKER" \
    --kind codex-config-backup --path "$DEST" --timeout 120 -- "$0" "$@"
fi

# Custom assets to back up (auth.json and runtime state are excluded by omission).
ITEMS=(
  AGENTS.md
  config.toml
  hooks.json
  rules
  guides
  skills
  skills-disabled
  hooks
  agents
  prompts
  grok.config.toml
  grok-hermes.config.toml
  grok-heavy.config.toml
  grok-4.3.config.toml
  grok-api.config.toml
  openai-default.config.toml
  grok-hermes-catalog.json
  start-grok-hermes-proxies.sh
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

find "$DEST" -mindepth 1 -maxdepth 1 ! -name 'BACKUP_MANIFEST.txt' -exec rm -rf {} +

for item in "${ITEMS[@]}"; do
  if [ -e "$SRC/$item" ]; then
    cp -aL "$SRC/$item" "$DEST/" 2>/dev/null || cp -a "$SRC/$item" "$DEST/"
  fi
done

# Keep machine-local trust/runtime state out of the portable snapshot.
if [ -f "$DEST/config.toml" ]; then
  awk '
    /^\[(projects\.|hooks\.state(\.|])|tui\.model_availability_nux])/ { skip=1; next }
    /^\[/ { skip=0 }
    !skip { print }
  ' "$DEST/config.toml" > "$DEST/config.toml.tmp"
  mv "$DEST/config.toml.tmp" "$DEST/config.toml"
  perl -0pi -e 's/\n+\z/\n/' "$DEST/config.toml"
fi

# Portable external-executor files only.
mkdir -p "$DEST/local-bin" "$DEST/grok/agents"
for f in clx-grok-delegate clx-ai-delegate; do
  [ -f "$HOME/.local/bin/$f" ] && cp -a "$HOME/.local/bin/$f" "$DEST/local-bin/"
done
for f in config.toml sandbox.toml clx-skill-links.tsv; do
  [ -f "$HOME/.grok/$f" ] && cp -a "$HOME/.grok/$f" "$DEST/grok/"
done
[ ! -f "$HOME/.grok/agents/clx-delegate.md" ] \
  || cp -a "$HOME/.grok/agents/clx-delegate.md" "$DEST/grok/agents/"

# The clone is materialized for its target account during restore.
python3 "$HOME/.claude/hooks/home-tokenize.py" "$HOME" "$DEST"


# Copied source trees may contain interpreter bytecode or agent work notes.
find "$DEST" -type d \( -name '__pycache__' -o -name '.codex-briefs' -o -name '.grok-briefs' \) \
  -prune -exec rm -rf {} +
find "$DEST" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

{
  echo "# Codex config backup"
  echo "generated: $(date '+%Y-%m-%d %H:%M:%S %z')"
  echo "source:    $SRC"
  echo "items:     ${ITEMS[*]}"
  echo
  echo "## Tree"
  (cd "$DEST" && find . -not -path '*/.git/*' | sort)
} > "$DEST/BACKUP_MANIFEST.txt"

echo "✓ Codex config backed up → $DEST"
