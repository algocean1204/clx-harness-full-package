---
name: clx-model
description: "Model registry manager — view or change model ids/efforts in ~/.agents/models.toml, the single source of truth (nothing else may hardcode model names). Explicit invocation ONLY — /clx-model or '모델 설정', '모델 변경', '모델 바꿔' requests. Pipeline: validate availability → update registry → regenerate machine configs → re-verify → backup."
---

# clx-model — Model Registry Pipeline

**View** (no args): print `~/.agents/models.toml` as a table — role | model | effort | transports.

**Change** (`/clx-model grok_exec=<id>` or natural language):

1. **VALIDATE before writing** — the model must exist on its backend:
   - `grok_exec` → `~/.grok/bin/grok models` (or `clx-grok-call models`) must list it.
   - `gpt_exec` → the Codex model catalog (`~/.codex/config.toml` provider catalog / a cheap read-only `codex exec` probe when usage allows) must accept it.
   - `code_delegate` / `test_agent` → must be a valid Agent-tool tier (opus / sonnet / haiku / fable) or a full `claude-*` id.
   - Unknown or unlisted → REFUSE and show the available list. Never write an unvalidated id.
2. **UPDATE** `~/.agents/models.toml` — preserve comments and structure; one role per change unless the user batches.
3. **PROPAGATE** the few machine configs that need literals: `~/.codex/config.toml` `model =` line follows `gpt_exec`; confirm Grok's default matches `grok_exec` via `grok models`. Guides/commands need NO edits — they reference roles, never literals.
4. **RE-VERIFY**: `model-registry-check.py` must end clean; if any selftest contract pins model behavior, run and repin in the same session. `config-doctor.py` is owner-only and is NOT shipped — skip it when absent.
5. **BACKUP**: `~/.claude/hooks/backup-to-git.sh`. Report outcome-first: role, old → new, validation evidence.

Rules: model names live ONLY in the registry — refuse any request to hardcode one elsewhere (core rule 2). Effort policy: `xhigh` when the backend supports it, else `high`. Explicit request only; never scheduled.
