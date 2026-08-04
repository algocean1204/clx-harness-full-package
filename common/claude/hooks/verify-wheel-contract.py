#!/usr/bin/env python3
"""Verify wheel Name/Version metadata against its canonical pyproject.

MANUAL tool — no hook or script calls it. Run it by hand during a cluxion plugin release
(guides/work/cluxion.md step 3) when a stale-wheel install is suspected.
"""

from __future__ import annotations

import email
import re
import sys
import zipfile

try:
    import tomllib                     # 3.11+
except ImportError:                    # the shipped floor is 3.9 (stock macOS)
    tomllib = None


def normalize(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def read_version(project: str) -> str:
    """`[project] version` out of pyproject.toml, without requiring a TOML parser.

    The stock interpreter on macOS is 3.9 and `tomllib` landed in 3.11; the regex reads the same
    line the release pipeline already reads with awk, and only inside the `[project]` table so a
    `[tool.x] version` cannot be picked up by mistake."""
    if tomllib is not None:
        with open(project, "rb") as handle:
            return tomllib.load(handle)["project"]["version"]
    with open(project, encoding="utf-8") as handle:
        text = handle.read()
    table = re.split(r"^\[", text, flags=re.M)
    for chunk in table:
        if chunk.startswith("project]"):
            found = re.search(r'^\s*version\s*=\s*"([^"]+)"', chunk, re.M)
            if found:
                return found.group(1)
    raise SystemExit(f"no [project] version in {project}")


def main(arguments: list[str]) -> int:
    if not arguments or len(arguments) % 3:
        raise SystemExit("usage: verify-wheel-contract.py WHEEL PYPROJECT NAME [...]")
    for index in range(0, len(arguments), 3):
        wheel, project, expected_name = arguments[index:index + 3]
        expected_version = read_version(project)
        with zipfile.ZipFile(wheel) as archive:
            metadata = [
                name for name in archive.namelist()
                if name.endswith(".dist-info/METADATA")
            ]
            if len(metadata) != 1:
                raise SystemExit(f"wheel METADATA count mismatch: {wheel}")
            message = email.message_from_bytes(archive.read(metadata[0]))
        if normalize(message["Name"]) != normalize(expected_name):
            raise SystemExit(f"wheel name mismatch: {wheel}: {message['Name']}")
        if message["Version"] != expected_version:
            raise SystemExit(
                f"wheel version mismatch: {wheel}: "
                f"{message['Version']} != {expected_version}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
