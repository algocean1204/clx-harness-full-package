#!/usr/bin/env python3
"""Stop hook: ONE structural self-review per user prompt, only on turns that actually wrote files.

Gate = intent-lock flag (non-trivial prompt) AND mutation marker (PostToolUse Edit|Write).
Exit 2 + stderr is the only Claude-visible blocking channel on Stop; decision:block reason is user-only.
"""
import json
import os
import re
import sys
import tempfile

# `__file__` is absent under some loaders (exec of compiled source, some embedders);
# fall back to the installed hooks directory so the import can never be what breaks.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                if "__file__" in globals() else os.path.expanduser("~/.claude/hooks"))
from clx_host import TMP    # the single marker directory both the shell and Python sides use

# Ending a turn by NAMING the next step is the failure this catches: it is not a permission ask, so
# nothing forbade it, and the run just stopped after approval. Matched against the last few lines
# only — "다음은 검증 결과입니다" mid-report is a heading, the same words as a closer are a handoff.
HANDOFF_BUDGET = 3      # push back on a repeating handoff, but never trap a genuinely stuck turn

# Split by how much the phrase proves on its own. An explicit intent to continue or to ask is a
# handoff wherever it lands in the closing lines. "다음은 …" only proves it as the FINAL line —
# mid-report it is an ordinary heading ("다음은 측정치입니다"), and treating that as a handoff
# would nag every turn that reports numbers.
HANDOFF_INTENT = re.compile(
    r"이어서\s*(진행|하)|이어가겠|계속\s*(해서\s*)?(진행)?하겠|이어\s*진행"
    r"|진행하시겠|진행할까요|계속할까요|해\s*드릴까요|할까요\s*[?？]"
    r"|shall i (proceed|continue)|should i (proceed|continue)|do you want me to"
    r"|i'?(ll| will) (continue|proceed|keep going)|would you like me to",
    re.I,
)
# Naming the next WORK is a handoff wherever it sits in the closing lines.
HANDOFF_NEXT = re.compile(
    r"다음\s*(단계|작업|차례|순서)(는|은)|남은\s*(작업|것|단계|부분)(은|이)"
    r"|(작업|단계|부분)이?\s*남아\s*(있)?습니다"
    r"|next (step|thing|up)\b|still to (do|come)",
    re.I,
)
# A bare "다음은 …" is usually a heading ("다음은 측정치입니다"), so it only counts as the very
# last line — where there is nothing left for it to introduce except more work.
HANDOFF_TOPIC = re.compile(r"다음\s*(은|으로는)\b|^다음\s", re.I)
# "No remaining work" is the opposite of a handoff; only count it when nothing negates it.
REMAINING = re.compile(r"remaining work", re.I)
NEGATED = re.compile(r"(no|zero|없|없습니다|none)\W{0,12}remaining work|remaining work\W{0,12}(none|0|없)", re.I)


# The one sanctioned ending that names work left undone: a guarded op the owner has not granted.
# That is rule 7's user-only stop, not a handoff — the turn cannot proceed without a human, and
# the closer carries the exact line to send rather than a question. Everything else still counts.
SANCTIONED_STOP = re.compile(r"^승인\s*(필요|대기)|^APPROVAL (NEEDED|REQUIRED)", re.I | re.M)


def is_handoff(tail):
    lines = [ln for ln in tail.splitlines() if ln.strip()]
    if not lines:
        return False
    if SANCTIONED_STOP.search("\n".join(lines[-3:])):
        return False
    closing = "\n".join(lines[-2:])          # a closer can sit above a trailing courtesy line
    if HANDOFF_INTENT.search(tail) or HANDOFF_NEXT.search(closing):
        return True
    if HANDOFF_TOPIC.search(lines[-1]):
        return True
    return bool(REMAINING.search(closing)) and not NEGATED.search(closing)


