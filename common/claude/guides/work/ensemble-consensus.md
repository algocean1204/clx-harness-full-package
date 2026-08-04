# Ensemble Consensus — 3-Lens Protocol (policy gate)

Load when: user asks 3-model consensus / 앙상블 / 다관점 토론 / 3모델 합의; material reversible
ambiguity after spec lock in high-stakes work; or `work/intent` routes INTERNAL_GATE.

Procedure (roles, pipeline, prompt shapes, artifacts): **skill `ensemble-consensus`** — this
guide holds only the policy.

- Use actual distinct transports when explicitly requested and available. If a requested transport is
  unavailable, report the blocker; never silently substitute 3-lens. Otherwise use 3 readonly lenses
  and call it 3-lens, never 3-model. Orchestrator owns `<consensus_decision>` and the reply.
- Debate, review, or consensus alone does not authorize implementation. Execute only when implementation
  is already authorized, all 3 SAFE verdicts name the identical candidate action, rollback, side effects,
  and evidence, and that candidate still satisfies DIRECT. The single implementer follows `work/models`;
  meta-config remains orchestrator-direct.
- For authorized implementation, execute the SAME turn → 3-lens verify → one gap-fill → one final
  re-verify; remaining gaps become one blocker/question. For review-only work, consensus is the result.
- Ending after consensus or verification without implementing is a failed turn only when implementation
  was already authorized and in scope.
- Bans: duplicate permission asks for already-authorized DIRECT work; calling 3-lens output "3-model";
  claiming implementation without a same-turn code change; multiple parallel implementers.
- **Autonomy gate:** exactly one round; each lens returns `SAFE | ASK | BLOCK` with the exact action,
  rollback, side effects, and evidence. Only **3/3 SAFE** on the identical DIRECT-eligible candidate
  permits same-turn execution when implementation was already authorized. Never retry,
  recurse, or repeat per file/command. Call this a 3-lens gate unless transports prove model diversity.
- Skip: user-specified one-liners/typos, explain-only, question-only turns.
