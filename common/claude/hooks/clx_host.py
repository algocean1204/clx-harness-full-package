#!/usr/bin/env python3
"""One place that answers "what can THIS machine do", so no hook has to guess.

Every bug that only showed up on someone else's machine came from a hook touching a host
assumption directly: `stat -f%z` (BSD flags on a GNU box), a hardcoded `/tmp` that the Windows
port spelled differently, `import tomllib` on a 3.9 interpreter, `import fcntl` on Windows.
The fix is not another patch each time — it is that those questions have exactly one answer here,
and a missing capability degrades loudly instead of failing silently.

Nothing is ever installed on the user's machine: the harness promises to write only inside
~/.claude, ~/.codex and ~/.agents. A capability that is absent is REPORTED, not provisioned.

    python3 clx_host.py            # human-readable capability table
    python3 clx_host.py --json     # the same as JSON
    python3 clx_host.py --tmp      # the marker directory, for shell callers
"""
import json
import os
import shutil
import sys
import tempfile

__all__ = ["TMP", "marker", "which", "file_size", "require_posix", "capabilities", "report"]

# The single marker directory. POSIX pins /tmp so the bash hooks and the Python hooks agree even
# when TMPDIR is set (macOS gives each process its own TMPDIR); Windows has no /tmp at all, so the
# Python ports and the Python hooks both take the real temp dir.
TMP = "/tmp" if os.name == "posix" else tempfile.gettempdir()

# Optional tools. Absent means a feature is off, never that anything breaks.
OPTIONAL = {
    "codex": "the /gpt delegation target",
    "grok": "the /grok delegation target",
    "hermes-call": "Hermes delegation",
    "ruff": "Python auto-format on edit",
    "node": "prettier auto-format on edit",
    "git": "config backup and update",
    "rsync": "the local config mirror",
}


def marker(name):
    """A per-prompt marker path. The one spelling both the shell and Python sides use."""
    return os.path.join(TMP, name)


def which(tool):
    return shutil.which(tool)


def file_size(path):
    """No shell-out: `stat -f%z` is BSD and `stat -c%s` is GNU, and picking wrong returns 0 —
    which silently disabled the "skip files over 1MB" guard on every Linux machine."""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def require_posix(feature):
    """Fail with a sentence a person can act on instead of a bare ImportError three frames deep."""
    if os.name != "posix":
        sys.stderr.write(f"{feature} is POSIX-only and this host is {os.name}; "
                         "the rest of the harness is unaffected.\n")
        raise SystemExit(0)


def _python_floor():
    """The interpreter running the Python hooks. 3.9 is the floor the shipped code targets."""
    major, minor = sys.version_info[:2]
    return {"version": f"{major}.{minor}", "ok": (major, minor) >= (3, 9),
            "note": "" if (major, minor) >= (3, 9) else "below the 3.9 floor the hooks target"}


def _toml():
    for name in ("tomllib", "tomli"):
        try:
            __import__(name)
            return {"provider": name, "ok": True, "note": ""}
        except ModuleNotFoundError:
            continue
    return {"provider": None, "ok": True,
            "note": "no TOML parser; the registry falls back to a line reader"}


def capabilities():
    home = os.path.expanduser("~")
    writable = os.access(TMP, os.W_OK)
    return {
        "platform": {"os": os.name, "sys": sys.platform},
        "python": _python_floor(),
        "toml": _toml(),
        "marker_dir": {"path": TMP, "writable": writable,
                       "note": "" if writable else "markers cannot be written; the self-check is off"},
        "tools": {name: {"path": which(name), "ok": which(name) is not None, "enables": why}
                  for name, why in sorted(OPTIONAL.items())},
        "trees": {d: os.path.isdir(os.path.join(home, d))
                  for d in (".claude", ".codex", ".agents")},
    }


def report():
    cap = capabilities()
    lines = ["host capabilities (nothing is installed for you — absent means that feature is off)"]
    lines.append(f"  platform    : {cap['platform']['sys']} ({cap['platform']['os']})")
    py = cap["python"]
    lines.append(f"  python      : {py['version']}" + (f"  ⚠ {py['note']}" if py["note"] else ""))
    tm = cap["toml"]
    lines.append(f"  toml parser : {tm['provider'] or 'none'}" + (f"  — {tm['note']}" if tm["note"] else ""))
    md = cap["marker_dir"]
    lines.append(f"  markers     : {md['path']}" + ("" if md["writable"] else f"  ⚠ {md['note']}"))
    for name, info in cap["tools"].items():
        state = info["path"] if info["ok"] else f"not installed — {info['enables']} stays off"
        lines.append(f"  {name:<12}: {state}")
    missing = [d for d, present in cap["trees"].items() if not present]
    lines.append("  trees       : " + ("all present" if not missing else "MISSING " + ", ".join(missing)))
    return "\n".join(lines)


if __name__ == "__main__":
    if "--tmp" in sys.argv:
        print(TMP)
    elif "--json" in sys.argv:
        print(json.dumps(capabilities(), ensure_ascii=False))
    else:
        print(report())
