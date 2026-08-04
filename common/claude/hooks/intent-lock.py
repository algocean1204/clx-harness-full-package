#!/usr/bin/env python3
"""UserPromptSubmit: proportional intent-fidelity injection + correction capture.

Proportionality: the heavy INTENT-LOCK block fires only for non-trivial prompts
(length >= 150, bracket payload, URL, or an imperative/task marker); short
conversational prompts get nothing extra. Correction-style prompts additionally get the
judge-then-append ledger pass. Never crash: malformed stdin exits 0 silently.
Protocol style follows two binding principles: per-item judgment over batch judgment,
and prohibition forms alongside imperatives.
"""
import json
import os
import re
import sys

try:
    data = json.load(sys.stdin)
    if not isinstance(data, dict):
        sys.exit(0)
    prompt = data.get("prompt")
    prompt = prompt.strip() if isinstance(prompt, str) else ""
except Exception:
    sys.exit(0)

# --- owner grant capture -----------------------------------------------------------------
# Claude UserPromptSubmit is the primary place a real owner prompt is visible. Codex may recover
# the latest real user_message from its trusted transcript when that event is skipped; both paths
# call the same capture implementation. The agent proposes `승인 <ID>: <exact command>`; the owner
# echoes that one line and nothing else; the ledger entry is hashed from the OWNER'S text, never
# from what the agent stored — so an agent that displays one command and files another gains
# nothing. The ID must have been issued this session, which is what stops text pasted from a
# file, a web page, or another model from minting anything.
# Runs BEFORE the proportionality gate below: an approval line is short by design.
# The rule itself lives in clx_grant.capture so Codex's UserPromptSubmit shares one implementation.
try:
    if prompt:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from clx_grant import capture as _capture_grant

        _note = _capture_grant(prompt)
        if _note:
            print(_note)
except Exception:   # a hostile id, a full disk — never let capture break the prompt
    pass

# Persistent session intent: re-inject every real prompt (even short acks —
# "이어서"/"계속해" are where direction gets lost) so it survives compaction.
# Written by skill `clx-session-intent`. Keyed PER LOGICAL SESSION (full UUID session_id
# via session_intent_paths.py) — never by cwd. This injects the single bounded core;
# longer evidence belongs in an explicit project handoff/checkpoint, not another
# session-state file. Never read another SID or cwd-legacy core. When this SID has no
# core yet, print one concise path hint so the session can create it on the first prompt.
try:
    if not prompt:
        raise ValueError
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from session_intent_paths import resolve, ROOT, LEGACY, LEGACY_DETAIL

    # One-time migration: hard-link the legacy shared file into recovery storage, then
    # remove the source only after the link exists. If a recovery name already exists,
    # leave the source untouched rather than overwrite either copy. Neither path is injected.
    try:
        os.makedirs(ROOT, exist_ok=True)
        for _source, _target in (
            (LEGACY, os.path.join(ROOT, "_legacy.md")),
            (LEGACY_DETAIL, os.path.join(ROOT, "_legacy.detail.md")),
        ):
            if not os.path.exists(_source):
                continue
            try:
                os.link(_source, _target)
            except FileExistsError:
                continue
            os.unlink(_source)
    except OSError:
        pass

    _dir, _core, _unused = resolve(hook_data=data)
    _intent = ""
    if _core:
        if os.path.isfile(_core):
            with open(_core, encoding="utf-8") as _f:
                _intent = _f.read().strip()
            if _intent:
                print(
                    f"SESSION-INTENT core (this session → {_core}; maintained per skill "
                    "clx-session-intent; read before the routed step):"
                )
                print(_intent)
                print()
        else:
            # Valid SID but no core yet: exact path hint only (never invent content).
            print(
                f"SESSION-INTENT: no core yet — create {_core} per skill clx-session-intent"
            )
            print()
    # Owner standing blocks: injected only when the session core does not already carry
    # their marker (single runtime copy; deterministic — see standing-blocks.py).
    # Once per session (the text stays in context afterwards); session-restore.py re-arms
    # it right after compaction, which is the only place it can actually be lost.
    try:
        import standing_blocks

        _sid = data.get("session_id") or ""
        _text = standing_blocks.render(
            standing_blocks.missing_from(_intent),
            "OWNER STANDING CONTEXT (private; do not repeat back verbatim):",
        )
        # claim() is the atomic once-per-session gate: two hooks racing on the same session
        # cannot both print. Render first so a claim is never spent on an empty injection.
        if _text and standing_blocks.claim(_sid):
            print(_text)
    except Exception:
        pass
except Exception:
    pass

