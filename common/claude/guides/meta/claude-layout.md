# Claude Code Config Layout

```
~/.claude/
├── CLAUDE.md       # router only: always-on + guide/skill router tables (loaded every session — keep minimal)
├── settings.json   # model pin, plugins, hooks, permissions, skillOverrides, statusLine
├── commands/       # custom slash commands (*.md → /name)
├── hooks/          # hook scripts (structural enforcement; agent never reads)
├── rules/          # AUTO-LOAD: path-scoped only (paths: frontmatter required)
│   ├── engineering.md   # code files
│   └── design/          # UI files (minimal core + AoE workflow)
├── guides/         # ON-DEMAND: read only via CLAUDE.md Guide router — never preloaded
│   ├── README.md        # human index
│   ├── meta/            # claude-layout, meta-governance, backup
│   └── work/            # work-modes, subagents, intent, intent-patterns, goals, ensemble-consensus, cluxion, models, git
├── skills/         # lazy-loaded procedural skills (*/SKILL.md)
└── plugins/        # plugin cache (managed by `claude plugin`)
```

## Layer roles

| Layer | Holds | Token policy |
|-------|-------|--------------|
| CLAUDE.md | language, always-on invariants, router tables | smallest possible; every session |
| rules/ | path-scoped policy ONLY | auto-loads on file match; a rule WITHOUT `paths:` frontmatter eager-loads every session — never put on-demand content here |
| guides/ | domain policy (git, goals, design routing, meta…) | read only when a router row triggers |
| commands/ | slash commands | zero until invoked |
| skills/ | multi-step procedures, deep domain | read when router/skill listing says |
| plugins/ | bundled skills/hooks/MCP | enable in `settings.json`; trim listing via `skillOverrides` |
| hooks/ | hard blocks + automation | no agent read — runs automatically |

## Wiring contract

1. Single source of truth — detail lives in one guide or skill, never duplicated in CLAUDE.md.
2. Router row — every guide/skill/plugin with a trigger gets one CLAUDE.md row.
3. Lazy load — read the target file only after the trigger matches; `rules/` is the only auto-load layer and must stay path-scoped.
4. English in CLAUDE.md/guides/rules/skills (chat stays Korean).
5. Precedence — repo guidance > global for project facts; global > repo for process, delegation, goals, git attribution, design.

## Anti-patterns

Non-path-scoped file in rules/ (eager-loads every session → move to guides/); long prose in CLAUDE.md (→ guide); same policy in guide + skill (guide = when/what, skill = how); guide/skill without a router row (never loaded); plugin enabled without a `settings.json` entry.
