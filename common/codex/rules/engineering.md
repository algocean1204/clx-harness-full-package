---
paths:
  - "**/*.py"
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.go"
  - "**/*.rs"
  - "**/*.sh"
  - "**/*.java"
  - "**/*.rb"
  - "**/*.c"
  - "**/*.cpp"
---

# Engineering Rules

Before changing code: find root cause (no symptom patching); read relevant code first and mirror existing patterns/APIs; minimal in-scope diff, no drive-by refactors.

Verification: build/run/test every change; state verified vs assumed, never fabricate results; prefer real parsers/libraries over string hacks.

Navigation: prefer LSP tools (typescript-lsp / pyright-lsp / jdtls-lsp plugins) for go-to-definition, references, and diagnostics in TS/Python/Java repos before grep guessing.

Style: comments minimal — the essential *why* only (a non-obvious constraint, a ceiling, a gotcha); never restate what the code does; no multi-line prose essays; one terse line beats a paragraph. Same for skill/doc authoring — core only, light. Batch independent reads/tool calls in parallel; search with `rg`.

A package entry file (`__init__.py`, `index.ts`, `mod.rs`, `package-info.java`) stays declarative —
re-exports, `__all__`, package metadata. Implementation there is allowed but needs its reason
stated in place, because the cost is real and was paid: diagnostics that name no package, the whole
package executing when one submodule is imported, and circular imports. Not a ban — those four
idioms genuinely differ, and `mod.rs` declaring modules and constants is its job.

Comments in someone else's project answer to that project, not to this harness. Three failures, all
observed in one real delivery:

- **No harness names.** No `ponytail:`, `clx-*`, skill, plugin, agent, or model name in code,
  comments, commits, or docs written for a project — the reader has none of this and the label is
  noise. OUTRANKS any skill asking for its own marker (ponytail's `// ponytail:` included): keep the
  insight, drop the prefix. `# ponytail: MemorySaver drops history on exit` → `# MemorySaver drops
  history on exit`.
- **Match the project's language.** Korean repo → Korean comments. The English-by-default rule
  governs THIS harness's own files, never the user's.
- **Never repeat a doc.** If the README already says it, the comment is duplication that will rot
  out of sync. Comment only what the code cannot show: a constraint, a ceiling, a gotcha.

Context budget for authored context files (CLAUDE.md, rules, guides, our SKILL.md): ≤200-line ceiling — full policy in `guides/meta/meta-governance.md` §Skills.

Scope: repo `AGENTS.md` wins on layout/APIs; global rules win on process (delegation, goals, git attribution).
