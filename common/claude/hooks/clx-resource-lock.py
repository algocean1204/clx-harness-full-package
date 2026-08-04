#!/usr/bin/env python3
"""Run one command under a stable, resource-scoped advisory lock."""

from __future__ import annotations

import argparse
import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from clx_host import require_posix  # noqa: E402

# fcntl does not exist on Windows; a bare import here died three frames deep with no
# hint that only THIS feature is unavailable.
require_posix('clx-resource-lock.py')

import fcntl
import hashlib
import os
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True)
    resource = parser.add_mutually_exclusive_group(required=True)
    resource.add_argument("--path")
    resource.add_argument("--resource")
    parser.add_argument("--timeout", type=float, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if args.timeout < 0 or not args.command or args.command[0] != "--":
        parser.error("a non-negative timeout and -- command are required")
    command = args.command[1:]
    if not command:
        parser.error("command is required")

    value = os.path.realpath(args.path) if args.path else args.resource
    marker = f"{args.kind}:{value}"
    digest = hashlib.sha256(f"{args.kind}\0{value}".encode()).hexdigest()
    root = Path(f"/tmp/cluxion-resource-locks-{os.getuid()}")
    root.mkdir(mode=0o700, exist_ok=True)
    os.chmod(root, 0o700)
    lock_path = root / f"{digest}.lock"
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    os.chmod(lock_path, 0o600)

    deadline = time.monotonic() + args.timeout
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() >= deadline:
                print(f"resource_busy: {args.kind}", file=sys.stderr)
                return 75
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))

    os.set_inheritable(fd, True)
    os.environ["CLX_RESOURCE_LOCK_HELD"] = marker
    os.environ["CLX_RESOURCE_LOCK_FD"] = str(fd)
    os.execvpe(command[0], command, os.environ)
    return 127


if __name__ == "__main__":
    raise SystemExit(main())
