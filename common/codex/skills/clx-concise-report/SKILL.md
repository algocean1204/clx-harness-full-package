---
name: clx-concise-report
description: >
  Token-efficient task reporting discipline — outcome first, core + reason + evidence only,
  hard length ceilings. Load for NON-TRIVIAL or multi-part reports (완료 보고, 결과 보고, 요약)
  or when report length/shape needs discipline; the always-on report rule already carries the
  default one-line report. Expand only when the user asks for detail (자세히).
---

# Concise Report

> Outcome first. Core + reason + evidence. Nothing else.

## Conclusion-first (두괄식) — applies to EVERY reply, not just reports

WHY it saves tokens: the reader (and any later turn quoting you) can stop at layer 1 — everything below becomes optional consumption instead of mandatory parsing.

**First-sentence formula**: [subject] + [verdict] + (one key number or cause). Fixed patterns by message type:

| Type | First sentence pattern |
|---|---|
| Completion | "X 완료 — <key result/number>." |
| Failure/blocker | "X 실패 — 원인은 Y." (failure first, cause second) |
| Question answer | "네/아니오/Z입니다." then reasoning |
| Diagnosis/analysis | "결론: X." evidence after |
| Recommendation | "권고: X." trade-offs after |
| Interim milestone | "▸ <phase>: <one-line result>." |

**Layering (inverted pyramid)**: L1 verdict (1 sentence) → L2 facts that change the reader's next action (≤5 bullets) → L3 evidence/numbers → L4 detail only on request. A lower layer may sharpen the verdict, NEVER reverse it — any caveat that would change the verdict belongs IN the first sentence.

**Pre-send self-test (3 questions)**: (1) If the reader stops after sentence 1, do they hold the correct conclusion? (2) Does sentence 1 contain a process verb instead of a verdict ("확인해보니…", "진행했으며…" → rewrite)? (3) Is a verdict-flipping caveat hiding below L1?

- Never open with background, restated request, headers, or throat-clearing.
- Questions get the answer first; failures state the failure first, then the cause.

## Shape (개조식 — mandatory above 4 lines)

A work report of **≥4 non-blank lines is ONE flat list**, never a paragraph block. Items are
noun-phrase: `- 항목 — 결과/수치`. No nesting. A table only for 3+ comparable rows; numbering
only when order carries meaning. Failures and unrun items go FIRST.

Exempt, because prose is the deliverable there: 1–3-line answers, design/gate text, refusals,
apologies, and explanations the user asked for. Measured on this harness's own history, the
ceiling was never the problem (0/12 over) — **prose blocks were** (3/12), so the shape rule is
where the leverage is, not the length rule.

Anti-cargo-cult: a bullet that would not change the reader's next action is not a bullet, it is
padding. `- 작업 — 완료됨` is the shape without the content; delete it.

## Structure (in order)

1. **Outcome line** — what happened / what was found, verdict first, one sentence.
2. **Core items** — only changes/findings that alter what the reader does next
   (≤5 bullets; a table only when 3+ items are genuinely comparable).
3. **Reason** — one line each, ONLY where a decision was non-obvious. Obvious choices
   get no justification paragraph.
4. **Evidence** — verification as numbers: `tests 12/12`, `70→61 lines`, `0 fail/0 warn`,
   `file:line`. Claims without numbers are narration, not evidence.
5. **Provenance** — a completion claim carries `- 검증 [측정] — <명령> → <출력 조각>`, the
   fragment **pasted from real output, never retyped**. Tag anything else: `[판단]` (derived),
   `[가정]` (premise), `[미확인](REQUIRED|OPTIONAL)` (not run), `[전달]` (a subagent's or the
   user's statement). A turn that changed something closes with `미검증:` — or `미검증: 없음`.
   The Stop hook measures this against the turn's actual tool calls, so an unrun check costs one
   word to admit and a blocked turn to hide.

## Approved-task completion

For a non-trivial task, the one final chat report is the exit contract. Keep it in chat; never
create a completion-report file unless the user explicitly requested one. Close the stable IDs
from the applicable specifications. If no development specification was needed, write
`development-spec N/A`; never invent `0/0`. Report only applicable rows in this flat shape:

```text
<task> 완료 — work-spec N/N · development-spec N/N|N/A · DoD N/N · verification N/N.
- 명세 충족 [판단] — W1 PASS, O1 DONE, A1 PASS; D1/V1 when applicable
- 적용·배포·백업 [측정] — <actual apply, deploy, and backup status>
- 검증 [측정] — <command> → <pasted output fragment>
미검증: 없음
```

Omit an apply, deploy, or backup row when it was out of scope; never add an empty success row.
If any unresolved REQUIRED item remains, use a blocker report and put the failure or unverified
item first. Never label that state completion, and never close a completion report with another
in-scope step or a continuation question.

## Hard length ceilings (unsolicited reports)

| Task size | Ceiling |
|-----------|---------|
| Trivial (one file, obvious change) | 1–3 lines |
| Standard | ≤10 lines |
| Large / multi-part | ≤20 lines, then offer "자세히 원하시면 전개합니다" |

The ceiling caps unsolicited length only — when the user asks 자세히/detail/why,
expand freely.

## Rules

- **Numbers over adjectives**: "1.7G→19M", never "much smaller". Deltas (before→after)
  over descriptions; `file:line` pointers instead of re-explaining content.
- **Omit entirely**: restating the request, tool-by-tool process narration ("~를 실행했고
  그 다음~"), hedging, self-praise, decorative headers on short reports, unsolicited
  next-step lists (offer next steps only when blocked or asked).
- **Intuitive first read**: the user must get the whole picture from the first 3 lines;
  everything after is support, not new surprises.
- **Required content survives compression**: goal/loop Cycle-report sections and the
  intent-fidelity `spec → delivered → evidence` check remain — in this compact form,
  not as prose essays.
- **Failures are never compressed away**: errors, skipped items, and unverified claims
  are reported plainly even if they break the ceiling.
- Report language follows the user's chat language (Korean here); identifiers stay as-is.

## Interim reporting (long runs, loops, goal mode)

Silence during a long run is a user-perspective bug; narration is too. The middle ground:

- During any run spanning multiple phases (roughly >10 tool calls or >3 minutes), post
  **one line per completed phase**: `▸ <phase>: <core result with a number>`.
  Example: `▸ 테스트: 3스위트 전부 [100%], 결함 0` — nothing more.
- Loop/goal iterations: milestone lines at phase boundaries INSIDE the iteration, plus the
  normal end-of-iteration report. Codex goal mode follows the same rule (see `work/goals`).
- DO NOT: narrate tool-by-tool; post a milestone for trivial steps; exceed one line per
  milestone; let a phase complete silently in a run the user is waiting on.

## Anti-pattern → fix

```
BAD : "먼저 설정 파일을 읽고, 훅을 등록한 뒤, 테스트를 진행했습니다. 테스트는
       성공적으로 완료되었으며, 전반적으로 훨씬 안정적인 구조가 되었습니다."
GOOD: "훅 등록 완료 — 테스트 3/3 통과 (settings.json:47, 발화 확인). 남은 리스크 없음."
```
