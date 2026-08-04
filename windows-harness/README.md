# Windows harness

**Windows is first-class.** The same `common/` config payload installs, and the shipped
hook wiring is rewritten at install time so every registered hook actually runs on Windows.
Activation is per-OS: `install.ps1` applies `common/` + `windows-harness/` and skips
`macos-harness/`.

## Requirements

- **PowerShell 5.1+ or 7+** (Windows PowerShell or `pwsh`).
- **Python 3.x on PATH** (`py -3`, `python`, or `python3`) — required for the hooks.
  Without Python the install still succeeds, but hooks are **not** registered (they would
  break sessions), and the summary lists them as inactive until you install Python and re-run.

## Install

```powershell
# from the repo root
powershell -ExecutionPolicy Bypass -File windows-harness\install.ps1 -Check    # dry run
powershell -ExecutionPolicy Bypass -File windows-harness\install.ps1 -Apply    # install
powershell -ExecutionPolicy Bypass -File windows-harness\install.ps1 -Apply -Force   # merge into a populated ~\.claude
```

The installer:

- creates `%USERPROFILE%\.claude`, `.codex`, `.agents`, `.grok` and copies `common/` (merge — overwrites matching files, never deletes);
- preserves existing Grok settings and updates only `[sandbox] profile`, keeping a timestamped `config.toml.pre-clx-*` copy;
- copies the cross-platform hook ports (`windows-harness\hooks\*.py`) into `~\.claude\hooks\`;
- rewrites `__CLX_HOME__` (and `$HOME` in `hooks.json`) to your profile path with **forward slashes** (JSON-safe and accepted by the tools);
- detects the Python launcher and rewrites every hook command to run through it;
- refuses a non-empty `~\.claude` without `-Force`; configures **no** git remote, touches **no** credentials.

## How the hooks run on Windows

| Hook (event) | Mac form | Windows form | Registered on Windows? |
|---|---|---|---|
| `intent-lock.py` (UserPromptSubmit) | `…/intent-lock.py` (shebang) | `<py> "…/intent-lock.py"` | yes |
| `block-goal-tools.py` (PreToolUse) | shebang | `<py> "…"` | yes |
| `guard-destructive.py` (PreToolUse; codex too) | shebang | `<py> "…"` | yes |
| `precompact-guard.sh` (PreCompact) | `.sh` | `<py> "…/precompact-guard.py"` (port) | yes |
| `session-intent-archive.sh` (SessionEnd) | `.sh` | `<py> "…/session-intent-archive.py"` (port) | yes (no-op without the forgetforge plugin) |
| `auto-format.sh` (PostToolUse) | `.sh` | `<py> "…/auto-format.py"` (port) | yes |
| `selfcheck-stop.py` (Stop) | shebang | `<py> "…"` | yes |
| `statusline.sh` (statusLine) | `.sh` | `<py> "…/statusline.py"` (port; ponytail badge only if bash present) | yes |
| `sync-grok-model-config.py`, `session-intent.py` (codex) | `python3 "…"` | `<py> "…"` | yes |
| `disk-guard.sh`, launchd job (macOS) | `macos-harness/` | — | **no** (macOS-only, intentionally inactive) |

`<py>` is the detected launcher (`py -3` / `python`). If Python is absent, none of the above
are registered and `statusLine` is removed — sessions still start cleanly.

For an identical experience to macOS (bash hooks, ponytail status badge), run the POSIX
`install.sh` inside **WSL** against your WSL `$HOME`.