def closing_lines(path, limit=3):
    """The LAST assistant entry's final text, or '' when there is none (no judgement, fail open).

    Deliberately not "the last text seen anywhere": if the final entry is tool_use only, falling
    back to an earlier block reads pre-tool narration ("다음은 파일을 수정하겠습니다") as the
    closer and flags a turn that ended perfectly well.
    """
    try:
        last_entry = None
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("type") == "assistant":
                    last_entry = entry
        if last_entry is None:
            return ""
        content = (last_entry.get("message") or {}).get("content")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            blocks = [b.get("text", "") for b in content
                      if isinstance(b, dict) and b.get("type") == "text"]
            text = blocks[-1] if blocks else ""
        else:
            text = ""
        lines = [ln for ln in text.splitlines() if ln.strip()]
        return "\n".join(lines[-limit:])
    except Exception:      # a corrupt or unreadable transcript must never cost the generic check
        return ""


# --- evidence: what actually ran this turn, written by auto-format.sh (PostToolUse) -----------
# The old nudge asked "did you REALLY finish?" and the agent answered itself — a prompt, not a
# measurement, which is exactly how a confident-but-wrong summary passed every control. These
# checks compare the closing text against the turn's recorded tool calls instead. They catch
# "claimed done, checked nothing" and "a command failed and the report says otherwise"; they
# cannot catch a wrong inference from a real result, and are not sold as if they could.
CLAIM_DONE = re.compile(
    r"완료|통과|성공|해결|수정했|반영했|끝났|\bdone\b|\bfixed\b|\bpassed\b|\bclean\b", re.I)
# `통과하지 못했습니다` and `not done` contain a success word while REPORTING A FAILURE. Without
# this, the gate demanded completion evidence from a report that said the opposite.
CLAIM_NEGATED = re.compile(
    r"(완료|통과|성공|해결|끝내지|하지)\s*(?:하지|되지)?\s*(?:못했|않았|못함|안\s*됨)"
    r"|\bnot\s+(?:done|fixed|passed|clean|complete)\b|\bfailed to\b", re.I)
# The failure vocabulary SUPPRESSES a finding, so it is deliberately generous: missing a real
# omission is far cheaper than blocking a report that did disclose the failure in other words.
CLAIM_FAIL = re.compile(
    r"실패|오류|에러|깨졌|깨짐|빨간|문제|결함|버그|막혔|차단|중단|안\s*됨|못했|미해결|남아\s*있"
    r"|\bblocked\b|\bfail(?:ed|ure|s)?\b|\berror\b|\bbroke\w*\b|\bred\b|\bdid not pass\b"
    r"|\bissue\b|\bregress\w*\b", re.I)
UNVERIFIED_LINE = re.compile(r"^\s*[-*]?\s*미검증\s*:", re.M)
# The provenance form rule 12 mandates for a completion claim. Its presence is what distinguishes
# "I checked and here is the output" from "I believe it works".
EVIDENCE_LINE = re.compile(r"\[측정\]|\[measured\]", re.I)


def closing_full(path):
    """Everything the assistant SAID this turn — every text block since the last user message.

    Not "the last assistant entry": at Stop time that entry is routinely a tool_use-only block,
    which yielded an empty string, so the evidence line was invisible no matter how carefully it
    was written and the nudge fired on every single turn that touched a file. The owner saw a red
    `Stop hook error` on finished, fully evidenced work and asked whether the hook was broken.
    It was.

    The lookback stops at the last user message, so this can never read a PREVIOUS turn's report
    and call it evidence. `closing_lines` deliberately keeps the last-entry-only rule — a handoff
    phrase lives in the closer, and pre-tool narration there would be a false positive.
    """
    try:
        texts = []
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                kind = entry.get("type")
                if kind == "user":
                    texts = []                     # a new turn began; drop the previous one
                    continue
                if kind != "assistant" or entry.get("isSidechain"):
                    continue                       # a subagent's text is not this turn's report
                content = (entry.get("message") or {}).get("content")
                if isinstance(content, str):
                    texts.append(content)
                elif isinstance(content, list):
                    texts.extend(p.get("text", "") for p in content
                                 if isinstance(p, dict) and p.get("type") == "text")
        return "\n".join(t for t in texts if t)
    except Exception:
        return ""


