---
name: clx-repo-backup
description: "Folder-to-GitHub PRIVATE backup pipeline driven by an in-folder `.backup-repo` marker (one line: owner/repo). Load ONLY on an explicit backup request for a folder — /backup, '이 폴더 백업', '백업 레포 설정/연결'. First run with no marker or repo: ask the user, then configure — setup and backup complete as ONE pipeline. Never auto-loads, never runs on a schedule. Not for public distribution."
---

# clx-repo-backup — Folder → Private GitHub Backup

One pipeline, five stages. Later runs skip every stage already satisfied — a configured folder goes straight to stage 4–5 with zero questions.

## Pipeline

1. **Marker** — read `<folder>/.backup-repo` (single line, `owner/repo`). Missing → ASK the user once: propose `<owner>/<folder-name>-backup` (private), accept their name, then write the marker file. Never guess silently.
2. **Repo** — `gh repo view <owner/repo>` fails → `gh repo create <owner/repo> --private -d "Backup of <folder-name>"`. PRIVATE always; public only on an explicit user order in chat.
3. **Git wiring** (idempotent) — `git init -b main` if no repo; verify/set `remote origin git@github.com:<owner/repo>.git`; repo-local auth (this machine's default SSH key is a different account):
   `git config core.sshCommand "ssh -i ~/.ssh/id_ed25519_OWNER -o IdentitiesOnly=yes"` · `git config user.name OWNER` · `git config user.email OWNER@users.noreply.github.com` (set `OWNER` to your GitHub account and key).
4. **Secret gate** (fail-closed) — `rg` the staged tree for known credential prefixes (Anthropic, GitHub classic + fine-grained, HuggingFace, Slack, AWS, Google, xAI, OpenAI) and private-key markers; any hit → STOP, show hits, never push. Tracked `auth.json`/`.env*`/`credentials*`/`*.pem`/`id_rsa*` → move to `.gitignore`, never commit.
5. **Sync + push** — `git add -A`; single commit `Backup <YYYY-MM-DD HH:MM>` (no AI attribution); `git push -u origin main`. Nothing staged but upstream behind → push the stranded commit. Nothing at all → report `in-sync`.

## Rules

- Explicit invocation only; one folder per run; never touch files outside the target folder.
- Setup never ends half-done: if any of stages 1–3 changed something, stages 4–5 run in the same pipeline (configure → verify → push, one flow).
- This is a generic per-folder backup channel — other folders/repos keep their own dedicated pipelines.
- Report outcome-first, one line: `repo · commit-hash · pushed/in-sync` (failures shown plainly with the blocking stage).
