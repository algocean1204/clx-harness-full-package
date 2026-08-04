---
description: Build/extend/audit an agent-team harness, or install one from the 100-harness library (clx-harness-factory)
argument-hint: <domain description | 점검/감사 | list [keyword] | use <id>>
---

Invoke skill `clx-harness-factory` and follow it for:

$ARGUMENTS

Local policy overrides in that skill WIN over its upstream references (tier/concurrency caps, no auto CLAUDE.md edits, lean bias, project-scoped output only).

## Library mode (`list` / `use`)

Vendored 100-harness library: `~/.agents/harness-library/` (upstream revfactory/harness-100 ko/, pristine).

- `list [keyword]`: read `~/.agents/harness-library/ko/README.md` catalog table (+ `INDEX.md` overlap badges); show matching rows only — never dump all 100 unless asked.
- `use <id>`: install `ko/<id>/.claude/` into the CURRENT project per the install contract in `~/.agents/harness-library/INDEX.md` — non-destructive (never overwrite; report skips), rename each `skills/*/skill.md` → `SKILL.md`, prepend the core-binding header line to the installed `CLAUDE.md`, warn if the harness carries an existing-asset-priority badge. Library files are read-only sources — never edit them.
