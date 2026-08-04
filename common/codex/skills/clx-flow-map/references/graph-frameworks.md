# Graph and workflow frameworks

Load this only when the code builds an explicit graph (`StateGraph`, a workflow DAG, a step
machine). Everything here is about edges a reader cannot see from the node list alone.

## Enumerate conditional edges from the router, not the builder

A conditional edge is registered with a *function*, so the builder shows only its name. The branch
table needs the return values of that function, which means reading it:

```python
def after_prepare(state):
    return END if state.get("asked") else ["route", "persona"]

def pick(state):
    return "reason" if state.get("route") == "reason" else "empathy"
```

| Point | Condition (as written) | Next |
|---|---|---|
| after prepare | `asked` | END |
| after prepare | otherwise | `route` ‖ `persona` |
| dispatch | `route == "reason"` | reason |
| dispatch | otherwise | empathy |

Every key the router can return must appear. A router with three returns and a two-row table is an
incomplete read, not a simplification.

## The sibling-write trap

Two steps in the same parallel region do **not** see each other's state writes — they were
scheduled together, so each reads the state as it was before the region ran. Hanging a conditional
edge off each sibling therefore branches on stale values.

```
        ┌ route ┐
before ─┤       ├─ dispatch ─┬─ …      join FIRST, then branch
        └ persona ┘          └─ …
```

The fix is a join node (often an empty pass-through) whose only job is to be a place where both
writes are visible. When a graph has one of these, say so in a note under the diagram — it is the
single most common reason a drawn flow disagrees with observed behaviour.

## Loops

A loop edge (`rewrite → surface`) needs its exit condition on the diagram, not just the arrow.
Exits are usually a score threshold OR an attempt cap — record both:

```
combine ─┬─ score ≥ pass OR len(drafts) ≥ max_rounds → finish
         └─ otherwise → rewrite ↺
```

A loop with no stated exit is either a bug in the code or an unfinished read.

## Subflows

A subgraph compiled elsewhere (`build()` in another module) is one node in the parent and a whole
diagram of its own. Draw the parent with `▷ name`, then give the subflow its own section. Do not
inline it — that is how a fifteen-node limit turns into forty.

## After the response

Work started after the user already has their answer (memory writes, compaction, webhooks) belongs
outside the main box, labelled with the user's wait: zero. Readers consistently mistake this for
latency they are paying.
