#!/usr/bin/env python3
"""Owner standing blocks: one runtime copy, deterministically.

Some owner context (delegation policy, personal-store map) must be present in EVERY turn's
context, and must survive compaction. Two carriers can supply it — the session-intent core
(re-injected each prompt) and this injector — so without a check the same text lands twice
and the two copies drift when one is edited.

The check is structural, not a judgment call: each block carries a stable marker
`[[clx:<name>]]`. If the marker is already in the session core, this injector stays silent.
No model call, no latency, no failure mode. Absent files simply yield no block.

Used by intent-lock.py (every prompt) and session-restore.py (right after compaction).
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

# `__file__` is absent under some loaders (exec of compiled source, some embedders);
# fall back to the installed hooks directory so the import can never be what breaks.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                if "__file__" in globals() else os.path.expanduser("~/.claude/hooks"))
from clx_host import TMP    # noqa: E402  one marker directory, shared by the shell and Python sides

USER_DIR = os.path.expanduser("~/.agents/user")
# (file, marker) — the marker string lives in the file itself, so a renamed block fails
# loudly here instead of silently double-injecting.
BLOCKS = (
    ("delegation.md", "[[clx:owner-delegation]]"),
    ("ontology.md", "[[clx:owner-ontology]]"),
)
TEMPLATE_SENTINEL = "TEMPLATE-UNFILLED"
MAX_BLOCK_BYTES = 200_000  # owner context is prose; anything larger is a mistake, not a block


def is_unfilled(text: str) -> bool:
    """True while the shipped sentinel still opens a line of its own."""
    return any(line.startswith(TEMPLATE_SENTINEL) for line in text.splitlines())


def available():
    """Blocks that exist, carry their marker, and are not still the shipped template."""
    out = []
    for name, marker in BLOCKS:
        path = os.path.join(USER_DIR, name)
        try:
            # utf-8-sig: a BOM would hide the leading TEMPLATE-UNFILLED line. Regular files
            # only, bounded read — a fifo or a huge file must not hang or balloon a hook that
            # runs on every prompt.
            # islink rejected too: a symlink planted here would inject whatever it points at.
            if (os.path.islink(path) or not os.path.isfile(path)
                    or os.path.getsize(path) > MAX_BLOCK_BYTES):
                continue
            with open(path, encoding="utf-8-sig") as fh:
                text = fh.read(MAX_BLOCK_BYTES)
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        # The distribution ships this folder as a skeleton; an unfilled file injects nothing.
        # Line-start only: prose that merely mentions the sentinel is not "unfilled".
        if marker in text and not is_unfilled(text):
            out.append((name, marker, path, text))
    return out


def missing_from(context: str):
    """Blocks whose marker is NOT already present in the given context text."""
    return [b for b in available() if b[1] not in (context or "")]


def render(blocks, header: str) -> str:
    if not blocks:
        return ""
    parts = [header]
    for name, marker, path, text in blocks:
        parts.append(f"--- owner context {marker} (source {path}; owner-curated, private) ---")
        parts.append(text.strip())
    return "\n".join(parts) + "\n"


def safe_key(value) -> str:
    """Turn any id into a filename-safe key. Ids are UUIDs in practice, but they land in a
    PATH: a slash escapes TMP, a NUL raises ValueError, a newline desynchronizes the Python
    and shell sides of the same marker. Sanitize, then append a digest so two different ids
    can never collapse onto one file. Empty in, empty out — callers skip on empty."""
    text = "" if value is None else str(value)
    if not text:
        return ""
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", text)[:100]
    return f"{safe}-{hashlib.sha1(text.encode('utf-8', 'surrogateescape')).hexdigest()[:8]}"


def sentinel(sid: str) -> str:
    return os.path.join(TMP, f"clx-standing-{safe_key(sid)}")


def already_sent(sid: str) -> bool:
    """Injected once per session: the text stays in context until compaction, and
    session-restore.py clears this so the post-compaction turn re-injects."""
    return bool(sid) and os.path.exists(sentinel(sid))


def claim(sid: str) -> bool:
    """Atomically claim the one injection for this session. O_CREAT|O_EXCL means two hooks
    racing on the same session cannot both decide to inject. Returns False when the claim is
    already taken, or when there is no usable id to key on (then nothing is injected)."""
    if not safe_key(sid):
        return False
    try:
        os.close(os.open(sentinel(sid), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        return True
    except FileExistsError:
        return False
    except OSError:
        return False


def mark_sent(sid: str) -> None:
    if not safe_key(sid):
        return
    try:  # O_NOFOLLOW: never write through a symlink planted at the sentinel path
        os.close(os.open(sentinel(sid),
                         os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW, 0o600))
    except OSError:
        pass


def clear_sent(sid: str) -> None:
    if not safe_key(sid):
        return
    try:
        os.unlink(sentinel(sid))
    except OSError:
        pass


if __name__ == "__main__":  # self-check: marker present → block is suppressed
    ctx = "".join(m for _n, m, _p, _t in available())
    assert missing_from(ctx) == [], "marker present but block still offered"
    assert len(missing_from("")) == len(available()), "empty context must offer every block"
    assert render([], "h") == ""
    _sid = "selftest-0000"
    clear_sent(_sid)
    assert not already_sent(_sid)
    mark_sent(_sid)
    assert already_sent(_sid), "sentinel must suppress the second injection"
    clear_sent(_sid)
    assert not already_sent(_sid), "compaction must re-arm the injection"
    print(f"standing-blocks OK ({len(available())} block(s) available)")