HARNESS_TREES = ("/.claude", "/.codex", "/.agents")
# A checkout of this config is harness scope by content and project scope by path — it lives at
# an ordinary path like any other repo. Without this the check fires on every session that works
# ON the harness, which is most of them, and a warning that cries wolf gets ignored. Found the
# honest way twice: it fired on the report announcing it, and then a replay over 100 real
# sessions classified ZERO as harness because only the distribution layout was covered — the
# private mirror puts the same trees at the root. Two markers together, never one: a lone
# `agents/AGENTS.md` could be coincidence, that plus a sibling `claude/hooks` is this config.
# The third pair is the home directory itself, where the trees are dotted. A session sitting in
# $HOME has no project at all, so "this reads as a fact about your project" has no subject — and
# it is where a config session actually runs: 10 of the 40 newest real sessions recorded exactly
# that cwd, this one included.
DISTRO_MARKERS = ((os.path.join("common", "agents", "AGENTS.md"),
                   os.path.join("common", "claude", "hooks")),
                  (os.path.join("agents", "AGENTS.md"), os.path.join("claude", "hooks")),
                  (os.path.join(".agents", "AGENTS.md"), os.path.join(".claude", "hooks")))


def _harness_scope(cwd):
    if any(t in (cwd or "") for t in HARNESS_TREES):
        return True
    path = os.path.abspath(cwd or ".")
    for _ in range(5):                 # a subdirectory of the checkout counts too
        for marker, sibling in DISTRO_MARKERS:
            if os.path.isfile(os.path.join(path, marker)) \
                    and os.path.isdir(os.path.join(path, sibling)):
                return True
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return False


def _global_names():
    """Proper nouns that live in harness-global registries and nowhere in a project.

    Only FULL ids and other-project directory names — never a bare vendor word. `grok-4.5` or
    `realTime_ASR` surfacing in a session that never named them is a leak with near-zero false
    positives; bare `gpt` is not, because a project that integrates one legitimately says it.
    ponytail: narrow on purpose — widen to vendor prefixes only if this set proves quiet.
    """
    names = set()
    home = os.path.expanduser("~")
    reg = os.path.join(home, ".agents", "models.toml")
    try:
        with open(reg, encoding="utf-8", errors="replace") as handle:
            names.update(re.findall(r'^\s*model\s*=\s*"([^"]+)"', handle.read(200_000), re.M))
    except OSError:
        pass
    cfg = os.path.join(home, ".codex", "config.toml")
    try:
        with open(cfg, encoding="utf-8", errors="replace") as handle:
            text = handle.read(2_000_000)
        for path in re.findall(r'^\[projects\."([^"]+)"\]', text, re.M):
            base = os.path.basename(path.rstrip("/"))
            if len(base) > 3:
                names.add(base)
        cat = re.search(r'^\s*model_catalog_json\s*=\s*"([^"]+)"', text, re.M)
        if cat:
            with open(os.path.expanduser(cat.group(1)), encoding="utf-8",
                      errors="replace") as handle:
                names.update(re.findall(r'"slug"\s*:\s*"([^"]+)"', handle.read(4_000_000)))
    except OSError:
        pass
    return {n for n in names if _distinctive(n)}


def _distinctive(name):
    """Specific enough that seeing it is evidence rather than coincidence.

    The raw registries yield `dataset`, `infra`, `codex`, `sonnet`, `opus` alongside `grok-4.5`
    and `Alpha_Pipeline` — the first group are words any project owns, and warning on them would make
    the check noise that gets ignored. A version digit, an underscore, or internal capitalisation
    is the cheap discriminator. ponytail: loosen only if a real leak slips through.
    """
    return (len(name) >= 6 and not name.startswith(".")
            and (any(c.isdigit() for c in name) or "_" in name
                 or any(c.isupper() for c in name)))


