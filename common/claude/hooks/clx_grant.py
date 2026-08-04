#!/usr/bin/env python3
"""Owner grants: issue a challenge, burn it, mint the approval.

The split that makes this work:

  ISSUE  the agent runs `clx_grant.py issue "<exact command>"` and shows the printed line.
         Issuing grants nothing — it only reserves an unguessable id.
  ECHO   the owner sends that one line, and only that line. `intent-lock.py` (UserPromptSubmit,
         the one channel injected content cannot reach) burns the id and mints the ledger entry.
  SPEND  `guard-destructive.py` consumes the entry once, at PreToolUse, by hash. No conversation.

The minted hash comes from the OWNER'S text, never from anything stored at issue time, so an
agent that prints one command and files another gains nothing: whatever the owner actually sent
is what the guard will allow.

Honest limit: same UID, no cryptographic boundary — an agent that deliberately edits this file
or the guard defeats it. The id makes pasted text unable to mint; it does not make the harness
tamper-proof. Detection is the ledger itself: every mint is one append-only line, so a forged
entry is visible in `~/.claude/security/user-approvals.txt`. (The owner's config-doctor adds an
[approval integrity] check on top; it is wired to that machine's layout and is not shipped.)
"""
from __future__ import annotations

import datetime
import hashlib
import os
import re
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                if "__file__" in globals() else os.path.expanduser("~/.claude/hooks"))
from clx_host import TMP    # noqa: E402  one marker directory, shared by every hook

TTL_MIN = 60                # a challenge the owner never echoed stops being usable
ID = re.compile(r"^[A-Z0-9]{6}$")


def store_path():
    return os.environ.get("CLX_CHALLENGE_STORE") or os.path.join(TMP, "clx-challenges")


def ledger_path():
    return os.environ.get("CLX_APPROVAL_LEDGER") or os.path.expanduser(
        "~/.claude/security/user-approvals.txt")


def _now():
    return datetime.datetime.now().astimezone()


def _read():
    """[(id, issued_at)] for entries still inside the TTL; malformed rows are dropped."""
    live = []
    try:
        with open(store_path(), encoding="utf-8") as fh:
            rows = fh.read().splitlines()
    except OSError:
        return live
    for row in rows:
        cid, _, stamp = row.partition("\t")
        if not ID.match(cid.strip()):
            continue
        try:
            issued = datetime.datetime.fromisoformat(stamp.strip())
        except ValueError:
            continue
        age = (_now() - issued).total_seconds()
        # A future stamp — clock skew, a DST jump, or a tampered row — would otherwise never
        # expire, since a negative age is always "inside" the window. Allow a minute of skew.
        if -60 <= age <= TTL_MIN * 60:
            live.append((cid.strip(), stamp.strip()))
    return live


def _write(rows):
    tmp = f"{store_path()}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("".join(f"{cid}\t{stamp}\n" for cid, stamp in rows))
    os.replace(tmp, store_path())          # atomic; two hooks cannot tear the store


def ambiguous_target(command):
    """A reason the command does not name its own target, or ''.

    The hash proves WHICH command, not WHERE it runs. `git push --force origin main` echoed an
    hour later, from a different repo, is a different destructive act with the same bytes — so a
    grantable command has to carry its target rather than inherit it from the shell's cwd.
    """
    toks = command.split()
    # `FOO=1 git push …` puts the assignment first, so the head has to be found past any
    # leading VAR=value tokens — otherwise an env prefix walks straight around this check.
    while toks and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", toks[0]):
        toks = toks[1:]
    if toks and os.path.basename(toks[0]) == "git" and "-C" not in toks:
        return "git commands must name their repo: git -C /abs/path …"
    return ""


def issue(command):
    """Reserve an id and return the line the owner must echo back verbatim."""
    reason = ambiguous_target(command)
    if reason:
        raise ValueError(reason)
    cid = secrets.token_hex(3).upper()
    _write(_read() + [(cid, _now().isoformat(timespec="seconds"))])
    return cid, f"승인 {cid}: {command}"


