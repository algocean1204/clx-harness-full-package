# Repository intents

TEMPLATE-UNFILLED — delete this line once you have filled the file in.

One row per repo you push to. Before pushing, check the row: content that belongs to a
PRIVATE row must never reach a PUBLIC one. When in doubt the answer is private.

| Repo | Visibility | Intent — what belongs here | Never here | Pipeline |
|---|---|---|---|---|
|  | PRIVATE / PUBLIC |  |  |  |

## Rules that follow from the table

1. A change touching both a private and a public repo lands in TWO commits, never one.
2. `~/.agents/user/` (this folder) never enters a public repo — the distribution ships only
   the empty template you started from.
3. Decide up front which repo may be force-pushed, and never widen that later by habit.
