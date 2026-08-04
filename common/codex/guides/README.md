# Codex Config Index

Two layers, one contract: `rules/` auto-loads by path match; `guides/` loads ONLY when an AGENTS.md router row triggers — nothing here is preloaded.

## rules/ — auto-load (paths: frontmatter)

| File | Auto-loads on |
|------|---------------|
| `engineering.md` | Code files (py/ts/js/go/rs/sh/java/rb/c/cpp) |
| `design/design-workflow.md` | UI files — orchestration order |
| `design/design-core.md` | UI files — tokens, anti-slop bans, critique gate |

## guides/ — on-demand via AGENTS.md router

| Guide | Load when |
|-------|-----------|
| `meta/codex-layout.md` | Understanding or changing ~/.codex tree |
| `meta/meta-governance.md` | Adding/editing AGENTS.md, rules, guides, skills, plugins, hooks |
| `meta/backup.md` | Back up config → `backup-to-git.sh` (owner-only, not shipped); or 백업 |
| `work/intent.md` | Task start / drift temptation — spec lock, alignment loop, autonomy suppression |
| `work/intent-patterns.md` | Self-growing failure ledger (shared symlink) — rg in JUDGE step; corrections append |
| `work/work-modes.md` | Task start — orchestrator / implementer / opinion sub |
| `work/subagents.md` | Delegating heavy/parallel work to Task subagents |
| `work/models.md` | pinned-model default; Grok wiring (kept, not routed) |
| `work/browser-state.md` | Browser automation or Chrome/profile state operations |
| `work/git.md` | Commit, PR, branch |
| `work/ensemble-consensus.md` | 3-model consensus, 앙상블, 다관점 |
| `work/cluxion.md` | `/supercoder`, `/ultracode`, cluxion skills — capability/tradeoff routing |

Sub-dir `AGENTS.md` walk-up chain also scopes by path. Maintenance: skill `clx-codex-config`.
