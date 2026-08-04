# Codex Config Layout

```
~/.codex/  ($CODEX_HOME)
├── AGENTS.md      # router only: always-on + guide/skill router tables (loaded every session — keep minimal)
├── config.toml    # features, plugins enabled, model provider, projects
├── hooks.json     # PreToolUse / PostToolUse hooks
├── hooks/         # hook scripts
├── prompts/       # custom slash prompts (*.md → /name)
├── rules/         # AUTO-LOAD: path-scoped only (paths: frontmatter required)
│   ├── engineering.md   # code files
│   └── design/          # UI files (minimal core + AoE workflow)
├── guides/        # ON-DEMAND: read only via AGENTS.md Guide router — never preloaded
│   ├── README.md        # human index
│   ├── meta/            # codex-layout, meta-governance, backup
│   └── work/            # work-modes, subagents, intent, intent-patterns, ensemble-consensus, cluxion, models, git
├── skills/        # lazy-loaded procedural skills (*/SKILL.md)
├── plugins/       # plugin cache
└── goals_1.sqlite # thread goals DB (do not set token_budget)
```

## Layer roles

| Layer | Holds | Token policy |
|-------|-------|--------------|
| AGENTS.md | language, always-on invariants, router tables | smallest possible; every session |
| rules/ | path-scoped policy ONLY | auto-loads on file match; a rule WITHOUT `paths:` frontmatter eager-loads every session — never put on-demand content here |
| guides/ | domain policy (git, design routing, meta…) | read only when a router row triggers |
| prompts/ | slash prompts | zero until invoked |
| skills/ | multi-step procedures, deep domain | read when router/skill listing says |
| plugins/ | bundled skills/hooks/MCP | enable in `config.toml` |
| hooks/ | structural hooks | no agent read — runs automatically |

## Wiring contract

1. Single source of truth — detail lives in one guide or skill, never duplicated in AGENTS.md.
2. Router row — every guide/skill/plugin with a trigger gets one AGENTS.md row.
3. Lazy load — read the target file only after the trigger matches; `rules/` is the only auto-load layer and must stay path-scoped.
4. English in AGENTS.md/guides/rules/skills (chat stays Korean).
5. Precedence — repo `AGENTS.md` > global for project facts; global > repo for process, git attribution, design.

## Anti-patterns

Non-path-scoped file in rules/ (eager-loads every session → move to guides/); long prose in AGENTS.md (→ guide); same policy in guide + skill; guide/skill without a router row; plugin enabled without a `config.toml` entry.
