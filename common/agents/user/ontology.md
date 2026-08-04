# Personal store map

TEMPLATE-UNFILLED — delete this line once you have filled the file in. Until then this block
is never injected.

`~/.agents/user/` is the single ROOT of your *context*. It is a map, not a datastore: live
personal stores stay where their tools expect them, and this file is the one place that says
what exists, who owns it, and where the public boundary runs.

Marker for injection dedup: `[[clx:owner-ontology]]`

| Store | Location | Written by | Read by | Ships? |
|---|---|---|---|---|
| Auto-memory | `~/.claude/projects/<proj>/memory/` | memory tool | session start (index only) | NO |
| Session intent | `~/.claude/session-intent/<SID>/core.md` | skill `clx-session-intent` | `intent-lock.py`, `precompact-guard.sh` | NO |
| Mistake ledger | `~/.claude/guides/work/intent-patterns.md` | correction capture | JUDGE step (`rg`) | ships EMPTY |
| Owner context | `~/.agents/user/` | you | AoE router rows only | NO |
| Harness library | `~/.agents/harness-library/` | `update-vendored.sh` | `/harness list\|use` | YES (pristine vendor) |

Add a row for anything you introduce.

## Boundary rules

1. Nothing in the NO column may reach a public repo.
2. A new personal store gets a row here in the same change that creates it.
3. Locations and roles only — never credentials, tokens, or contents.
