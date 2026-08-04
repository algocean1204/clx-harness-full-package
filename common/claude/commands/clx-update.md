---
description: Update the whole harness from its git clone (pull → dry-run → apply → verify)
argument-hint: (optional) path to the clx-harness-full-package clone
---

Update this harness to the latest published version. One project, one pass — rules, guides,
skills, commands, agents, hooks, plugins, and the harness library all come from the same repo.

$ARGUMENTS

1. **Locate the clone.** Use the path in `$ARGUMENTS` if given; otherwise try
   `~/Downloads/clx-harness-full-package`, `~/clx-harness-full-package`,
   `~/Documents/clx-harness-full-package`, `~/src/clx-harness-full-package`. If none exists,
   say so and stop — offer the clone command, do not clone into a surprising place:
   `git clone https://github.com/algocean1204/clx-harness-full-package.git`
2. **Pull.** In that directory: `git fetch origin && git status --short`. If the worktree has
   local edits, STOP and show them — the user decides whether to keep or discard. Otherwise
   `git pull --ff-only origin main`. Report the version delta in one line
   (`git log --oneline HEAD@{1}..HEAD | head -10`, or "already up to date").
3. **Dry-run.** `bash install.sh --check` (Windows: `install.ps1 -Check`). Show only the
   summary lines. If it reports anything unexpected, stop and report.
4. **Apply.** `bash install.sh --apply --force` (Windows: `-Apply -Force`).
   `--force` here means MERGE: same-named files are overwritten, nothing of the user's is
   deleted, and `~/.agents/user/` is copied no-clobber so filled-in owner context survives.
5. **Verify** (report as a small table, all measured — never assumed):
   ```bash
   ls "$HOME/.claude/plugins-vendored" | wc -l        # 11
   ls "$HOME/.claude/skills" | wc -l                  # 36
   ls "$HOME/.claude/commands" | wc -l                # 7
   ls "$HOME/.agents/harness-library/ko" | wc -l      # 100
   find "$HOME/.agents/user" -type f | wc -l          # 8
   grep -c '@~/.agents/AGENTS.md' "$HOME/.claude/CLAUDE.md"   # 1
   python3 "$HOME/.claude/hooks/model-registry-check.py"      # OK per role, or a stale-pin WARN
   ```
   Paths are quoted because an unquoted `~/...` is still glob-expanded — a HOME with a `*` in it would count the wrong directory. Counts may legitimately grow between releases — flag only a DROP or a zero. The last line asks
   the installed backends what they serve; a WARN means a pin fell behind — fix with `/clx-model`,
   never by editing a model name anywhere else.
6. **Report outcome-first**: updated from → to, what changed, which files the user still has
   to fill in (`~/.agents/user/*` still carrying `TEMPLATE-UNFILLED`), and whether a restart
   is needed (yes if skills/plugins/hooks changed).

Never: push anything, touch git remotes or credentials, delete a backup folder, or modify
files outside `~/.claude`, `~/.codex`, `~/.agents`.
