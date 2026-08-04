---
description: Run this unit natively at top GPT effort (you ARE the GPT executor — no self-delegation)
argument-hint: <task>
---

You are already the Codex GPT executor (the `gpt_exec` model in `~/.agents/models.toml`), so `/gpt` means: execute natively, never re-enter `codex` (recursion ban, core rule 2).

$ARGUMENTS

- Availability: if the `codex` CLI is not installed, say so in one line and execute natively — never treat a missing CLI as a failure.
- Apply maximum available reasoning effort (xhigh) to this unit.
- If the task is bulk/repetitive and better suited to Grok, suggest `/grok` instead of self-delegating.
- Report outcome-first with verification evidence.
