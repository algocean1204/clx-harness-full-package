# Meta-Governance — Editing AGENTS.md, Rules, Skills, Plugins

Load when a task touches Codex global setup: AGENTS.md, `~/.codex/rules/`, `~/.codex/guides/`, skills, plugins, hooks, `config.toml`. Procedure: follow skill `clx-codex-config`.

## Where does a change go?

| Change | Target | Also |
|--------|--------|------|
| New always-on invariant (rare) | AGENTS.md § Always-on | — |
| On-demand domain policy | `guides/<meta|work>/<topic>.md` | AGENTS.md Guide router row |
| Path-scoped policy (file-type specific) | `rules/<topic>.md` with `paths:` frontmatter | none (auto-loads) |
| New procedure / tool integration | `skills/<name>/SKILL.md` | AGENTS.md skill router row |
| Marketplace extension | `codex plugin add` + `config.toml` | router row if agent-triggered |
| Structural hard block | `hooks/<script>` + `hooks.json` | AGENTS.md hooks line |
| Feature flag | `config.toml [features]` | relevant guide if docs needed |

Never add procedural detail to AGENTS.md — add a router row pointing to the file. Never put a file without `paths:` frontmatter in `rules/` — it would eager-load every session; use `guides/`.

## Shared root and platform adapters

`~/.agents/AGENTS.md` is the sole authored shared policy root. A platform adapter must load it
before platform deltas by native import when supported, otherwise by a generated snapshot whose
drift is checked. The adapter must not restate shared rules. It declares whether file reads,
routers, hooks, tools, sandboxing, session state, and subagents are available; unsupported
capabilities are reported, never simulated. Repository instructions may add project facts but do
not replace the global process root. External delegates receive only a bounded root snapshot and
the task IDs they need, never the orchestrator's session core.

## Guides
- Add: create `guides/<meta|work>/<kebab>.md` (English, concise, first line = "Load when:"), add one AGENTS.md Guide router row, verify with `rg`.
- Edit: change the guide file only; touch AGENTS.md only if the trigger or filename changed.

## Skills / plugins
- Skill: install via `skill-installer` or create `skills/<name>/SKILL.md` (frontmatter `name`, `description`); add one router row; policy gate via thin `guides/<group>/<topic>.md` only if needed. Large data → skill subfolder.
- Plugin: `codex plugin add <name>@<marketplace>` → `enabled = true` in `config.toml` → router row if agent must load its skills → `codex plugin list` to confirm.
- Skills follow the agentskills.io spec (user policy 2026-07-06): `name` matches the directory name (lowercase-hyphen, ≤64, no `--`), `description` ≤1024 chars covering what+when, extras live under `metadata:` — no custom top-level fields except ones Claude Code itself consumes (e.g. `disable-model-invocation`), SKILL.md <500 lines with detail split into `references/`, executables in `scripts/`. Validate with `skills-ref validate` when available. Vendored upstream skills (docx 590L is the sole >500L case) stay upstream-as-is — forking them for line count creates update drift; the ceiling binds skills WE author. Skill description language policy (2026-07-25): English prose with QUOTED Korean trigger keywords kept in place (e.g. '백업', '점검') — the owner prompts in Korean, so stripping them hurts trigger matching; skill BODIES and references stay English.
- Rust-first (user policy 2026-07-06): refactor refactorable components of custom skills/plugins to Rust — hot paths and existing rust/ backends first; build/ship natives (cargo/maturin) so python fallbacks stop being the live path; new helper tooling starts in Rust, not JS. Script-glue may stay non-Rust only when porting would hurt portability or simplicity — justify per component. Python fallback remains the fail-open path.
- Tell user to restart if the skills/plugins list is stale.

## Hooks
Script in `hooks/`, register in `hooks.json` with matcher, test with stdin JSON, add one AGENTS.md hooks line if agent-relevant.

## AGENTS.md discipline

Fixed sections: output+precedence, always-on (~5 bullets), guide router, skill/plugin router, hooks. Keep minimal; no procedural detail. After any meta edit: no duplicate policy; every new guide/skill/plugin has a router row; English in meta files; `meta/codex-layout` still accurate if tree changed.

## Delegation
Meta edits are orchestrator-direct (the pinned main model's session). No `create_goal` during meta maintenance.
