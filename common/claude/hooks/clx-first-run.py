#!/usr/bin/env python3
"""SessionStart: tell a brand-new installation what is still unconfigured — exactly once.

The installer prints host capabilities and the model registry, and the `~/.agents/user/` files
ship as blank templates that `standing_blocks` correctly refuses to inject. Nothing joined those
two facts INSIDE a session, so a fresh user's agent never mentioned that eight files are waiting.
The setup guide says it, but the guide is a document the owner hands over, not something the
install carries.

SessionStart stdout is the AGENT's context, not the user's terminal — so this is addressed to the
agent and asks it to relay, rather than speaking to a human who would never see it. The installer
prints the same fact to the human at the end of `install.sh`, which is the channel they are
actually reading.

Fires only while templates are still blank, at most once per install, and never for an owner whose
files are filled. Fail-open: any error exits 0 with no output.
"""
import json
import os
import sys

STAMP = ".clx-first-run-seen"
LIMIT = 8
READ_WINDOW = 200_000          # standing_blocks.MAX_BLOCK_BYTES — the two must agree or a file
                               # reads as configured here and is refused by the loader


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    # `clear` is how a new user most often lands in a blank session; resume/compact/fork already
    # carry the context. Documented sources: startup | resume | clear | compact | fork.
    if not isinstance(data, dict) or data.get("source") not in ("startup", "clear", None, ""):
        return 0

    user_dir = os.path.expanduser("~/.agents/user")
    if not os.path.isdir(user_dir):
        return 0                       # not installed, or the owner removed the tree deliberately
    # lexists, not exists: a DANGLING symlink at the stamp path reads as absent here and then
    # makes O_EXCL raise FileExistsError below, so the notice was suppressed forever with no
    # diagnostic. Either way a name is occupied — treat it as stamped.
    if any(os.path.lexists(p) for p in _stamp_paths()):
        return 0

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from standing_blocks import is_unfilled
    except Exception:
        return 0

    blank = []
    for root, dirs, names in os.walk(user_dir):
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
        for name in sorted(names):
            path = os.path.join(root, name)
            if not name.endswith(".md") or name == "README.md":
                continue
            # standing_blocks refuses to inject THROUGH a symlink, so a symlinked template is
            # never loaded no matter what it contains — reporting it as configured left the
            # owner's policy silently dead. Symlinking dotfiles out of the tree is ordinary.
            if os.path.islink(path):
                blank.append(os.path.relpath(path, user_dir) + " (심볼릭 링크 — 실제 파일이어야 주입됩니다)")
                continue
            # isfile before open: a FIFO named *.md blocks forever, and a SessionStart hook that
            # hangs is the one failure a session cannot absorb. standing_blocks guards the same way.
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8-sig", errors="replace") as handle:
                    # same window standing_blocks reads; a smaller one called a file configured
                    # that the loader would still reject, which is the same silent-dead outcome
                    if is_unfilled(handle.read(READ_WINDOW)):
                        blank.append(os.path.relpath(path, user_dir))
            except OSError:
                continue

    # Every template filled: a configured install says nothing. It is deliberately NOT stamped —
    # the blank state IS the trigger, so a reinstall or a reset template correctly speaks again.
    if not blank:
        return 0
    if not _claim():
        return 0                       # another session (or a subagent) already showed it

    shown = blank[:LIMIT]
    more = len(blank) - len(shown)
    print("[clx] 첫 실행 안내 — 아래 내용을 사용자에게 한 번 전달하세요 (이 안내는 한 번만 주입됩니다).\n"
          "  이 하네스는 " + str(len(blank)) + "개의 사용자 컨텍스트 템플릿이 아직 비어 있습니다. "
          "채운 파일만 실제로 동작하고, 안 채우면 아무 영향이 없습니다:\n"
          + "".join("    ~/.agents/user/" + b + "\n" for b in shown)
          + ("    … 외 " + str(more) + "개\n" if more > 0 else "")
          + "  가장 체감이 큰 것은 profile/identity.md (이름·git 계정·언어)입니다. "
            "토큰·비밀번호·키는 절대 넣지 마세요.\n"
          "  커맨드 목록은 /clx-help, 설치 상태와 모델 전환은 클론한 저장소의 setup-ui/server.py.\n"
          "  (English: these templates under ~/.agents/user/ are optional; fill only what you want, "
          "never secrets.)")
    return 0


def _stamp_paths():
    """`~/.agents` first; `~/.claude` is the fallback for a managed install whose agents tree is
    read-only, where a best-effort stamp would otherwise never take and the notice would repeat
    every single session."""
    return [os.path.join(os.path.expanduser("~/.agents"), STAMP),
            os.path.join(os.path.expanduser("~/.claude"), STAMP)]


def _claim() -> bool:
    """O_CREAT|O_EXCL, the same primitive standing_blocks.claim uses: SessionStart fires once per
    subagent, so a first turn that fans out would otherwise print N copies of this."""
    # O_NOFOLLOW is Unix-only. Naming it unguarded raised AttributeError inside main(), which the
    # top-level handler swallowed — so on Windows this hook was silently dead, and Windows has no
    # installer summary carrying the same fact either.
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    for path in _stamp_paths():
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | nofollow, 0o600)
        except FileExistsError:
            return False
        except OSError:
            continue                   # unwritable directory — try the fallback
        os.write(fd, b"first-run notice shown\n")
        os.close(fd)
        return True
    return True                        # nowhere to stamp: still inform, rather than stay silent


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