def user_text(path):
    """Everything the user actually typed this session, original case kept."""
    out = []
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("type") != "user":
                    continue
                content = (entry.get("message") or {}).get("content")
                if isinstance(content, str):
                    out.append(content)
                elif isinstance(content, list):
                    out.extend(p.get("text", "") for p in content
                               if isinstance(p, dict) and p.get("type") == "text")
    except OSError:
        pass
    return "\n".join(out)


def scope_bleed(report, transcript, cwd):
    """Harness-global names stated bare in a PROJECT session (core rule 12, scope clause).

    The fact is usually correct and correctly sourced — what is wrong is that it reads as a fact
    about the user's project. Real case: a codex-config question answered out of
    `model_catalog_json` put six vendor model ids into a session that had never named that vendor.
    Advisory only; a line that already carries its origin (a path, `전역`, `global`) is fine.
    """
    if not report or _harness_scope(cwd):
        return []                      # harness session: these names ARE the subject
    said = user_text(transcript)
    here = cwd or ""
    hits = []
    for name in sorted(_global_names()):
        # A name distinguished ONLY by its capitalisation (`DataSet`, `AlphaBot`) must match
        # case-SENSITIVELY — lowercased it collides with the ordinary English word and the check
        # becomes noise. Version-numbered and underscored names keep loose matching.
        exact = not any(c.isdigit() for c in name) and "_" not in name
        needle = name if exact else name.lower()
        hay_said = said if exact else said.lower()
        # the current project's OWN name is registered as a project too — naming it is not a leak
        if needle in hay_said or needle in (here if exact else here.lower()):
            continue
        for line in report.splitlines():
            if needle not in (line if exact else line.lower()):
                continue
            if "~/." in line or "/.codex" in line or "/.agents" in line \
                    or "전역" in line or "global" in line.lower():
                break                  # origin already named on the same line
            hits.append(f"`{name}` — 사용자가 이 세션에서 한 번도 쓰지 않은 이름")
            break
        if len(hits) >= 4:
            break
    return hits


def read_ledger(path):
    """[(tool, status, outlen, mutating, subject)] — best effort, never fatal."""
    rows = []
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 5:
                    rows.append(tuple(parts[:5]))
    except OSError:
        pass
    return rows


def evidence_gaps(report, rows):
    """Findings the LEDGER supports — each one names the row it came from.

    `report` is the WHOLE closing message, never the 3-line tail: a disclosed failure or the
    `미검증:` line usually sits in the body, and reading only the tail turned both into
    findings against a report that was already honest."""
    if not rows or CLAIM_NEGATED.search(report):
        return []
    gaps = []
    # only PROVEN mutations anchor the check: '?' marks a script whose effect is unknowable
    # statically, and treating it as a mutation would demand verification after every test run
    last_mut = max((i for i, r in enumerate(rows) if r[3] == "1"), default=-1)
    checked_after = [r for r in rows[last_mut + 1:] if r[3] == "0"]
    if CLAIM_DONE.search(report) and last_mut >= 0 and not checked_after:
        gaps.append(f"완료를 말했지만 마지막 변경({rows[last_mut][4][:60]}) 이후 "
                    f"검증 성격의 호출이 0건입니다")
    failed = [r for r in rows if r[1] == "err"]
    if failed and not CLAIM_FAIL.search(report):
        gaps.append(f"이 턴에서 {len(failed)}건이 실패로 기록됐는데 보고에 실패가 없습니다 "
                    f"(예: {failed[0][4][:60]})")
    silent = [r for r in rows if r[3] == "1" and r[2] == "0"]
    if CLAIM_DONE.search(report) and silent and not checked_after:
        gaps.append(f"무출력으로 끝난 변경 명령({silent[0][4][:60]})만으로 성공을 말했습니다 "
                    f"— exit 0은 종료 상태일 뿐 결과가 아닙니다")
    # Only when completion is actually claimed, and only for a report big enough that rule 8
    # asks for structure anyway. Demanding the line on every one-line fix would make
    # `미검증: 없음` a reflex signature, which is a one-word lie rather than a control.
    substantial = len([ln for ln in report.splitlines() if ln.strip()]) >= 4
    if (substantial and CLAIM_DONE.search(report) and last_mut >= 0
            and not UNVERIFIED_LINE.search(report)):
        gaps.append("변경이 있는 완료 보고에 `미검증:` 줄이 없습니다 "
                    "(없으면 `미검증: 없음` 한 줄)")
    return gaps


