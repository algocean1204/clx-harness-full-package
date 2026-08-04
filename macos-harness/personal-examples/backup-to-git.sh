#!/usr/bin/env bash
# EXAMPLE — the owner's config-backup-and-push flow, sanitized.
# NOT run by install.sh and NOT wired into any hook as shipped. Personalize before use:
#   1. Set OWNER to your GitHub account.
#   2. Create a PRIVATE repo and set EXPECTED_REMOTE to it.
#   3. Review the secret-scan patterns below — never push if it matches.
# The clean distribution ships with no remote and never auto-pushes.
set -euo pipefail

OWNER="OWNER"                                                   # <-- your GitHub account
EXPECTED_REMOTE="git@github.com:${OWNER}/agents-config-backup.git"
REPO_DIR="$HOME/Documents/agents-config-backup"                 # your local clone of that repo
CLAUDE_MIRROR="$HOME/Documents/agents-backup/claude"
CODEX_MIRROR="$HOME/Documents/agents-backup/codex"

command -v rg >/dev/null 2>&1 || { echo "backup: rg (ripgrep) required for the secret scan" >&2; exit 1; }
[ -d "$REPO_DIR/.git" ] || { echo "backup: $REPO_DIR is not a git repo" >&2; exit 1; }
[ "$(git -C "$REPO_DIR" remote get-url origin)" = "$EXPECTED_REMOTE" ] \
  || { echo "backup: origin is not $EXPECTED_REMOTE — refusing" >&2; exit 1; }

# 1. Refresh the local safe mirrors (these already exclude secrets/runtime by omission).
"$HOME/.claude/hooks/backup-config.sh" >/dev/null
"$HOME/.codex/hooks/backup-config.sh"  >/dev/null

# 2. Mirror into the repo (BACKUP_MANIFEST.txt carries a username/host path — keep it out).
mkdir -p "$REPO_DIR/claude" "$REPO_DIR/codex"
rsync -a --delete --exclude '.git' --exclude 'BACKUP_MANIFEST.txt' "$CLAUDE_MIRROR/" "$REPO_DIR/claude/"
rsync -a --delete --exclude '.git' --exclude 'BACKUP_MANIFEST.txt' "$CODEX_MIRROR/"  "$REPO_DIR/codex/"

# 3. Secret scan — FAIL CLOSED. Generalized token patterns; tokens in git history are forever.
#    rg exit code: 0 = matched (abort), 1 = clean (proceed), other = error (abort).
set +e
rg -n --no-messages --glob '!.git/**' \
  -e 'sk-[A-Za-z0-9_-]{24,}' \
  -e 'gh[a-z]_[A-Za-z0-9]{30,}' \
  -e 'xox[a-z]-[A-Za-z0-9-]{20,}' \
  -e 'AKIA[0-9A-Z]{16}' \
  -e 'xai-[A-Za-z0-9]{20,}' \
  -e 'PRIVATE KEY-----' \
  "$REPO_DIR" >/tmp/backup-secret-scan.txt 2>&1
scan_rc=$?
set -e
[ "$scan_rc" -eq 1 ] || { echo "backup: secret scan matched or errored (rc=$scan_rc, see /tmp/backup-secret-scan.txt)" >&2; exit 1; }

# 4. Commit + push. No AI attribution.
cd "$REPO_DIR"
git add -A -- claude codex
if git diff --cached --quiet; then
  echo "backup: no changes"
else
  git -c user.name="$OWNER" -c user.email="${OWNER}@users.noreply.github.com" \
    commit -q -m "backup: sync agents config $(date '+%Y-%m-%d %H:%M')"
  git push -u origin main && echo "backup: pushed"
fi
