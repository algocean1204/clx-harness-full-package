---
name: clx-report-policy
description: >
  Governs WHEN a work report may become a FILE and where it lives — chat-first default,
  importance gate, single rolling worklog for ephemera, TTL pruning, retro-cleanup of
  accumulated report piles. Use whenever about to create ANY report/summary/completion
  document (보고서, 결과 문서, 완료 문서, 작업 로그), and when cleaning existing report
  clutter. Pairs with `clx-concise-report` (which governs chat-report FORM).
---

# Report Policy (file governance)

> A report is chat by default. A report FILE must earn its existence through the gate
> below — "I did work, so I'll leave a document" is never a reason.

## Decision tree (run in order, stop at first verdict)

**STEP 0 — Is it actually a report?**
A DELIVERABLE the user commissioned (design doc, spec, audit, DESIGN.md, migration plan)
is not a report — normal file rules apply (`docs/`), exit this policy.
A REPORT describes work that was done. Continue.

**STEP 1 — Chat-first gate.**
Did the user explicitly ask for a file, OR does another session/person need this as a
handoff artifact? NO → deliver in chat using `clx-concise-report` form. **No file. STOP.**

**STEP 2 — Importance classification** (file is warranted; classify it):
IMPORTANT iff ANY of:
- records a decision with lasting consequence (architecture choice, contract, tradeoff)
- is a handoff another session/person will load to continue work
- the user named it or will reference it later ("그 보고서")
Otherwise EPHEMERAL (progress notes, verification dumps, iteration logs).

**STEP 3 — Placement (exactly one destination):**
- IMPORTANT → `docs/reports/YYYY-MM-DD-<topic>.md`, git-tracked, **max one file per task**.
  Body follows clx-concise-report form (outcome → core → reason → evidence), ≤1 page default.
- EPHEMERAL → **append** to the repo-local rolling worklog `.reports/WORKLOG.md`
  (ensure `.reports/` is gitignored) under a `## YYYY-MM-DD HH:MM <topic>` heading.
  **Never a new file.** If WORKLOG exceeds ~1,000 lines, drop the oldest half.

## Hard prohibitions

- No `REPORT.md` / `SUMMARY.md` / `COMPLETION_REPORT.md` / `VERIFICATION_*.md` scattered
  at repo root or per task.
- No report files inside `src/` or alongside code.
- No duplicating the chat report into a file "for the record" — chat IS the record
  (transcripts persist); git history IS the change record.
- No per-iteration files in loops — loops append to the WORKLOG at most.

## Retention

- EPHEMERAL: `hooks/report-prune.sh` trims WORKLOG entries older than 14 days. It is MANUAL —
  run it on request. No timer and no hook calls it; the backup chain deliberately excludes
  host/project maintenance (see the enforcement map below, which this line used to contradict).
  Prune scans `.reports/WORKLOG.md` under your report roots — `~/Documents` by default, or
  the colon-separated `CLX_REPORT_ROOTS` if you set it (maxdepth 8) — WORKLOGs
  outside those roots are not auto-pruned.
  Deleting a pruned entry is safe by definition — anything that mattered should have been IMPORTANT.
- IMPORTANT: git-managed; never auto-deleted.

## Retro-cleanup of existing piles

1. Scan: `rg --files -g '*{REPORT,SUMMARY,VERIFICATION,COMPLETE,RESULT}*.md' -g '20??-??-*.md'`
   plus root-level dated md files.
2. Classify each via STEP 2. IMPORTANT → move to `docs/reports/` (dated rename).
   EPHEMERAL → fold a 3-line digest into `.reports/WORKLOG.md`, delete the file.
   Duplicate of chat/git history → delete.
3. Report the counts (moved / folded / deleted) in chat — not in a new file.

## Enforcement map (this machine)

- Codex (worst offender): AGENTS.md always-on carries the one-line rule; this skill is the detail.
- Claude: CLAUDE.md always-on #8 (chat form) + this gate for files.
- Pruner: `~/.claude/hooks/report-prune.sh` — MANUAL (run on request; the backup chain deliberately excludes host/project maintenance).
