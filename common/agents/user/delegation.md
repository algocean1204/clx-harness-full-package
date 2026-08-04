# Delegation policy — mine, not the core's

TEMPLATE-UNFILLED — delete this line once you have filled the file in. Until then this block
is never injected, and the harness simply runs everything on the session's native model.

Core rule 2 defines the *mechanism* (external delegation is opt-in and gated). This file is
your *choice*: which executors exist on THIS machine and when to reach for them. With no CLI
installed there is nothing to configure — `/grok`, `/gpt`, and `/claude` say so and run native.

Marker for injection dedup: `[[clx:owner-delegation]]`

## Executors available here

| Slash | CLI | models.toml role | Reach for it when |
|---|---|---|---|
| `/grok` | Grok Build | `grok_exec` |  |
| `/gpt` | Codex | `gpt_exec` |  |
| `/claude` | Claude Code | `claude_exec` |  |

Delete the rows you have no CLI for. Model ids and efforts come ONLY from
`~/.agents/models.toml` (change via `/clx-model`) — never write a model name here.

## Automatic routing gate

Architecture, design, security, verification, ambiguous-spec work — and main's own duties
(clarification, meta-config, diff inspection, verification). An explicit executor request overrides
this automatic-selection gate for one bounded unit. Add your own automatic exclusions below.

Never: recursive delegation, external-executor chaining, blind auto-retry, subagents invoking external CLIs.
