# `~/.agents/user/` — your own context (template)

This folder is **yours**. It ships EMPTY on purpose: the distribution carries the shape,
never anyone's data. Every file here still says `TEMPLATE-UNFILLED` — until you remove that
line, the harness treats the file as blank and injects nothing.

## Hard rules

1. **Never publish this folder.** It is excluded from the distribution's own repo and must
   stay out of any public repo you push. If you back it up, back it up to a PRIVATE repo.
2. **No secrets.** No tokens, API keys, passwords, or private keys — not even "temporarily".
   Names, machines, preferences, and pointers only.
3. **Facts here, policy in the core.** `~/.agents/AGENTS.md` owns the rules; this folder owns
   who you are and what you prefer. On a conflict the core wins.

## What each file is for

| File | Fill it in when |
|---|---|
| `profile/identity.md` | Your name/handle, git account, how you want to be addressed |
| `profile/devices.md` | The machines you work on and what differs between them |
| `profile/preferences.md` | How you want the agent to work with you |
| `principles/design-principles.md` | Your constitution for changing this harness |
| `delegation.md` | Which external executor to use for which work (if any) |
| `ontology.md` | Where your personal stores live (memory, sessions, ledgers) |
| `repos.md` | What each of your repos is for, and what must never enter which |

## How it loads

Nothing here is always-on. `delegation.md` and `ontology.md` carry a `[[clx:...]]` marker and
are injected **once per session** (and again right after compaction) only after you remove
their `TEMPLATE-UNFILLED` line. The rest is read on demand through the router row in
`~/.claude/CLAUDE.md`.
