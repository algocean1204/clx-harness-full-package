# Claude Code Config Index

Two layers, one contract: `rules/` auto-loads by path match (native); `guides/` loads ONLY when a CLAUDE.md router row triggers — nothing here is preloaded.

## rules/ — auto-load (paths: frontmatter)

| File | Auto-loads on |
|------|---------------|
| `engineering.md` | Code files (py/ts/js/go/rs/sh/java/rb/c/cpp) |
| `design/design-workflow.md` | UI files — orchestration order |
| `design/design-core.md` | UI files — tokens, anti-slop bans, critique gate |

## guides/ — on-demand via CLAUDE.md router

| Guide | Load when |
|-------|-----------|
| `meta/claude-layout.md` | Understanding or changing ~/.claude tree |
| `meta/meta-governance.md` | Adding/editing CLAUDE.md, rules, guides, skills, plugins, hooks |
| `meta/backup.md` | Back up config → `backup-to-git.sh` (owner-only, not shipped); or 설정 백업 (folder backup → skill `clx-repo-backup`) |
| `~/.agents/user/` (owner context, PRIVATE) | `profile/*` for identity/devices/preferences; `principles/design-principles.md` REQUIRED before env/config changes; `repos.md` before any push; `delegation.md`·`ontology.md` self-inject — open only to EDIT |
| `work/intent.md` | Task start / drift temptation — spec lock, alignment loop, anti-drift |
| `work/intent-patterns.md` | Self-growing failure ledger — rg in JUDGE step; corrections append |
| `work/work-modes.md` | Task start — orchestrator/executor/reader roles; executor and skill axes stay separate |
| `work/subagents.md` | Delegating heavy/parallel work to a Task subagent |
| `work/models.md` | `/grok` · `/gpt` opt-in delegation, grade gate, host fallback, recursion ban |
| `work/browser-state.md` | Browser automation or Chrome/profile state operations |
| `work/git.md` | Commit, PR, branch |
| `work/goals.md` | `/goal`, loops, cycle report, broken-loop fixes |
| `work/ensemble-consensus.md` | 3-model consensus, 앙상블, 다관점 |
| `work/cluxion.md` | `/supercoder`, cluxion skills — capability/tradeoff routing |

Maintenance: skill `clx-claude-config`.
