#!/usr/bin/env bash
# EXAMPLE — Stop hook that runs backup-to-git.sh when config changed since the last mirror.
# NOT wired in as shipped. To use: personalize backup-to-git.sh first, copy both into
# ~/.claude/hooks/, then add a Stop hook in settings.json:
#   { "type": "command", "command": "__CLX_HOME__/.claude/hooks/auto-backup.sh", "timeout": 120, "async": true }
M="$HOME/Documents/agents-backup/claude/BACKUP_MANIFEST.txt"
[ -f "$M" ] || exit 0

changed=$(find \
  "$HOME/.claude/CLAUDE.md" "$HOME/.claude/settings.json" \
  "$HOME/.claude/rules" "$HOME/.claude/guides" "$HOME/.claude/skills" \
  "$HOME/.claude/hooks" "$HOME/.claude/commands" "$HOME/.claude/agents" \
  "$HOME/.codex/AGENTS.md" "$HOME/.codex/config.toml" "$HOME/.codex/hooks.json" \
  "$HOME/.codex/rules" "$HOME/.codex/guides" "$HOME/.codex/skills" "$HOME/.codex/hooks" \
  -newer "$M" -type f -not -name '.DS_Store' 2>/dev/null | head -1)
[ -n "$changed" ] || exit 0

# Debounce: at most one attempt per ~2 min.
STAMP=/tmp/auto-backup-last-attempt
[ -n "$(find "$STAMP" -mmin -2 2>/dev/null)" ] && exit 0
touch "$STAMP" 2>/dev/null || true

if "$HOME/.claude/hooks/backup-to-git.sh" >/tmp/auto-backup-last.txt 2>&1; then
  echo "auto-backup: config change detected -> backed up + pushed"
else
  echo "auto-backup: FAILED (see /tmp/auto-backup-last.txt)"
fi