CORRECTION = re.compile(
    r"아니야|아니라고|아니잖아|틀렸|그게 아니|왜 안 |왜 멋대로|하라고 했잖|라고 했잖아|"
    r"다시 해|다시해|제대로 해|빼먹|누락됐|누락했|멈추지 말|말라고 했|하지 말랬|시킨 대로|시킨대로"
)
# Korean puts the verb last, so a request is recognisable by its ENDING, not by a keyword. The
# original list only had `해줘`-shaped stems and therefore missed the three commonest real asks —
# `버그 고쳐`, `이 글 다듬어줘`, `테스트 돌려봐` — leaving exactly the under-specified work the
# rule-11 gate exists for with no gate at all. Measured on this session's own 75 prompts, the
# additions catch 10 more, all of them real work, and the trivial controls (알려줘, 보여줘,
# 이거 뭐야) stay quiet — bare `줘` is deliberately NOT here, since it would catch every question.
TASK = re.compile(
    r"해줘|하자|만들|수정|구현|분석|확인|작업|다듬|고쳐|고치|바꿔|바꾸|지워|삭제|옮겨|올려|내려|"
    r"보내|돌려|실행|설치|배포|정리|추가|제거|갱신|점검|검사|테스트|써줘|짜줘|"
    r"fix|implement|create|refactor|build|add|remove|update|deploy|install|run tests",
    re.I,
)
URL = re.compile(r"https?://|www\.", re.I)

if CORRECTION.search(prompt):
    print(
        "CORRECTION-CAPTURE: this prompt looks like a user correction. After handling it, judge: does it "
        "reveal an intent-fidelity failure (under-delivery, scope drift, unrequested pivot, early stop, "
        "ignored quantity)? If YES → append ONE table row to ~/.claude/guides/work/intent-patterns.md "
        "(rg for duplicates first, merge similar rows). If NO (mere preference/new info) → skip silently. "
        "Never skip the judgment itself."
    )

# Arm the Stop-time self-check for EVERY real prompt. It used to ride on the proportionality gate
# below, which conflated two different questions — "is this prompt worth injecting the heavy
# protocol text into?" and "should this turn be checked when it ends?". Measured against this
# session's own history, 22 of 70 real prompts never armed, including "더 다각도로 검사해봐" and
# the request that produced this fix: a third of real work ended unchecked. Whether the turn did
# anything is already answered independently by the mutation marker, so arming is unconditional
# and the heavy block stays proportional.
_pid = data.get("prompt_id")
if _pid:
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from standing_blocks import TMP as _tmp, safe_key as _safe_key

        _key = _safe_key(_pid)
        if _key:
            open(os.path.join(_tmp, f"clx-selfcheck-{_key}"), "w").close()
    except Exception:  # a hostile id, a full disk — arming is best-effort, never fatal
        pass

# Heavy INTENT-LOCK block: non-trivial prompts only (deterministic, no LLM).
# Skip short conversational prompts (< 150 chars, no task marker, no bracket) → nothing.
if not (len(prompt) >= 150 or '["' in prompt or URL.search(prompt) or TASK.search(prompt)):
    sys.exit(0)

print(
    "INTENT-LOCK: spec-lock this request. Judge PER ITEM, not as a batch — enumerate every asked "
    "item and quantity, then verdict each one (covered? evidence?) before executing; explicit "
    "quantities are hard floors to saturate. Loop think→judge→adjust (max 3). "
    "For each item classify completion needs as REQUIRED, OPTIONAL, or OUT-OF-SCOPE; use REQUIRED "
    "at the narrowest existing integration point, defer OPTIONAL, discard OUT-OF-SCOPE, and never "
    "finish with unresolved REQUIRED needs. Reassess only when material evidence changes direction. "
    "DO NOT: start before the per-item judge pass completes on non-trivial work; deliver partial "
    "items silently; pivot from the stated approach; stop early without a real blocker; treat a "
    "stated quantity as a suggestion. During long runs, post one-line milestone updates at phase "
    "boundaries (see clx-concise-report §interim). Consult guides/work/intent-patterns.md for known "
    "traps. Full protocol: guides/work/intent.md "
    "TWO-STAGE APPROVAL GATE (core rule 11): for a NEW approval-requiring task, first present the "
    "chat-only work specification and wait. After its approval, present the chat-only development "
    "specification and wait. No mutation or implementation command is allowed before development-"
    "spec approval; after it, execute autonomously inside the approved boundary. Material scope, "
    "authority, or risk changes return to the work specification; implementation-only changes "
    "return to the development specification. Trivial/direct-answer/read-only requests and precise "
    "approved follow-ups skip the gate. Full contract: guides/work/intent.md."
)
