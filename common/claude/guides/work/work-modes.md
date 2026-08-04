# Work Modes

Spec-lock first (`work/intent`). Executor selection and skill selection are separate AoE axes.

| Role | Default | Owns |
|------|---------|------|
| Orchestrator | pinned native main | clarify, route, meta-config, user interaction, inspect, verify, report |
| Executor | solo Task subagent (native model) | one bounded non-trivial execution unit; ≤2 tiers, ≤10 concurrent |
| External executor | `/grok` (grok-4.5) · `/gpt` (gpt-5.6-sol) — opt-in only | one bounded unit passing the grade gate (`work/models`) |
| Reader | readonly Task subagent | independent exploration, Fable/SOL lens, review |

Small precise edits, judgment calls, and host-only mutation stay main. Explicit user executor/model choices win. Within Grok/Codex, execute directly and never self-delegate. A one-value edit skips process skills and stays main.

Parallelize only independent analysis with a real wall-clock win. Keep shared-state work sequential. High-stakes/requested ensemble: debate → orchestrator decision → one executor → independent verification. Goal turns still execute in the same turn; no plan-only or permission-ask stop.
