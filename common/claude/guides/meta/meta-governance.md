# Meta-Governance — Editing CLAUDE.md, Rules, Skills, Plugins

Load when a task touches Claude Code global setup: CLAUDE.md, `~/.claude/rules/`, `~/.claude/guides/`, skills, plugins, hooks, `settings.json`. Procedure: follow skill `clx-claude-config`.

## Where does a change go?

| Change | Target | Also |
|--------|--------|------|
| New always-on invariant (rare) | CLAUDE.md § Always-on | — |
| On-demand domain policy | `guides/<meta|work>/<topic>.md` | CLAUDE.md Guide router row |
| Path-scoped policy (file-type specific) | `rules/<topic>.md` with `paths:` frontmatter | none (auto-loads) |
| New procedure / tool integration | `skills/<name>/SKILL.md` | CLAUDE.md skill router row |
| Marketplace extension | `claude plugin install` + `settings.json` | router row if agent-triggered |
| Structural hard block | `hooks/<script>` + `settings.json` | CLAUDE.md hooks line |
| Feature flag | `settings.json` | relevant guide if docs needed |

Never add procedural detail to CLAUDE.md — add a router row pointing to the file. Never put a file without `paths:` frontmatter in `rules/` — it would eager-load every session; use `guides/`.

## Guides
- Add: create `guides/<meta|work>/<kebab>.md` (English, concise, first line = "Load when:"), add one CLAUDE.md Guide router row, verify with `rg`.
- Edit: change the guide file only; touch CLAUDE.md only if the trigger or filename changed.

## Skills / plugins
- Skill: create `skills/<name>/SKILL.md` (frontmatter `name`, `description`) or install a plugin; add one router row; policy gate via thin `guides/<group>/<topic>.md` only if needed. Large data → skill subfolder. Trim listing cost of low-traffic plugin skills via `settings.json skillOverrides` (name-only / user-invocable-only).
- Plugin: `claude plugin install <name>@<marketplace>` → enable in `settings.json` → router row if the agent must load its skills → `claude plugin list` to confirm.
- Skills-description budget (codex reserves ~2% of context; too many enabled plugins truncates every description — a startup warning fires). Rule: enable only role-relevant, non-redundant plugins per surface, and disable large multi-skill bundles that duplicate dedicated plugins. Codex is the coding-execution surface → disable there (not in Claude Code): `document-skills@anthropic-agent-skills` (18 skills; its docx/pptx/xlsx/pdf overlap the openai `documents/presentations/spreadsheets/pdf`, its clx-frontend-design/skill-creator overlap the claude-plugins-official ones, the rest are design/content unused in codex) and `ponytail@ponytail` (dumps its full ruleset as visible codex hook-context; Claude-Code-only). Reversible via each `[plugins."x@y"] enabled` flag in `~/.codex/config.toml`. The bigger consumer is the always-loaded skills dir `~/.codex/skills/*` (not gated by plugin flags): keep only coding/process skills there (debugging, TDD, verification, reporting, architecture, planning, clx-codex-config, chronicle, clx-dataset-work), and move office/design/UI/content ones (docx/pdf/pptx/xlsx, clx-figma-workflow, clx-frontend-design, impeccable, clx-theme-factory, clx-unslop, clx-vercel-web-design-guidelines, ensemble-consensus, clx-playwright) to `~/.codex/skills-disabled/` — codex does not scan it, so it leaves the budget while staying on disk. If a `~/.claude/skills/<x>` symlink points into `~/.codex/skills/<x>` (some skills are codex-native, Claude-Code-borrowed — config-doctor `symlink resolves` FAIL flags a break), re-point it to the new `skills-disabled/<x>` so Claude Code keeps it. Verify a fix with a `codex exec` smoke: the `2% skills` warning must be gone.
- Skills follow the agentskills.io spec (user policy 2026-07-06): `name` matches the directory name (lowercase-hyphen, ≤64, no `--`), `description` ≤1024 chars covering what+when, extras live under `metadata:` — no custom top-level fields except ones Claude Code itself consumes (e.g. `disable-model-invocation`), SKILL.md <500 lines with detail split into `references/`, executables in `scripts/`. Validate with `skills-ref validate` when available. Context-budget ceiling for anything WE author that enters model context (CLAUDE.md/AGENTS.md, auto-loaded rules, router guides, our SKILL.md): ≤200 lines, aim ~100 — split overflow into `references/` (on-demand). Vendored upstream skills (docx 590L etc., process skills) stay upstream-as-is — forking them for line count creates update drift; the ceiling binds skills WE author. config-doctor flags authored context files over 200 lines. Skill description language policy (2026-07-25): English prose with QUOTED Korean trigger keywords kept in place (e.g. '백업', '점검') — the owner prompts in Korean, so stripping them hurts trigger matching; skill BODIES and references stay English.
- Rust-first (user policy 2026-07-06): refactor refactorable components of custom skills/plugins to Rust — hot paths and existing rust/ backends first; build/ship natives (cargo/maturin) so python fallbacks stop being the live path; new helper tooling starts in Rust, not JS. Script-glue may stay non-Rust only when porting would hurt portability or simplicity — justify per component. Python fallback remains the fail-open path.
- Tell user to restart if the skills/plugins list is stale.

## Hooks
Script in `hooks/`, register in `settings.json` with matcher, test with stdin JSON, add one CLAUDE.md hooks line if agent-relevant.

## CLAUDE.md discipline

Fixed sections: output+precedence, always-on (~6 bullets), guide router, skill/plugin router, hooks. Keep minimal; no multi-paragraph policy, model troubleshooting, design bans, or git prose — those live in guides.

After any meta edit: no duplicate policy between CLAUDE.md and guides; every new guide/skill/plugin has a router row; English in meta files (chat stays Korean); `meta/claude-layout` still accurate if tree changed.

## Delegation
Meta edits are always orchestrator-direct — edit CLAUDE.md/rules/config yourself. No `create_goal` during meta maintenance.
