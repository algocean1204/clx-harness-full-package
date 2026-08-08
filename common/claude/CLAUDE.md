# Claude Code — Platform Config

@~/.agents/AGENTS.md

Core rules above are the source of truth; this file adds Claude-only deltas and routers. Config: path-scoped `rules/`; on-demand `guides/`. Layout: `meta/claude-layout`; maintenance: `clx-claude-config`.

## Claude-only always-on

- Goals/ensemble: no goals or plan-only turns except the system gate and the core rule 11 event-driven specification gate for a new non-trivial task. The rule-11 gate owns task start — `brainstorming`/`clx-grill-me` fire only on explicit request or inside the gate. Authorized work: debate → implement → verify same turn; review returns consensus, never implementation authority. → `work/goals`, `work/ensemble-consensus`
- `/supercoder` is explicit slash-only (user-invoked only, `disable-model-invocation`); `clx-preprocess` may self-load when preprocessing is genuinely needed. Routing detail: `work/cluxion`.

## Guide router — read `~/.claude/guides/<guide>.md` on trigger

| Guide | Load when |
|-------|-----------|
| `meta/claude-layout` | Inspect/change ~/.claude structure |
| `meta/meta-governance` | Add/edit CLAUDE.md, rules, guides, skills, plugins, hooks, settings |
| `meta/backup` | After any config change → `backup-to-git.sh` (mirror + push); or 설정 백업 (folder backup → `clx-repo-backup`) |
| `~/.agents/user/` (owner context, PRIVATE) | `profile/*` for identity/devices/preferences; `principles/design-principles.md` REQUIRED before env/config changes; `repos.md` before any push; `delegation.md`·`ontology.md` self-inject — open only to EDIT |
| `work/intent` | Task start / drift temptation — spec lock, alignment loop, anti-drift |
| `work/intent-patterns` | JUDGE step of non-trivial tasks (rg by domain); user corrections append rows |
| `work/work-modes` | Task start — orchestrator/executor/reader roles; executor and skill axes stay separate |
| `work/subagents` | Before delegating to a Task subagent (caps: ≤2 tiers, ≤10 concurrent) |
| `work/models` | `/grok` · `/gpt` · `/claude` delegation, fallback, recursion ban |
| `work/browser-state` | Any browser automation or Chrome/profile/cookie/session operation |
| `work/git` | Commit, branch, PR, git safety |
| `work/goals` | `/goal`, loops, cycle report, broken-loop fixes |
| `work/ensemble-consensus` | 3-model consensus, 앙상블, 다관점 토론 |
| `work/cluxion` | `/supercoder` or cluxion skills — capability/tradeoff routing |

Index: `guides/README.md`. Auto-loaded, no router: `rules/engineering.md`, `rules/design/*`.

## Skill / plugin router

| Asset | Load when |
|-------|-----------|
| Meta/state: `clx-claude-config` · `clx-session-intent` · `clx-bracket-payload` · `clx-anti-hallucination` | Named config maintenance / explicit session intent or DoD repair / bracket syntax (wins over ambiguity) / long or compacted context |
| Planning/data/report: `clx-grill-me` · `clx-modular-architecture-design` · `clx-dataset-work` · `clx-concise-report` · `clx-report-policy` · `clx-flow-map` | Ambiguous scope / new-system architecture / dataset work / non-trivial chat report / report-file gate / RUNTIME flow of existing code (`/clx-tree`; static structure → `graphify`) |
| Design specialists: `clx-figma-workflow` · `clx-frontend-design` · `impeccable` | Route through `rules/design/design-workflow.md`; choose at most one |
| Design foundation: `clx-apple-design` | Substantial UI work even without an Apple request; skip non-UI, exact-copy, and one-value patches |
| Design helpers: `clx-theme-factory` · `clx-color-expert` · `clx-immersive-web` · `clx-vercel-web-design-guidelines` · `clx-playwright` | Explicit theme / color science / 3D / named audit / browser evidence; owning helper may omit a specialist |
| Design media: `clx-canvas-design` · `clx-algorithmic-art` · `clx-hand-drawn-diagrams` | Explicit static art / generative art / Excalidraw; no Apple or UI specialist |
| Design system: `clx-astryx` | Only when the design-workflow Astryx rule fires (new React, no established system) or explicitly requested |
| Writing pack: `viral-hooks` · `storytelling` · `dumbify` · `anti-ai-writing` · `voice-dna` · `clx-unslop` | Publishable content the user asked for ONLY; never reports/commits/comments (rules 4/8). Chain hook→structure→dumbify→anti-ai→voice, `clx-unslop` last |
| Team factory: `clx-harness-factory` | Explicit `/harness` (incl. `list`/`use`; 100 harnesses at `~/.agents/harness-library`) or 하네스 구성/팀 설계/설치 only — obeys core tier/concurrency caps |
| Model registry: `clx-model` | Explicit `/clx-model` or 모델 설정/변경 only — models.toml single source, validate→propagate→verify |
| Folder backup: `clx-repo-backup` | Explicit `/backup` or folder-backup only — `.backup-repo` marker, ask-and-configure on first run, one setup→push pipeline |
| Cluxion: `clx-hermes-call:clx-hermes-call` | Explicit Hermes delegation, one role. Via the `/grok` gate: one-shot through the `clx-grok-call` CLI (wrapper plugin retired as duplicate), repo execution via `clx-grok-delegate`. `/supercoder` user-invoked only; `clx-preprocess` self-loads when needed; consensus → `ensemble-consensus` |
| Authoring/process: `skill-creator` · Plugin `plugin-dev` · `ponytail` · `clx-anti-overengineering` · `ensemble-consensus` · `brainstorming` · `systematic-debugging` · `test-driven-development` · `verification-before-completion` | Exact triggers; non-trivial feature/bugfix only (never a behavior-preserving refactor) → TDD; non-trivial changed work → `verification-before-completion`. Do not stack same-role alternatives; ponytail owns lean discipline here (clx-anti-overengineering is the portable mirror). Router rows win over a skill's own self-description. |
| `docx` · `pptx` · `xlsx` · `pdf` | Load only the matching office/PDF authoring skill |
| External context tools: `graphify` CLI · `claude-hr` alias | Opt-in only — structure graph via `graphify . --code-only` (keyless AST; semantic mode needs an API key, never stored); `claude-hr` (Headroom proxy) is launched BY THE USER, never default-wrap |

System skills (`.system/*`): only on a matching task.

## Hooks

Lifecycle hooks live in `settings.json`; implementation and checks stay in `hooks/` and `meta/claude-layout`, not always-on context.
