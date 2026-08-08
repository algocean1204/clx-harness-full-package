#!/usr/bin/env bash
# Install the clean agent harness into ~/.claude, ~/.codex, ~/.agents, ~/.grok.
# Copies the sanitized common/ payload and materializes the __CLX_HOME__ token to
# your real $HOME. It NEVER configures a git remote, installs launchd jobs (unless
# you pass --with-launchd), or touches auth/credentials.
#
# Usage:
#   ./install.sh --check                  # dry run: print the exact write scope
#   ./install.sh --apply                  # install (refuses a non-empty ~/.claude)
#   ./install.sh --apply --force          # install even into a populated ~/.claude (merge, never delete)
#   ./install.sh --apply --with-launchd   # also stage the macOS local-mirror launchd job (opt-in)
set -euo pipefail

ROOT=$(cd "$(dirname "$0")" && pwd -P)
COMMON="$ROOT/common"
MODE=""; FORCE=0; WITH_LAUNCHD=0
for arg in "$@"; do
  case "$arg" in
    --check) MODE=check ;;
    --apply) MODE=apply ;;
    --force) FORCE=1 ;;
    --with-launchd) WITH_LAUNCHD=1 ;;
    *) echo "install: unknown argument: $arg" >&2; exit 2 ;;
  esac
done
[ -n "$MODE" ] || { echo "usage: ./install.sh --check | --apply [--force] [--with-launchd]" >&2; exit 2; }
[ -d "$COMMON/claude" ] && [ -d "$COMMON/codex" ] && [ -d "$COMMON/agents" ] && [ -d "$COMMON/grok" ] && [ -d "$COMMON/local-bin" ] \
  || { echo "install: $COMMON is missing claude/codex/agents/grok/local-bin — run from the repo root" >&2; exit 1; }

PYTHON_BIN=$(command -v python3 || true)
[ -n "$PYTHON_BIN" ] || { echo "install: python3 is required (token materialization)" >&2; exit 1; }

OS=$(uname -s)
# src-under-common -> dest-under-HOME
MAP_SRC=("claude" "codex" "agents" "grok" "local-bin")
MAP_DST=("$HOME/.claude" "$HOME/.codex" "$HOME/.agents" "$HOME/.grok" "$HOME/.local/bin")

nonempty() { [ -d "$1" ] && [ -n "$(ls -A "$1" 2>/dev/null)" ]; }

# --- environment detection ---------------------------------------------------
# What is already on this machine decides what the install must PRESERVE. Printed in
# both modes so nothing about your setup changes silently.
detect_env() {
  echo "detected environment:"
  echo "  os          : $OS $(uname -m)"
  echo "  python3     : $PYTHON_BIN ($("$PYTHON_BIN" -c 'import sys;print(".".join(map(str,sys.version_info[:3])))' 2>/dev/null))"
  echo "  git         : $(command -v git >/dev/null 2>&1 && git --version | head -1 || echo 'MISSING (required)')"
  for cli in claude codex grok hermes-call clx-grok-delegate clx-ai-delegate; do
    if command -v "$cli" >/dev/null 2>&1; then
      echo "  $(printf '%-12s' "$cli"): $(command -v "$cli")"
    else
      echo "  $(printf '%-12s' "$cli"): not installed — features that need it stay off"
    fi
  done
  for d in "$HOME/.claude" "$HOME/.codex" "$HOME/.agents" "$HOME/.grok"; do
    if nonempty "$d"; then
      echo "  $(printf '%-12s' "$(basename "$d")"): EXISTING ($(find "$d" -type f 2>/dev/null | wc -l | tr -d ' ') files) — will be merged, never wiped"
    else
      echo "  $(printf '%-12s' "$(basename "$d")"): new"
    fi
  done
  for f in "$HOME/.claude/auth.json" "$HOME/.claude/.credentials.json" "$HOME/.codex/auth.json"; do
    [ -f "$f" ] && echo "  auth        : ${f#"$HOME"/} present — left untouched"
  done
  if [ -f "$HOME/.claude/settings.json" ]; then
    echo "  settings    : existing settings.json — YOUR keys are kept, our hooks are added"
  fi
  if [ -d "$HOME/.agents/user" ]; then
    echo "  user context: existing ~/.agents/user — filled files are never overwritten"
  fi
}

