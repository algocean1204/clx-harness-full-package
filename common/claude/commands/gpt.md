---
description: Delegate one bounded Git-repository unit to Codex (model from models.toml)
argument-hint: <task to delegate>
---

Read `~/.claude/guides/work/models.md` (§ Opt-in delegation gate) and apply it to this explicit request:

$ARGUMENTS

0. Availability: if `clx-ai-delegate` or the `codex` CLI is not installed, say so in one line and execute natively.
1. Explicit invocation authorizes one bounded Codex unit. Do not refuse by grade category; narrow ambiguous input to a verifiable unit.
2. Resolve the target Git repository, then run exactly one `clx-ai-delegate codex <repo> -p "<prompt>"` call.
   - Model/effort: a model the USER named in this request wins for this call (say which, and that it is a
     one-call override, not a registry change). Otherwise use role `gpt_exec` from `~/.agents/models.toml`
     verbatim — never hardcode, and never silently substitute a "better" model for the pinned one.
3. Never chain or retry blindly; on failure inspect partial state first. The wrapper owns sandboxing, recursion rejection, cleanup, and Codex config normalization.
4. Verify the returned diff/output yourself (main owns verification), then report outcome-first.
