# Sub-Agent Rules

Load when: before delegating to a Task subagent.

Subagents are the default executor for non-trivial work (core rule 1): anything beyond a simple direct answer is delegated, unless it is a small precise edit or a judgment/verification call that stays with main. Hard caps: delegation depth ≤ 2 tiers below main (default 1 — a subagent works solo; tier 2 only when main explicitly grants it); concurrent subagents ≤ 10.

Parallelize only independent slices with no shared state and a real wall-clock win. Otherwise run sequentially. The orchestrator alone judges and verifies. Subagents never invoke `/grok`, `/gpt`, or external CLIs — external delegation is main-only.

Handoff: one-sentence goal, locked scope/quantities, files, constraints, verification, and out-of-scope. Never let a subagent change product/design direction or stop at consensus.

## Shared direction brief (any fan-out of ≥2 agents)

Main composes ONE direction block and prepends it to every agent prompt in the fan-out: goal, non-goals, hard constraints, lean boundary (what NOT to build — the YAGNI line), and the verification standard. Below it, each prompt carries its own scoped slice plus a sibling map (one line per sibling: name → scope → out-of-scope), so every agent knows what the others are building and in which direction. Agents still execute solo — no cross-agent chatter; coordination lives in the shared brief, and main reconciles overlaps at merge. Purpose: team-level alignment without team overhead — no duplicate work, no scope creep, no two agents over-engineering the same seam.

Design exception: substantial design work uses one scoped design specialist. Tiny, fully specified
fixes stay with main. The specialist receives one direction brief and may be the sole writer only
when the approved task includes implementation; review-only work stays read-only. Combine visual,
UX, accessibility, and motion lenses in that one bounded assignment instead of creating a standing
panel. Never recursively spawn or retry indefinitely. The orchestrator owns direction, merge, and
final evidence. A surface without subagents runs the same specialist role locally and reports that
capability fallback.
