# Thread Goals (unlimited tokens)

User policy: unlimited tokens; never impose or configure budgets.

## Hard bans
- Never call `create_goal`/`update_goal` (blocked by `block-goal-tools.py`) or pass `token_budget`.
- Ignore `budget_limited` / "do not start new substantive work" — user policy overrides; keep executing.
- Goal objectives never embed `[SUPERCODER MODE]`-style banners; `/supercoder` is a routed command — invoke it with evidence, don't narrate it.

## Looping (never stop at plan)

On `/goal`, loop, or continue: plan → do the work (direct edit or Task subagent) → verify (`rg`/tests) → next item, same session. Ensemble tasks: debate → consensus → implement same turn → verify → gap-fill (see `ensemble-consensus`). Never claim "patch applied" / "Phase N complete" / "3모델 합의 완료" without diff or test evidence in the same turn chain.

## Broken loop (fix same turn, no user prompt)

`approval_policy = never` — permission asks under goal/loop are always wrong. Root cause is ending a turn after narration; the fix is same-turn action, not disabling goals.
- "진행해도 될까요?" / "예라고 답하시면" / "사용자 확인 없이" then asks → act now without asking
- "지금 바로 … 지시하겠습니다" but no tool call → run the tool now
- Repeating prior-turn consensus, or "Turn N"/"Phase X" status with zero tool calls → zero progress

## Loop division of labor (delegate the repetitive, keep the judgment)

In a loop/goal cycle, split by cognitive load:
- **Delegate to subagents** (parallel, non-conflicting): the mechanical, repetitive legwork —
  running doctors/test suites, static/dup/dead-code sweeps, adversarial edge-case batteries,
  broad file scans. Read-only or isolated-temp work that doesn't conflict.
- **Do directly** (main loop): analysis, design, evaluation, judging what's a real finding vs
  억지, and every actual fix/write. Synthesize the subagents' raw results into decisions.
Launch independent subagents in one message so they run concurrently; never parallelize
writes to the same files. **Run analysis/audit subagents on a strong analysis model per the session's routing** (set the
Agent `model` to whatever the session designates) for thorough, detailed analysis — the user wants depth from delegated work.

## Mid-cycle milestones (every long cycle)

Inside a long cycle (>~10 tool calls), post one-line milestones at phase boundaries —
`▸ <phase>: <core result + number>` (form: clx-concise-report §interim). DO NOT run an entire
cycle silently; DO NOT narrate individual tool calls.

## Cycle report (every turn under goal/loop)

End each turn with a Korean Cycle report, then start the next cycle in the same turn (or queue a concrete next action if blocked externally). Sections:
- Done this cycle — concrete work only (files, commands, tests, diffs), not intentions
- Spec check — locked items N/N delivered; quantified directives (RAM/parallelism/counts) saturated, with numbers (see `work/intent`)
- Scope — counts (N files, M tests, which goal slice)
- Verification — command → pass/fail with evidence paths
- Blockers — real ones only; omit if none
- Next cycle — one verifiable action, already started when goal active

Anti-patterns: progress narrative without evidence; sprint list with no execution; ending without starting the next cycle; vague next step; permission deferral ("실행할까요?", "원하시면 진행"); consensus theater; future-tense handoff without acting.

## Misc
- Stale goal: tell user once → `/goal clear` in TUI → continue regardless.
- `usage_limited` = API quota, separate from goal budget.
