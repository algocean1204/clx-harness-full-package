#!/bin/sh
# Cheap AoE prefilter: start Python only for likely browser-related tool payloads.
set -eu

phase=${1:-}
case "$phase" in
  pre|post) ;;
  *) echo "browser-audit-hook: expected pre or post" >&2; exit 2 ;;
esac

payload=$(cat)
case "$payload" in
  *browser*|*Browser*|*chrome*|*Chrome*|*playwright*|*Playwright*|*computer-use*|*computer_use*) ;;
  *) exit 0 ;;
esac

audit=${BROWSER_AUDIT_PYTHON:-"$HOME/.claude/hooks/browser-audit.py"}
printf '%s' "$payload" | "$audit" "hook-$phase"
