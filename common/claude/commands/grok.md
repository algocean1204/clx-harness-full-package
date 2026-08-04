---
description: Delegate one bounded execution unit to Grok Build (model from models.toml)
argument-hint: <task to delegate (optionally: repo path + task)>
---

Read `~/.claude/guides/work/models.md` (§ Opt-in delegation gate) and apply it to this explicit request:

$ARGUMENTS

0. Availability: if `clx-grok-delegate`/`clx-grok-call` is not installed, say so in one line and execute natively — never treat a missing CLI as a failure.
1. Explicit invocation authorizes one bounded Grok unit. Do not refuse by grade category; narrow ambiguous input to a verifiable unit.
2. Delegate exactly ONE bounded unit to Grok:
   - Git-repo execution → `clx-grok-delegate <repo> -p "<prompt>" --always-approve --output-format plain`
   - One-shot analysis/second opinion → `clx-grok-call` CLI directly via Bash (wrapper plugin retired)
   - Model/effort: a model the USER named in this request wins for this call (say which, and that it is a
     one-call override, not a registry change). Otherwise use role `grok_exec` from `~/.agents/models.toml`
     verbatim — never hardcode, and never silently substitute a "better" model for the pinned one.
3. Never chain or retry blindly; on failure inspect partial state first. Never Grok→Grok.
4. Verify the returned diff/output yourself (main owns verification), then report outcome-first.
