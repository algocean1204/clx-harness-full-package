#!/usr/bin/env python3
"""Remove host-specific HOME and launchd namespace values from a copied tree."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape


if len(sys.argv) != 3:
    raise SystemExit("usage: home-tokenize.py <home> <root>")
home = sys.argv[1]
root = Path(sys.argv[2])
token = ("__CLX_" + "HOME__").encode()
username = Path(home).name
replacements = {
    home.encode(): token,
    json.dumps(home, ensure_ascii=False)[1:-1].encode(): token,
    escape(home, {'"': "&quot;", "'": "&apos;"}).encode(): token,
    f"com.{username}.".encode(): b"com.cluxion.",
}

for path in root.rglob("*"):
    if path.is_symlink() or not path.is_file():
        continue
    data = path.read_bytes()
    if b"\x00" in data:  # binary asset — byte-replacing HOME would corrupt it
        continue
    updated = data
    for value, replacement in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        updated = updated.replace(value, replacement)
    if updated != data:
        path.write_bytes(updated)

if username != "cluxion":
    prefix = f"com.{username}."
    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if not path.name.startswith(prefix):
            continue
        target = path.with_name("com.cluxion." + path.name[len(prefix):])
        if target.exists():
            raise SystemExit(f"portable namespace collision: {target}")
        path.rename(target)