# Merge our settings into an EXISTING settings.json instead of replacing it: the user's own
# permissions, env, model pin and their own hooks stay; our hook registrations are added.
# The pre-merge file is copied aside first, so the change is always reversible.
merge_settings() {  # $1 = target (already holds the shipped file), $2 = snapshot of the user's previous file
  "$PYTHON_BIN" - "$1" "$2" "$HOME" <<'PY'
import json, sys
target_path, previous_path, home = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    live = json.load(open(previous_path, encoding="utf-8"))
    shipped = json.load(open(target_path, encoding="utf-8"))
except Exception:
    sys.exit(0)                      # unreadable either side: the plain shipped copy stands

merged = dict(shipped)
for key, value in live.items():
    if key != "hooks":
        merged[key] = value          # the user's own choices win outside hooks
# hooks: union, so neither side loses a registration. Compare on the MATERIALIZED form —
# the shipped file still says __CLX_HOME__ while an already-installed copy holds the real
# path, and without normalizing, every re-install would register everything a second time.
def key(hook):
    norm = {k: (v.replace("__CLX_HOME__", home) if isinstance(v, str) else v)
            for k, v in hook.items()}
    return json.dumps(norm, sort_keys=True)


hooks, seen = {}, {}
for source in (shipped.get("hooks", {}), live.get("hooks", {})):
    for event, entries in source.items():
        for entry in entries:
            fresh = [h for h in entry.get("hooks", [])
                     if key(h) not in seen.setdefault(event, set())]
            for h in fresh:
                seen[event].add(key(h))
            if fresh:
                hooks.setdefault(event, []).append({**entry, "hooks": fresh})
merged["hooks"] = hooks
json.dump(merged, open(target_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
open(target_path, "a", encoding="utf-8").write("\n")
print("settings.json: merged — your keys kept, harness hooks added")
PY
}

# Preserve existing Grok settings while enforcing the shipped sandbox profile and shared-root
# agent adapter. Both values come from common/grok/config.toml so policy has one source.
merge_grok_config() {  # $1 = shipped target, $2 = snapshot of the user's previous file
  "$PYTHON_BIN" - "$1" "$2" <<'PY'
import re, sys

target_path, previous_path = sys.argv[1], sys.argv[2]
shipped = open(target_path, encoding="utf-8").read()
previous = open(previous_path, encoding="utf-8").read()

def shipped_line(section, key):
    match = re.search(
        rf"(?ms)^\s*\[{re.escape(section)}\]\s*(?:#.*)?$\n(?P<body>.*?)(?=^\s*\[|\Z)",
        shipped,
    )
    value = re.search(rf"(?m)^\s*{re.escape(key)}\s*=.*$", match.group("body") if match else "")
    if not value:
        raise SystemExit(f"install: common/grok/config.toml is missing [{section}] {key}")
    return value.group(0)

enforced = {
    "agent": {"definition": shipped_line("agent", "definition")},
    "sandbox": {"profile": shipped_line("sandbox", "profile")},
}
lines, output, current = previous.splitlines(), [], None
seen_sections, seen_keys = set(), {section: set() for section in enforced}

def close_section():
    if current not in enforced:
        return
    for key, value in enforced[current].items():
        if key not in seen_keys[current]:
            output.append(value)
            seen_keys[current].add(key)

for line in lines:
    header = re.match(r"^\s*\[([^]]+)\]\s*(?:#.*)?$", line)
    if header:
        close_section()
        current = header.group(1)
        seen_sections.add(current)
        output.append(line)
        continue
    replacement = None
    if current in enforced:
        for key, value in enforced[current].items():
            if re.match(rf"^\s*{re.escape(key)}\s*=", line):
                if key not in seen_keys[current]:
                    replacement = value
                    seen_keys[current].add(key)
                break
    if replacement is not None:
        output.append(replacement)
    elif not (current in enforced and any(
        re.match(rf"^\s*{re.escape(key)}\s*=", line) for key in enforced[current]
    )):
        output.append(line)
close_section()
for section, values in enforced.items():
    if section in seen_sections:
        continue
    if output and output[-1]:
        output.append("")
    output.append(f"[{section}]")
    output.extend(values.values())

open(target_path, "w", encoding="utf-8").write("\n".join(output).rstrip() + "\n")
print("config.toml: merged — your Grok settings kept, shared-root adapter updated")
PY
}

if [ "$MODE" = check ]; then
  echo "clx-harness-full-package installer — DRY RUN (no changes)"
  echo "source : $COMMON"
  echo "target HOME : $HOME"
  echo
  detect_env
  echo
  echo "Would copy (merge; existing files overwritten, never deleted):"
  need_force=0
  for i in "${!MAP_SRC[@]}"; do
    src="$COMMON/${MAP_SRC[$i]}"; dst="${MAP_DST[$i]}"
    state="new"
    if nonempty "$dst"; then state="EXISTS/non-empty"; [ "${MAP_DST[$i]}" = "$HOME/.claude" ] && need_force=1; fi
    printf '  %-14s -> %s   [%s]\n' "common/${MAP_SRC[$i]}/" "$dst" "$state"
  done
  echo
  echo "Would materialize the __CLX_HOME__ token to: $HOME"
  echo "Would set +x on hook scripts under ~/.claude/hooks and ~/.codex/hooks"
  if [ "$WITH_LAUNCHD" = 1 ]; then
    if [ "$OS" = Darwin ]; then
      echo "Would stage launchd job -> $HOME/Library/LaunchAgents/com.$(id -un).agents-backup.plist (NOT auto-loaded)"
    else
      echo "launchd requested but host is not macOS ($OS) — would be SKIPPED"
    fi
  else
    echo "launchd job: NOT installed (pass --with-launchd to stage it, macOS only)"
  fi
  echo
  echo "Applies: common/ (cross-platform) + macos-harness/ (this OS: $OS)."
  echo "Skipped: windows-harness/ (Windows-only — use install.ps1 there)."
  echo "Will NOT: configure any git remote, push anywhere, or touch auth/credentials/Keychain."
  if [ "$need_force" = 1 ] && [ "$FORCE" = 0 ]; then
    echo
    echo "NOTE: ~/.claude is non-empty. --apply will REFUSE without --force."
  fi
  exit 0
fi

# ---- apply ----
if nonempty "$HOME/.claude" && [ "$FORCE" = 0 ]; then
  echo "install: ~/.claude already exists and is non-empty. Re-run with --force to merge into it." >&2
  echo "install: (merge overwrites matching files; it never deletes your data.)" >&2
  exit 1
fi

copy_tree() {  # $1 src dir, $2 dst dir
  mkdir -p "$2"
  # -R preserves the tree; we merge into an existing dst rather than wiping it.
  cp -R "$1/." "$2/"
  restore_write "$1" "$2"
}

# `cp` carries the source's mode across. A clone on a read-only mount, an unpacked release
# tarball, or a restrictive umask hands us 444 files — the copies land read-only and the token
# materialization below then dies half-installed. They are the user's own config now, so put the
# write bit back, walking the SOURCE listing so only files we just copied are touched.
restore_write() {  # $1 src dir, $2 dst dir
  # `! -type l`: chmod follows symlinks, so a link in the payload would otherwise let this
  # touch a file outside the install tree.
  (cd "$1" && find . -mindepth 1 ! -type l) | while IFS= read -r rel; do
    dst="$2/${rel#./}"
    [ -e "$dst" ] && chmod u+w "$dst" 2>/dev/null
  done
  return 0
}

# agents/user/ ships as an EMPTY template. Once you fill it in it is yours — a re-install
# (even with --force) must never overwrite it, so those files are copied no-clobber.
copy_user_tree() {  # $1 src .../agents/user, $2 dst ~/.agents/user
  [ -d "$1" ] || return 0
  (cd "$1" && find . -type f -print) | while IFS= read -r rel; do
    dst="$2/${rel#./}"
    [ -e "$dst" ] && continue
    mkdir -p "$(dirname "$dst")"
    cp "$1/${rel#./}" "$dst"
    chmod u+w "$dst" 2>/dev/null   # a read-only source would otherwise ship an unfillable template
  done
}
detect_env
echo

# An existing settings.json is the user's own configuration — merge into it rather than
# replacing it (their permissions/env/model pin survive; our hooks get registered).
LIVE_SETTINGS="$HOME/.claude/settings.json"
PREV_SETTINGS=""
_STAMP=$(date +%Y%m%d-%H%M%S)
if [ -f "$LIVE_SETTINGS" ]; then
  PREV_SETTINGS=$(mktemp)
  cp "$LIVE_SETTINGS" "$PREV_SETTINGS"
  cp "$LIVE_SETTINGS" "$LIVE_SETTINGS.pre-clx-$_STAMP"   # always reversible
fi

LIVE_GROK_CONFIG="$HOME/.grok/config.toml"
PREV_GROK_CONFIG=""
if [ -f "$LIVE_GROK_CONFIG" ]; then
  PREV_GROK_CONFIG=$(mktemp)
  cp "$LIVE_GROK_CONFIG" "$PREV_GROK_CONFIG"
  cp "$LIVE_GROK_CONFIG" "$LIVE_GROK_CONFIG.pre-clx-$_STAMP"
fi

# Instruction files are REPLACED, not merged — the harness router has to be the whole file for the
# rule imports to hold. settings.json was snapshotted for exactly that reason and these were not,
# so a user who had written their own CLAUDE.md or AGENTS.md lost it with nothing to restore from.
_KEPT_DOCS=""
for _doc in "$HOME/.claude/CLAUDE.md" "$HOME/.codex/AGENTS.md" "$HOME/.agents/AGENTS.md"; do
  if [ -f "$_doc" ]; then
    cp "$_doc" "$_doc.pre-clx-$_STAMP"
    _KEPT_DOCS="$_KEPT_DOCS ${_doc#$HOME/}.pre-clx-$_STAMP"
  fi
done

for i in "${!MAP_SRC[@]}"; do
  if [ "${MAP_SRC[$i]}" = "agents" ]; then
    # everything except user/ merges normally; user/ is preserved file-by-file
    tmp_agents=$(mktemp -d)
    cp -R "$COMMON/agents/." "$tmp_agents/"
    restore_write "$COMMON/agents" "$tmp_agents"   # else a 555 staged user/ cannot be removed
    rm -rf "$tmp_agents/user"
    copy_tree "$tmp_agents" "${MAP_DST[$i]}"
    rm -rf "$tmp_agents"
    copy_user_tree "$COMMON/agents/user" "${MAP_DST[$i]}/user"
    echo "installed: common/agents/ -> ${MAP_DST[$i]} (user/ template: existing files kept)"
    continue
  fi
  copy_tree "$COMMON/${MAP_SRC[$i]}" "${MAP_DST[$i]}"
  echo "installed: common/${MAP_SRC[$i]}/ -> ${MAP_DST[$i]}"
done

# Fold the user's previous settings back in (before token materialization, so the merged
# hook paths still get their __CLX_HOME__ resolved below).
if [ -n "$PREV_SETTINGS" ] && [ -f "$LIVE_SETTINGS" ]; then
  merge_settings "$LIVE_SETTINGS" "$PREV_SETTINGS" || \
    echo "install: settings merge skipped (kept the shipped file; your previous copy is at $LIVE_SETTINGS.pre-clx-*)"
  rm -f "$PREV_SETTINGS"
fi

if [ -n "$PREV_GROK_CONFIG" ] && [ -f "$LIVE_GROK_CONFIG" ]; then
  merge_grok_config "$LIVE_GROK_CONFIG" "$PREV_GROK_CONFIG"
  rm -f "$PREV_GROK_CONFIG"
fi

# Materialize __CLX_HOME__ -> real $HOME in every installed text file.
"$PYTHON_BIN" - "$HOME" "${MAP_DST[@]}" <<'PY'
import json, sys
from pathlib import Path
from xml.sax.saxutils import escape
home = sys.argv[1]
token = b"__CLX_HOME__"
raw = home.encode()
jsn = json.dumps(home)[1:-1].encode()          # json/toml string escaping
xml = escape(home, {'"': "&quot;", "'": "&apos;"}).encode()
for root in map(Path, sys.argv[2:]):
    for p in root.rglob("*"):
        if p.is_symlink() or not p.is_file():
            continue
        data = p.read_bytes()
        if token not in data or b"\x00" in data:
            continue
        suffix = p.suffix.lower()
        repl = jsn if suffix in {".json", ".toml"} else xml if suffix == ".plist" else raw
        p.write_bytes(data.replace(token, repl))
print("materialized __CLX_HOME__ ->", home)
PY

# Executable bits on hook scripts.
for hooks in "$HOME/.claude/hooks" "$HOME/.codex/hooks"; do
  [ -d "$hooks" ] || continue
  find "$hooks" -type f \( -name '*.sh' -o -name '*.py' \) -exec chmod +x {} +
done
find "$HOME/.local/bin" -maxdepth 1 -type f -name 'clx-*-delegate' -exec chmod +x {} + 2>/dev/null || true

# Optional launchd staging (macOS only, never auto-loaded).
if [ "$WITH_LAUNCHD" = 1 ]; then
  if [ "$OS" = Darwin ]; then
    owner=$(id -un)
    dest="$HOME/Library/LaunchAgents/com.$owner.agents-backup.plist"
    mkdir -p "$HOME/Library/LaunchAgents"
    # not sed: every sed delimiter is a character a HOME or a username may legally contain, and a
    # `#` or `&` in either one silently produces a broken plist
    HOME_VALUE="$HOME" OWNER_VALUE="$owner" python3 - "$ROOT/macos-harness/com.OWNER.agents-backup.plist" "$dest" <<'PY'
import os, sys
from xml.sax.saxutils import escape
src, dst = sys.argv[1], sys.argv[2]
text = open(src, encoding="utf-8").read()
text = text.replace("OWNER", os.environ["OWNER_VALUE"])
text = text.replace("__CLX_HOME__", escape(os.environ["HOME_VALUE"]))
open(dst, "w", encoding="utf-8").write(text)
PY
    echo "staged launchd job: $dest (local mirror only; no push)"
    echo "  to enable:  launchctl load $dest"
  else
    echo "launchd requested but host is not macOS ($OS) — skipped"
  fi
fi

# Model registry vs. what the backends actually serve. Pins are hand-written and go stale silently,
# so surface it at the one moment the user is already looking at install output.
# What this machine can and cannot do, before anything that depends on it. Nothing is installed
# for the user; an absent capability is reported and the feature that needed it stays off.
_host="$HOME/.claude/hooks/clx_host.py"
if [ -f "$_host" ] && command -v python3 >/dev/null 2>&1; then
  echo
  python3 "$_host" 2>&1 | sed 's/^/  /'
fi

_mrc="$HOME/.claude/hooks/model-registry-check.py"
if [ -x "$_mrc" ] && command -v python3 >/dev/null 2>&1; then
  echo
  echo "Model registry (roles whose CLI is absent are skipped):"
  # keep stderr: swallowing it turned a failing final check into a silent "Done"
  if ! python3 "$_mrc" 2>&1 | sed 's/^/  /'; then
    echo "  (the registry check could not complete — run it yourself: python3 $_mrc)"
  fi
fi

# The in-session first-run notice is injected into the AGENT's context, and a throwaway first
# session burns it before any human reads it. This is the one place the person installing is
# certainly looking, so the same fact is stated here too.
# -maxdepth first: GNU find warns when it follows another expression, BSD find does not care.
# xargs -r would be the obvious guard for an empty list, but it is a GNU extension — grep with no
# file argument would read stdin and hang, so the count runs through a real file list only.
_utpl=0
if [ -d "$HOME/.agents/user" ]; then
  _utpl=$(find "$HOME/.agents/user" -maxdepth 2 -name '*.md' ! -name 'README.md' \
    -exec grep -l 'TEMPLATE-UNFILLED' {} + 2>/dev/null | wc -l | tr -d ' ')
fi
if [ "${_utpl:-0}" -gt 0 ]; then
  echo
  echo "Optional next step: $_utpl template(s) under ~/.agents/user/ are still blank."
  echo "  Only filled files are ever injected; blank ones do nothing. Start with profile/identity.md."
  echo "  Never put tokens, passwords or keys in them."
fi

if [ -n "$_KEPT_DOCS" ]; then
  echo
  echo "Your previous instruction files were replaced by the harness router; copies kept at:"
  for _k in $_KEPT_DOCS; do echo "  ~/$_k"; done
  echo "  Anything you want to keep goes in ~/.agents/user/ or a project-level CLAUDE.md."
fi

echo
echo "Skipped: windows-harness/ (Windows-only — use install.ps1 there). Applied common/ (+ macos-harness/ launchd only with --with-launchd)."
echo "Done. Start Claude Code / Codex; public plugins load from the vendored local marketplace (~/.claude/plugins-vendored) — no network needed."
echo "Nothing was pushed and no git remote was configured."
