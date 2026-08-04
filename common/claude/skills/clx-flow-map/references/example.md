# One worked example — for density, not for copying

This is what "enough" looks like for an ordinary HTTP handler: **one diagram, a branch table of a
few rows, three path lines.** Anything more on a flow this size is padding.

## Input

```python
@app.post("/orders")
def create_order(req):
    validate(req)                                   # raises 400
    if not inventory.reserve(req.items):
        return 409
    if not payment.charge(req.card, req.total):
        inventory.release(req.items)
        return 402
    queue.enqueue("ship", req.id)
    email_worker.send_later(req.id)                 # after the response
    return 201
```

## Output

```
POST /orders
  → validate
  → inventory.reserve ─┬─ fail → 409
                       └─ ok → payment.charge
                                  ├ fail → inventory.release → 402
                                  └ ok → enqueue ship → 201
after: email worker (user wait 0)
```

| Point | Condition (as written) | Next |
|---|---|---|
| reserve | `not inventory.reserve(...)` | 409 |
| charge | `not payment.charge(...)` | release → 402 |
| charge | otherwise | enqueue → 201 |

```
① out of stock   validate → reserve ✗ → 409
② card declined  validate → reserve → charge ✗ → release → 402
③ happy path     validate → reserve → charge → enqueue → 201
```

## What the density rule looked like here

Three branch points, no parallel region, no subflow, no loop → the short form. No layer table (one
layer), no state-field map (no shared state), no closing summary (the diagram already is one). The
one thing that survives at every size is the branch table, because it carries the conditions.
