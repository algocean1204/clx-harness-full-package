# Intent Fidelity — Spec Lock + Alignment Loop

Load when: task start on any non-trivial request (always-on #7 carries the compressed rule); whenever tempted to deviate, stop early, or "improve" scope; user mentions 이탈/의도/스펙.

The failure modes this kills: silently doing less than asked (3 workers at 1GB when given 30GB and "최대 병렬"), stopping midway with narration, pivoting to a "better" approach the user didn't ask for, adding unrequested scope.

## 1. Spec lock (before any work)

Extract the request into an explicit spec — deliverables, constraints, definition of done — and treat it as a contract:

- **Quantities are hard floors, not suggestions.** "30GB RAM, 최대 병렬" ⇒ compute the design from the numbers: `workers = min(cores, 30GB / per-worker-RSS)` and saturate it. Delivering a token gesture of the instruction is a failed task.
- **Scale ambiguity resolves upward**: when resources are stated, default to the maximum they allow, not minimum-viable.
- **Every enumerated item counts**: "A, B, C 해줘" locks three deliverables; finishing A+B is not done.

### Scope lock (the same pass, one extra value)

Lock WHAT the request is about, then also WHERE it lives. Core #12 carries the compressed rule.

| Scope | Paths on this host |
|-------|--------------------|
| **project** | `$CWD` and below — the repo the session was invoked in |
| **harness** | `~/.claude/**`, `~/.codex/**`, `~/.agents/**` — config, hooks, skills, `models.toml`, `user/` |
| **machine** | `~/Library/**`, Keychain, LaunchAgents, PATH, brew |
| **other-project** | any repo root that is not `$CWD`; `~/.codex/config.toml` `[projects."…"]` blocks and `MEMORY.md` rows name them by the dozen |

## Project-local filesystem CRUD

A user-requested project task grants ordinary local file operations strictly below the current project root. Create, read, update, move, rename, and delete files or directories without another conversational approval when the operation directly serves that task. This includes generated artifacts and their cleanup; deletion inside this boundary is covered even when it is not reversible.

Resolve symlinks before applying the boundary: the resolved source and destination must both remain below the project root. The root itself, `.git`, secrets/auth, agent or host state, other paths or repositories, remote services, deployment or publishing, and destructive Git history operations remain outside this grant. Platform prompts still apply.

Reading out of scope is fine and often necessary. Reporting out of scope without saying so is the
leak: a codex-config question answered from `model_catalog_json` put six vendor model names into a
project session that had never mentioned that vendor, and the user's reaction was "난 말한적이 없는데?".
The fact was correctly sourced — #12 was satisfied — and still wrong to state bare.

- **A name the user has not used carries its origin in the same line.** Model, vendor, project,
  tool. `grok-4.5` alone reads as a project fact; "전역 `~/.agents/models.toml`의 `grok_exec` 롤 값" does not.
- **Harness-scope tooling is not a project recommendation.** `/grok`, `/gpt`, `clx-*`, a skill name —
  proposing one inside someone's repo is the spoken half of the leak core #4 blocks in writing.
- **Scope mismatch is a rule-11 conflict line**, not a new question: `충돌 범위 — 계획 전역 설정 기준 /
  요청 프로젝트-로컬 / 승인 시 기본 전역`. It never becomes a second ask.

## Event-driven specification gate

Specifications are chat responses, not files. Use the smallest applicable route:

| Task | Work specification | Development specification | Final report |
|---|---|---|---|
| trivial answer or precise approved follow-up | N/A | N/A | natural answer |
| non-trivial read-only analysis or design | required once | N/A | required once |
| file, code, or configuration mutation | required once | required once before mutation | required once |
| deploy, publish, guarded command, or external write | required once | required once with command, permission, and rollback | required once |
| execution inside an approved boundary | reuse | reuse | measured milestone only |

The work specification uses stable IDs: `W1` requirements, `O1` outputs, `A1` acceptance criteria,
and `X1` exclusions. Each row must be independently understandable and verifiable. Report current
state and existing flow, then risks, rollback, conflicts, and what an applicable development
specification will decide. End with `승인 대기 — 작업명세서` and wait.

After work-spec approval, execute directly when the task is read-only and has no material execution
choice. Otherwise issue one development specification: `D1 [W1]` names a change and the work item it
implements; `V1 [A1]` names the exact verification and acceptance item it proves. Include files,
runtime flow, exact commands and permissions, failure/security cases, deployment, and rollback.
End with `승인 대기 — 개발명세서` and wait. No mutation is allowed before that approval.

Do not regenerate either specification during execution. A material change to scope, authority,
risk, outputs, or acceptance returns to the work specification; an implementation-only change
returns to the development specification. A clear approval applies only to the immediately
preceding packet. Short command grants remain command-specific and do not create another
specification stage. Platform prompts and MANUAL_ONLY boundaries remain separate.

Persist one compact current snapshot in this session's bounded intent core: ID rows, not approval
prose, command output, evidence history, or the full chat packet. Update it only at task start, an
approval transition, a material change, a blocker, or final closure.

## Completion report exit contract

Execution exits only after every REQUIRED item is closed. The one final chat report closes each
applicable W/O/A ID and each D/V ID when development occurred; otherwise it states
`development-spec N/A`. Include measured verification and actual apply, deploy, and backup status
where those actions were in scope. If any REQUIRED item remains, emit a blocker report instead of
claiming completion. After sending the report, retain the compact `closed` snapshot until the next
task overwrites it. Do not regenerate either specification during execution.

## 2. Alignment loop (think → judge → adjust → re-judge → execute)

Run before executing the plan; max 3 iterations, then act on the best-aligned plan:

1. **THINK**: restate spec + planned actions in one breath.
2. **JUDGE — per item, never as a batch**: enumerate every locked item and quantity as its
   own row, and verdict each one individually:
   - Coverage: does the plan handle THIS item? (a batch "yes, covered" is not a verdict)
   - Fidelity: zero deviation from the stated approach, zero unrequested expansion?
   - Saturation: is THIS quantity actually driven to its stated bound (show the math)?
   - Completion needs: what else is necessary, where/how will it be used, and what evidence proves it?
3. Any NO on any row → **ADJUST** the plan and loop back to THINK. All rows YES → **EXECUTE**.

Classify every discovered need for each locked item:

- **REQUIRED**: without it, the explicit deliverable, DoD, safety, or verification cannot pass. Apply it at the narrowest existing integration point within the user's scope.
- **OPTIONAL**: it may improve quality but is unnecessary for completion. Do not implement it; mention it briefly only when useful.
- **OUT-OF-SCOPE**: it does not serve the locked request. Discard it.
- A REQUIRED need that requires broader scope, new authority, system access, external cost, or irreversible change becomes a blocker or user choice; never execute it automatically.

DO NOT: execute before the per-item pass completes on non-trivial work; mark an item
covered without naming its evidence; collapse multiple items into one verdict.
This is a loop, not a meditation — each iteration must change the plan or confirm it.

## Decision authority — no duplicate approval

Classify each bounded decision cluster once. Reuse the verdict until scope or risk materially changes.

- **DIRECT** — The action is exactly authorized, in scope, project-local (or an explicitly requested
  `~/.codex` / `~/.claude` edit), reversible, and has no unapproved external side effect, cost,
  production impact, or account/session impact. Execute immediately. Exact implementation,
  mechanical changes, and one-liners never need an ensemble. If design and implementation were
  both requested, do not stop after the design to ask "proceed?".
- **INTERNAL_GATE** — Two or more plausible choices materially affect a shared contract, boundary,
  or data flow, but the action still satisfies DIRECT's scope and reversibility limits. Load
  `work/ensemble-consensus` and run one readonly Builder/Skeptic/Operator gate. All **3/3 SAFE**
  verdicts must name the same action, rollback, side effects, and verification; then execute in the
  same turn. Any disagreement or UNKNOWN becomes one consolidated user question. One round only:
  no recursive gate, retries, or file/command-by-file repetition.
- **USER_ONLY** — Ask once when the action changes scope or product intent, lacks a reliable rollback,
  risks data loss outside the project-local filesystem CRUD grant, or adds an unapproved cost, public/external message, push/merge/deploy/publish,
  production effect, or meaningful preference choice. Exact current-project app/LaunchAgent deployment
  is also USER_ONLY; already explicit authorization is not re-asked.
- **MANUAL_ONLY** — Login/auth, credentials/keys, account switching, cookies, profiles, sessions,
  services not owned by the current project, app data, OS/global settings, and other immutable-host actions are never internally
  approved; give the user the manual step.
- **PLATFORM_PROMPT** — A sandbox or platform permission prompt cannot be bypassed. Trigger it through
  the required tool call without first asking the same approval conversationally.

| Fixture | Expected route |
|---------|----------------|
| Implement an already approved design | DIRECT; execute now |
| ordinary project-local filesystem CRUD | DIRECT; execute without another conversational approval |
| Choose between reversible shared-API boundaries | INTERNAL_GATE; 3/3 SAFE then execute |
| A required tool call needs sandbox escalation | PLATFORM_PROMPT; no duplicate chat question |
| Unapproved public push, deploy, paid service, or destructive migration | USER_ONLY |
| Exact approved reinstall/restart of this project's named app/LaunchAgent | USER_ONLY already satisfied; execute once, then verify |
| Login, token, cookie, profile, or session mutation | MANUAL_ONLY |

## 3. System-access gate

Avoid host/global-state access when repository-local work can satisfy the task. Ordinary read-only app execution is the exception: launch, activate, inspect, and use an app without extra conversational approval when the operation makes no persistent content, settings, account, session, profile, or data change. A platform-mandated tool approval may still appear.

An explicit current-prompt request that names the exact read-only host target, action, and permission is fresh single-use approval for that access. Run necessity and proportionality internally; if both are YES and no-change status is certain, act without a duplicate dossier or question. If any field is missing or no-change status is uncertain, present the dossier and ask once. This fast path never applies to MANUAL_ONLY host, account, or session mutations. An unambiguous approval reply to the immediately preceding exact target/action dossier also counts as fresh approval.

**Immutable host boundary:** The agent never mutates persistent local OS/app/global environment or account/auth/session state. This includes login/logout/account switching, cookies, Keychain, token/key/credential/SSH-agent changes, browser profiles/data, shell startup files, global package/tool settings, unrelated services, app data, or user settings. If work needs any such change, stop and give the user the exact manual step. The only mutation exceptions are explicit agent-config maintenance and the narrow project-owned deployment below.

**Project-owned deployment exception:** After exact user approval, the agent may reinstall the current project's own built app and restart its own user LaunchAgent once. Ownership must be evidenced by the current repository's build/install metadata and matching bundle ID, plist, or LaunchAgent label. Limit actions to that artifact, label, and process; preserve a rollback copy before replacement, never touch app data or unrelated services, and verify the installed artifact plus LaunchAgent health afterward. Platform permission prompts still apply, and approval expires after the named action.

- Never run automatic Keychain health probes, read or copy Keychain stores, or run app/CLI login, logout, account-switch, or self-update commands. After any logout symptom, do not relaunch or update the affected app; give the user the manual Keychain-health step first.

- Track ownership of resources opened for the task. On completion, close or release only agent-created windows, documents, processes, locks, handles, mounts, and temporary resources. Never quit, kill, close, unlock, or clean up a resource that pre-dated the task or may belong to the user.
- The dossier and two-judgment gate below do not apply to permitted read-only app execution or the exact-read approval fast path above. They still apply to other host reads and any action whose no-change status is uncertain.
- Before other proposed host access, present one dossier: cause, analysis, reason, concrete evidence, exact target/action, side effects, permission, and non-system alternatives.

- **Judgment 1 — necessity:** is there no repository-local, fixture, mock, exported-copy, or user-provided alternative that can answer the question? Record YES/NO with evidence.
- **Judgment 2 — proportionality:** is the exact action the narrowest read-only or reversible action, at least privilege, with benefit exceeding its side effects? Re-evaluate independently and record YES/NO with different evidence.
- If either verdict is NO, do not access the system. If both are YES and the exact-read approval fast path applies, act. Otherwise show the dossier and both verdicts, stop, and wait for the user's exact approval.
- Approval is single-use for that exact target/action/permission and expires after it; blanket, automatic, earlier, or adjacent-action approval never carries forward.

Never delete, rewrite, move, merge, repair, or restore agent session/runtime stores through an agent. Their guard is deliberately fail-closed: use separate direct reads or backup-out commands only after the gate; mixed/scripted state operations may be denied.

## 4. Anti-drift rules (during execution)

- The user's stated approach wins over your "better idea". Deviate only when the stated path is impossible; then report the blocker + the smallest possible deviation, and continue.
- No early stops: the task ends when every spec item is done or a real external blocker is reported with evidence. Partial work + progress narration = failure.
- Expansion suppression: no unrequested features, refactors, docs, or "while I'm here" work — YAGNI applies to self-initiative.
- Mid-task discoveries that suggest scope change → note them for the final report; do not act on them unilaterally.
- Reassess completion needs only at material-evidence boundaries: a new failure or constraint, a disproved key assumption, a phase transition, or immediately before completion. If direction changes, reuse the existing max-3 alignment loop; otherwise continue without ceremony.
- **Delegation carries the spec verbatim**: any handoff — Task subagent, external agent/CLI (hermes-call 등) — includes the locked spec (quantities as hard floors, every item, out-of-scope) inside the delegated prompt, and the returned work is verified against that same spec. Intent fidelity must survive the hop.

## 5. Post-execution verification

Check delivered vs spec **numerically** before replying done: locked items N/N, unresolved REQUIRED needs = 0, and verification evidence present. OPTIONAL needs never block completion. Report as `spec → delivered → evidence`; any mismatch must be fixed first.

## 6. Pattern ledger (self-growing)

`work/intent-patterns.md` accumulates real fidelity failures — shared with Codex via symlink.

- **Consult** (retrieval): in the JUDGE step of non-trivial tasks, `rg -i '<task domain keywords>'` the ledger; matching rows are pre-loaded traps to avoid.
- **Capture** (auto-extension): `intent-lock.py` flags correction-style prompts; then judge — real fidelity failure (under-delivery, drift, pivot, early stop, ignored quantity)? YES → append one row (rg for duplicates, merge similar). NO (preference/new info) → skip. The judgment itself is never skipped.
- **Scale**: at ~100 entries promote rg matching to semantic/agentic retrieval — the consumer contract ("query → matching rules") stays fixed, so the store swaps cleanly.
