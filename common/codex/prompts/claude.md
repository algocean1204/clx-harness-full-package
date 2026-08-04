---
description: Delegate one bounded Git-repository unit to Claude Code (model from models.toml)
argument-hint: <task to delegate (optionally: repo path + task)>
---

Read `~/.codex/guides/work/models.md` (§ Opt-in delegation gate) and apply it to this explicit request:

$ARGUMENTS

0. Availability: if `clx-ai-delegate` or the `claude` CLI is not installed, say so in one line and execute natively.
1. Explicit invocation authorizes one bounded Claude Code unit. Do not refuse by grade category; narrow ambiguous input to a verifiable unit.
2. Resolve the target Git repository, then run exactly one `clx-ai-delegate claude <repo> -p "<prompt>"` call.
3. A model the USER named in this request wins for this call via `--model` and optional `--effort`. Otherwise use role `claude_exec` from `~/.agents/models.toml` verbatim.
4. Never chain or retry blindly; on failure inspect partial state first. The wrapper owns sandboxing, recursion rejection, and cleanup.
5. Verify the returned diff/output yourself, then report outcome-first.