def _claim(cid):
    """Atomically claim one id. O_CREAT|O_EXCL is indivisible on POSIX and Windows alike, so two
    hooks racing on the same challenge cannot both win — a plain read-check-write would let both
    mint, and "single-shot" is the whole point."""
    try:
        os.close(os.open(f"{store_path()}.used.{cid}",
                         os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        return True
    except OSError:          # already claimed, or the marker cannot be written — fail closed
        return False


def _prune_claims():
    """Claim markers are bounded by challenges issued; drop the ones past any usable TTL."""
    base = os.path.basename(store_path()) + ".used."
    directory = os.path.dirname(store_path()) or "."
    cutoff = _now().timestamp() - TTL_MIN * 60 * 2
    try:
        names = os.listdir(directory)
    except OSError:
        return
    for name in names:
        if not name.startswith(base):
            continue
        path = os.path.join(directory, name)
        try:
            if os.path.getmtime(path) < cutoff:
                os.unlink(path)
        except OSError:
            pass


def burn(cid):
    """Spend the id. True only if it was live AND this caller won the claim."""
    if not ID.match(cid or ""):          # the marker name is a PATH; never let junk shape it
        return False
    rows = _read()
    if not any(row[0] == cid for row in rows):
        return False
    if not _claim(cid):
        return False
    _write([row for row in rows if row[0] != cid])
    _prune_claims()
    return True


def mint(command):
    """Append the single-use approval the guard will consume. Owner text in, hash out."""
    digest = hashlib.sha256(command.encode("utf-8")).hexdigest()
    path = ledger_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"{digest} PENDING {_now().isoformat(timespec='seconds')} {command[:80]}\n")
    return digest


ECHO = re.compile(r"^\s*(?:승인|APPROVE)\s+([A-Z0-9]{6})\s*:\s*(\S.*?)\s*$")


def capture(prompt):
    """Mint from a real owner prompt. Returns a note for the model, or ''.

    Called by every surface's UserPromptSubmit hook (Claude `intent-lock.py`, Codex
    `session-intent.py`) so one implementation covers both. The whole prompt must be the single
    echoed line — that is what stops an approval buried in a pasted document from minting.
    """
    lines = [ln for ln in (prompt or "").splitlines() if ln.strip()]
    if len(lines) != 1:
        return ""
    match = ECHO.match(lines[0])
    if not match:
        return ""
    cid, command = match.group(1), match.group(2)
    if not burn(cid):
        return (f"APPROVAL IGNORED: challenge {cid} was never issued here, is older than "
                f"{TTL_MIN} minutes, or was already used.")
    mint(command)
    return (f"APPROVAL CAPTURED ({cid}): the guard will allow exactly `{command}` once. "
            "Run it now without asking again; report the result, not a question.")


if __name__ == "__main__":
    # A store that cannot be written is a real situation on a locked-down machine. Say so in one
    # sentence — a raw traceback is what this harness replaced everywhere else.
    if len(sys.argv) >= 3 and sys.argv[1] == "issue":
        try:
            _cid, _line = issue(" ".join(sys.argv[2:]))
        except ValueError as exc:
            print(f"clx_grant: {exc}", file=sys.stderr)
            sys.exit(2)
        except OSError as exc:
            print(f"clx_grant: cannot write the challenge store at {store_path()} "
                  f"({exc.__class__.__name__}) — no challenge was issued.", file=sys.stderr)
            sys.exit(2)
        print(_line)
    elif len(sys.argv) >= 2 and sys.argv[1] == "pending":
        try:
            print("\n".join(cid for cid, _ in _read()) or "(none)")
        except OSError:
            print("(store unreadable)")
    else:
        print("usage: clx_grant.py issue \"<exact command>\" | pending", file=sys.stderr)
        sys.exit(2)
