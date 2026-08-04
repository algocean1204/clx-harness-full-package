#!/bin/bash
# Slim plugin caches (Claude + Codex) for directory-source plugins (cluxion):
# directory installs copy .venv/target/dist wholesale and keep old versions —
# runtime only needs plugin.json + skills/ + commands/ (CLIs live on PATH as uv tools).
# Safe by construction: CLAUDE_PLUGIN_ROOT refs in cluxion md files point only into
# skills/ (e.g. supercoder commands/supercoder.md), which slim always keeps.
set -euo pipefail

slim_root() {
  local CACHE="$1"
  [ -d "$CACHE" ] || return 0
  local before after
  before=$(du -sk "$CACHE" | awk '{print $1}')

  for plugdir in "$CACHE"/clx-*/*/ "$CACHE"/cluxion-*/*/; do
    [ -d "$plugdir" ] || continue
    local keep
    # keep the newest VERSION DIR only — never let a stray file win the sort and
    # cause every real version dir to be deleted (this loop does rm -rf).
    keep=$(for d in "$plugdir"*/; do [ -d "$d" ] && basename "$d"; done | sort -V | tail -1)
    [ -n "$keep" ] || continue
    for v in "$plugdir"*/; do
      [ -d "$v" ] || continue
      [ "$(basename "$v")" = "$keep" ] && continue
      rm -rf "$v"
    done
    find "$plugdir$keep" -maxdepth 3 -type d \
      \( -name '.venv*' -o -name 'target' -o -name 'dist*' -o -name '__pycache__' \
         -o -name 'node_modules' -o -name '.pytest_cache' -o -name '.uv-cache' -o -name '.ruff_cache' \) \
      -exec rm -rf {} + 2>/dev/null || true
  done

  # caches for plugins no longer registered anywhere
  # (NEVER list a marketplace whose plugin is enabled in settings.json —
  #  cluxion-forgetforge was wrongly here and its live cache got deleted)
  for stale in cluxion-hermes-call; do
    # never delete a cache whose name is still referenced by any live plugin config
    grep -qs "$stale" "$HOME/.claude/settings.json" \
      "$HOME/.claude/plugins/known_marketplaces.json" "$HOME/.codex/config.toml" && continue
    [ -d "$CACHE/$stale" ] && rm -rf "$CACHE/$stale"
  done

  # orphaned install-staging dirs older than 1h
  find "$CACHE" -maxdepth 1 -type d \( -name 'temp_local_*' -o -name 'temp_git_*' \) \
    -mmin +60 -exec rm -rf {} + 2>/dev/null || true

  after=$(du -sk "$CACHE" | awk '{print $1}')
  echo "cache-slim [$CACHE]: $((before/1024))M → $((after/1024))M (reclaimed $(( (before-after)/1024 ))M)"
}

slim_root "$HOME/.claude/plugins/cache"
slim_root "$HOME/.codex/plugins/cache"
