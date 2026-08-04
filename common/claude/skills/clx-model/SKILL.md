---
name: clx-model
description: "Model registry manager — view or change model ids/efforts in ~/.agents/models.toml, the single source of truth (nothing else may hardcode model names). Explicit invocation ONLY — /clx-model or '모델 설정', '모델 변경', '모델 바꿔' requests. Pipeline: detect what the backends serve → update registry → regenerate machine configs → re-verify → backup."
---

# clx-model — Model Registry Pipeline

Detection is a script, not prose: `~/.claude/hooks/model-registry-check.py` asks each **installed**
backend what it serves and compares it to the pins. Roles whose CLI is absent are skipped, so this
is safe on a machine with no Grok or no Codex.

**View** (no args): run `~/.claude/hooks/model-registry-check.py --list` — prints the registry, the
Codex catalog ranked by priority, and `grok models`. Report it as a table.

A model the USER names for a specific call wins for that call — pass it to that one invocation and
say so. That is NOT a registry change and must never trigger this pipeline.

**Change** (`/clx-model grok_exec=<id>` or natural language):

1. **VALIDATE before writing** — the requested id must appear in `--list` output for that role
   (`code_delegate`/`test_agent` instead need an Agent tier: opus / sonnet / haiku / fable, or a
   full `claude-*` id). Unknown or unlisted → REFUSE and show the available list. Never write an
   unvalidated id. A live `codex exec` probe is optional confirmation, not the gate — it fails on
   usage limits for reasons unrelated to the model.
2. **UPDATE** `~/.agents/models.toml` — preserve comments and structure; one role per change unless the user batches. Keep `owner_pinned = true` on a role the owner chose deliberately: it silences the "a higher-ranked sibling exists" warning without weakening the id/effort checks. Drop it only when the owner asks to track the top model again.
3. **DO NOT propagate to `~/.codex/config.toml`.** Its `model` and `model_reasoning_effort` are the **interactive** Codex defaults; the registry is the **delegation** pin, and `/gpt` passes `-m`/`-c` explicitly on every call. Coupling them would overwrite a preference the owner set for their own sessions. Guides and commands need no edits either — they reference roles, never literals.
4. **RE-VERIFY**: `model-registry-check.py` must end clean — it is the checker, and it ships. Where `config-doctor.py` exists it runs the same check on a schedule; it is owner-only and is NOT part of the distribution, so its absence is normal, never a failure.
5. **BACKUP**: `~/.claude/hooks/backup-to-git.sh`. Report outcome-first: role, old → new, detection evidence.

The setup-ui page does the same thing in one click (`python3 setup-ui/server.py`) — same detector, same validation, same `.bak`. Use it when the user wants to browse what is on offer; use this skill when they name a change directly.

Rules: model names live ONLY in the registry — refuse any request to hardcode one elsewhere (core rule 2). Effort policy: the highest tier the backend serves, excluding self-delegating tiers (Codex `ultra` spawns its own subtasks, colliding with the one-bounded-unit rule). Explicit request only; never scheduled.
