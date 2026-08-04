#!/usr/bin/env python3
"""Run a command with a timeout and whole-process-group cleanup."""

from __future__ import annotations

import os
import select
import signal
import subprocess
import sys
import time


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: clx-bounded-run.py <seconds> <command>...", file=sys.stderr)
        return 2
    try:
        timeout = int(sys.argv[1])
    except ValueError:
        return 2
    if timeout < 1:
        return 2

    pid: int | None = None
    pgid: int | None = None
    status: int | None = None
    pending: int | None = None
    exit_seen = False
    exit_queue = None
    handled = tuple(
        sig for sig in (getattr(signal, "SIGHUP", None), signal.SIGINT, signal.SIGTERM)
        if sig is not None
    )

    def remember(signum: int, _frame: object) -> None:
        nonlocal pending
        if pending is None:
            pending = signum

    for sig in handled:
        signal.signal(sig, remember)

    gate_read, gate_write = os.pipe()
    try:
        pid = os.fork()
    except OSError as exc:
        print(f"clx-bounded-run: {exc}", file=sys.stderr)
        return 127
    if pid == 0:
        try:
            os.close(gate_write)
            os.setsid()
            while True:
                try:
                    token = os.read(gate_read, 1)
                    break
                except InterruptedError:
                    continue
            os.close(gate_read)
            if token != b"1":
                os._exit(125)
            for sig in handled:
                signal.signal(sig, signal.SIG_DFL)
            os.execvpe(sys.argv[2], sys.argv[2:], os.environ)
        except OSError as exc:
            print(f"clx-bounded-run: {exc}", file=sys.stderr)
        os._exit(127)

    os.close(gate_read)
    pgid = pid
    if not hasattr(os, "waitid"):
        if not hasattr(select, "kqueue"):
            os.close(gate_write)
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
            print("clx-bounded-run: no non-reaping process observer", file=sys.stderr)
            return 125
        exit_queue = select.kqueue()
        exit_queue.control(
            [
                select.kevent(
                    pid,
                    filter=select.KQ_FILTER_PROC,
                    flags=select.KQ_EV_ADD | select.KQ_EV_ENABLE,
                    fflags=select.KQ_NOTE_EXIT,
                )
            ],
            0,
            0,
        )

    def observed_exit() -> bool:
        nonlocal exit_seen
        assert pid is not None
        if exit_seen:
            return True
        if hasattr(os, "waitid"):
            try:
                exit_seen = os.waitid(
                    os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT
                ) is not None
                return exit_seen
            except InterruptedError:
                return False
        exit_seen = bool(exit_queue.control(None, 1, 0))
        return exit_seen

    def send(sig: int) -> None:
        assert pgid is not None
        try:
            os.killpg(pgid, sig)
        except (ProcessLookupError, PermissionError):
            pass

    def group_alive() -> bool:
        assert pgid is not None
        try:
            os.killpg(pgid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    def descendants_alive() -> bool:
        assert pid is not None and pgid is not None
        try:
            rows = subprocess.check_output(
                ["/bin/ps", "-axo", "pid=,pgid=,stat="], text=True
            )
        except (OSError, subprocess.SubprocessError):
            return True
        for row in rows.splitlines():
            fields = row.split(None, 2)
            if len(fields) != 3:
                continue
            child_pid, child_pgid, state = fields
            if int(child_pgid) == pgid and int(child_pid) != pid and not state.startswith("Z"):
                return True
        return False

    def reap() -> int:
        nonlocal status
        assert pid is not None
        if status is None:
            while True:
                try:
                    _, status = os.waitpid(pid, 0)
                    break
                except InterruptedError:
                    continue
        return status

    def clean(initial: int, grace: float = 1.0) -> None:
        for sig in handled:
            signal.signal(sig, signal.SIG_IGN)
        send(initial)
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            if observed_exit() and not descendants_alive():
                break
            time.sleep(0.02)
        send(signal.SIGKILL)
        reap()
        deadline = time.monotonic() + 1
        while group_alive() and time.monotonic() < deadline:
            time.sleep(0.02)

    def forward(signum: int, _frame: object) -> None:
        clean(signum, 0.2)
        raise SystemExit(128 + signum)

    for sig in handled:
        signal.signal(sig, forward)
    os.write(gate_write, b"1")
    os.close(gate_write)
    if pending is not None:
        forward(pending, None)

    deadline = time.monotonic() + timeout
    while not observed_exit() and time.monotonic() < deadline:
        time.sleep(0.02)
    if not observed_exit():
        clean(signal.SIGTERM)
        return 124

    clean(signal.SIGTERM)
    result = reap()
    if group_alive():
        return 125
    if os.WIFEXITED(result):
        return os.WEXITSTATUS(result)
    if os.WIFSIGNALED(result):
        return 128 + os.WTERMSIG(result)
    return 125


if __name__ == "__main__":
    raise SystemExit(main())
