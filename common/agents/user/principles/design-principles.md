# Design principles — REQUIRED reading before environment/config changes

TEMPLATE-UNFILLED — delete this line once you have made these yours.

Your constitution for modifying this harness. When a change conflicts with one of these,
stop and surface the conflict instead of proceeding. The distribution's own reasoning is
summarized in `PRINCIPLES.md` at the repo root — start from it, then edit freely: this file
is the one the agent obeys on YOUR machine.

1. **Single source of truth.** One canonical home per fact; everything else routes to it.
2. **Load on demand.** Nothing is always-on unless it earns it; prove the cost.
3. **Evidence before assertion.** Read or grep before claiming; cite the file.
4. **Vendored upstream stays pristine.** Customize at install time, not in vendored bodies.
5. **Public/private hard separation.** Personal state never enters a public repo, and a test
   enforces it rather than your memory.
6. **Minimal diff, but never skip comprehension.**
7. **Every policy change lands with its test.**
8. **Deploy discipline.** Decide what may be force-pushed, and how approval is recorded.
9. **Cross-platform first-class.** If you use two OSes, both get verified.
10. **Reversibility by default.** Back up rather than delete; leave an escape hatch.