def main():
    if os.environ.get("CLX_SELFCHECK") == "0":
        return 0
    data = json.load(sys.stdin)
    pid = data.get("prompt_id") or ""
    if not pid:
        return 0
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from standing_blocks import safe_key  # same key on the Python and shell sides

    key = safe_key(pid)
    if not key:
        return 0
    flag = os.path.join(TMP, f"clx-selfcheck-{key}")
    mark = os.path.join(TMP, f"clx-mutated-{key}")
    counter = os.path.join(TMP, f"clx-handoff-{key}")
    if not os.path.exists(mark):        # nothing was actually done this turn
        return 0
    # A trivial prompt is never interrupted: the intent-lock flag has to have been there. It is
    # consumed on the first fire, so an already-started counter stands in for it afterwards.
    generic = os.path.exists(flag)
    if not generic and not os.path.exists(counter):
        return 0
    # stop_hook_active is set on every Stop after one blocks. Short-circuiting on it made the
    # handoff budget unreachable — one push per prompt, never the advertised three. The counter is
    # the real bound now, so only the GENERIC nudge defers to the flag's one-shot.
    if data.get("stop_hook_active"):
        generic = False
    if generic:
        os.unlink(flag)  # consume BEFORE emitting — a crash after this fails open, never loops
    # The generic nudge stays one-shot. A HANDOFF is different: the whole complaint is that it
    # repeats, so it gets its own budget — the marker stays put so later stops still see the work.
    tail = closing_lines(data.get("transcript_path") or "")
    handoff = is_handoff(tail)
    if handoff:
        try:
            with open(counter, encoding="utf-8") as handle:
                seen = int(handle.read().strip() or 0)
        except (OSError, ValueError):
            seen = 0
        if seen >= HANDOFF_BUDGET:      # never trap a turn that genuinely cannot proceed
            handoff = False
        else:
            try:
                with open(counter, "w", encoding="utf-8") as handle:
                    handle.write(str(seen + 1))
            except OSError:
                pass
    if not (handoff or generic):
        return 0
    core_clause = ""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from session_intent_paths import resolve
        _d, core, _u = resolve(hook_data=data)
        if core and os.path.isfile(core):
            core_clause = f" DoD source to re-read: {core}"
    except Exception:
        pass
    if handoff:
        sys.stderr.write(
            "SELF-CHECK — HANDOFF DETECTED (harness-injected, fires once per prompt): your closing "
            "lines name work that is still to be done:\n---\n" + tail[-500:] + "\n---\n"
            "If this run is already approved, naming a next step is proof a REQUIRED item is "
            "unfinished, and an unfinished REQUIRED item may not end a turn (core rule 7). DO THAT "
            "WORK NOW in this same turn, then any work it uncovers, until nothing in scope remains; "
            "do not re-report what is already done. The valid stops are only: this IS the core "
            "rule 11 two-stage approval gate (a NEW task awaiting work-spec or development-spec "
            "approval before execution — those approvals are the user's and this check never "
            "overrides them), the "
            "user must act (credential, physical device, an approval no rule grants you), or an "
            "external system is down. If one of those holds, say which in a single line and stop."
            + core_clause
        )
        return 2
    # Prefer a MEASUREMENT over a question wherever the ledger supports one.
    gaps, report = [], ""
    try:
        report = closing_full(data.get("transcript_path") or "")
        gaps = evidence_gaps(report, read_ledger(os.path.join(TMP, f"clx-evidence-{key}")))
    except Exception:
        gaps = []
    if not gaps:
        try:
            bleed = scope_bleed(report, data.get("transcript_path") or "",
                                data.get("cwd") or os.getcwd())
        except Exception:
            bleed = []
        if bleed:
            sys.stderr.write(
                "SELF-CHECK — SCOPE (advisory, measured against this session's user messages):\n"
                + "".join(f"  - {b}\n" for b in bleed)
                + "이 이름들은 전역 레지스트리(`~/.agents/models.toml`, `~/.codex/config.toml`)에서 온 값이고 "
                "지금 세션은 프로젝트 범위입니다. 사실 자체는 맞아도 프로젝트 사실처럼 읽히는 게 누출입니다 "
                "(core rule 12 범위 조항). 같은 줄에 출처 범위를 붙이거나 빼세요. 이미 출처를 밝혔거나 "
                "사용자가 전역 설정을 물은 경우라면 한 줄로 그렇다고 답하고 끝내면 됩니다." + core_clause
            )
            return 2
    if gaps:
        sys.stderr.write(
            "SELF-CHECK — EVIDENCE GAP (measured from this turn's tool calls, not a question):\n"
            + "".join(f"  - {g}\n" for g in gaps)
            + "Run the missing check now, or state it as `미검증: <항목> (REQUIRED|OPTIONAL)` — "
            "both end the turn cleanly; a retyped number does not. Completion evidence is "
            "`- 검증 [측정] — <명령> → <출력 조각>` pasted from real output (core rule 12)."
            + core_clause
        )
        return 2
    # A report that already carries this turn's measurement AND its `미검증:` line has answered
    # the generic question before it was asked — the evidence gate above just confirmed there is
    # nothing missing. Asking "did you REALLY finish?" there costs a whole extra turn and reaches
    # the owner as a red `Stop hook error` on work that was complete, which is how a useful check
    # becomes one people want switched off. The nudge stays for reports without that evidence.
    # The `미검증:` line is NOT part of this condition, and must not be: rule 8 exempts a trivial
    # one-line 완료 report from it, and `evidence_gaps` above already encodes those exemptions —
    # it just returned none. Restating the demand here would both duplicate that gate and fire on
    # the very reports it deliberately lets through (`수정 완료 — 12/12 통과.`).
    if EVIDENCE_LINE.search(report):
        return 0
    # Name what is actually absent. "did you REALLY finish?" alone reads as a nag on work that
    # looks finished, and the client renders it as a red hook error — the owner saw exactly that
    # and asked whether it was a malfunction. One concrete missing item is actionable; a
    # rhetorical question is not.
    sys.stderr.write(
        "SELF-CHECK (harness-injected, fires once per prompt). This turn changed files and the "
        "closing report carries no `- 검증 [측정] — <명령> → <출력 조각>` line.\n"
        "Re-read the user's request and enumerate every asked item with its verification evidence. "
        "If any item is unfinished or unverified: finish it now with the minimal change — no new scope, "
        "no over-engineering. A turn ends only when every REQUIRED item is done or genuinely blocked "
        "on the user or an outage; 'next is X' and 'I'll continue' are not endings. If you are waiting "
        "on the user (design-gate approval, a clarifying question, a blocked decision): stop now; this "
        "check does not apply. If the work IS done, do not repeat the report — add only the missing "
        "line above and stop." + core_clause
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)  # a broken Stop hook must fail open
