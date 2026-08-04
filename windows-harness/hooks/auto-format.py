#!/usr/bin/env python3
"""PostToolUse Edit|Write: format the edited file iff its project has a formatter config.

Cross-platform port of auto-format.sh (macOS/Linux keep the .sh; Windows uses this).
Fail-silent: any error leaves the file untouched and exits 0.
"""
import json
import os
import subprocess
import sys
from shutil import which

MARKERS = ("package.json", "pyproject.toml", "ruff.toml", "Cargo.toml", ".git")
PRETTIER_EXT = {".js", ".jsx", ".ts", ".tsx", ".css", ".scss",
                ".json", ".html", ".vue", ".svelte", ".md"}


def project_root(start: str) -> str:
    root = os.path.dirname(start)
    while True:
        if any(os.path.exists(os.path.join(root, m)) for m in MARKERS):
            return root
        parent = os.path.dirname(root)
        if parent == root:
            return root
        root = parent


def has_ruff_config(root: str) -> bool:
    if os.path.exists(os.path.join(root, "ruff.toml")):
        return True
    try:
        with open(os.path.join(root, "pyproject.toml"), encoding="utf-8") as fh:
            return "[tool.ruff" in fh.read()
    except OSError:
        return False


def has_prettier_config(root: str) -> bool:
    try:
        for name in os.listdir(root):
            if name.startswith(".prettierrc") or name.startswith("prettier.config."):
                return True
    except OSError:
        pass
    try:
        with open(os.path.join(root, "package.json"), encoding="utf-8") as fh:
            return "prettier" in json.load(fh)
    except (OSError, ValueError):
        return False


def run(cmd, cwd=None) -> None:
    try:
        subprocess.run(cmd, cwd=cwd, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=False)
    except OSError:
        pass


def main() -> None:
    try:
        data = json.load(sys.stdin)
        f = data.get("tool_input", {}).get("file_path", "")
    except (ValueError, AttributeError):
        return
    # self-check gate: mark that this prompt's turn mutated files (consumed by selfcheck-stop.py)
    pid = data.get("prompt_id", "")
    if pid:
        try:
            import tempfile
            open(os.path.join(tempfile.gettempdir(), f"clx-mutated-{pid}"), "w").close()
        except OSError:
            pass
    if not f or not os.path.isfile(f):
        return
    try:
        if os.path.getsize(f) > 1048576:  # skip >1MB generated bundles
            return
    except OSError:
        return

    root = project_root(f)
    ext = os.path.splitext(f)[1].lower()
    if ext == ".py" and which("ruff") and has_ruff_config(root):
        run(["ruff", "format", f])
        run(["ruff", "check", "--fix", "--quiet", f])
    elif ext == ".rs" and which("rustfmt") and os.path.exists(os.path.join(root, "Cargo.toml")):
        run(["rustfmt", f])
    elif ext in PRETTIER_EXT and has_prettier_config(root):
        npx = which("npx")
        if npx:
            run([npx, "--no-install", "prettier", "--write", "--ignore-unknown", f], cwd=root)


if __name__ == "__main__":
    main()
