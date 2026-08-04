# Backup Rules

Load when: user asks to back up / 백업; or after any change to global config under `~/.claude/` or `~/.codex/` (CLAUDE.md, AGENTS.md, rules, guides, skills, commands, hooks, settings).

## Local mirror (no push)

`~/.claude/hooks/backup-config.sh` → `~/Documents/agents-backup/claude/`;
`~/.codex/hooks/backup-config.sh` → `~/Documents/agents-backup/codex/`.
Idempotent, deletions propagate, symlinks resolved (`cp -aL`), and `$HOME` is
tokenized to `__CLX_HOME__` so the mirror stays portable. Secrets and runtime state
are never copied — auth, sessions, memory, caches, history, and sqlite are excluded
by omission (only the config ITEMS are mirrored).

Backed up: Claude/Codex routers and custom config assets. Never: auth/secrets or
log/session/project/cache/history/sqlite runtime state.

## Push to a private git remote (optional, owner-configured)

This distribution ships **no** git remote and **never auto-pushes**. To wire your own
backup-and-push flow, adapt the examples under `macos-harness/personal-examples/`
(`backup-to-git.sh`, `auto-backup.sh`): set the `OWNER` placeholder to your GitHub
account and point `EXPECTED_REMOTE` at your own private repo. Always secret-scan the
staged mirror before pushing — tokens in git history are permanent.

## Folder backup (marker-driven, optional)

The `clx-repo-backup` skill (Claude Code) backs up an arbitrary folder to its own
PRIVATE GitHub repo, driven by a `.backup-repo` marker file inside the folder — a
single line, `OWNER/repo`. On an explicit `/backup` request it reads the marker (or
asks and writes one on first run), creates the private repo if missing, runs a
fail-closed secret scan, then commits + pushes as one pipeline. Set `OWNER` to your
own GitHub account; nothing is pre-wired and nothing pushes without your marker.
