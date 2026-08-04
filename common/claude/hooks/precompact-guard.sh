#!/bin/bash
# PreCompact: inject importance-based double-pass instructions into compaction.
# Hallucination risk concentrates in post-compaction recall — spend slightly more
# effort at compression time to preserve what matters verbatim.
# Includes only THIS session's lean session-intent core (full UUID SID) in MUST-KEEP.
HOOKDIR=$(cd "$(dirname "$0")" && pwd)
_J=$(cat)
_CORE=$(printf '%s' "$_J" | python3 "$HOOKDIR/session_intent_paths.py" --from-stdin core 2>/dev/null)
_SID=$(printf '%s' "$_J" | python3 "$HOOKDIR/session_intent_paths.py" --from-stdin sid 2>/dev/null)

cat <<'EOF'
COMPACTION GUARD (double-pass, fidelity over speed):
PASS 1 — extract MUST-KEEP verbatim before summarizing: (a) the active task spec incl.
locked quantities and enumerated items with completion state N/N, (b) user decisions and
approvals with their reasons, (c) exact file paths + key line refs touched this session,
(d) claims not yet verified (mark UNVERIFIED), (e) open blockers, (f) architecture/config
invariants established this session.
EOF

if [ -n "$_CORE" ] && [ -s "$_CORE" ]; then
  printf '%s\n' "(g) this session's session-intent lean core only (SID ${_SID}; path ${_CORE}; never another SID) — keep verbatim:"
  cat "$_CORE"
  printf '\n'
fi

cat <<'EOF'
PASS 2 — re-scan the original once more: anything referenced later in the conversation but
missing from your summary gets added back. Prefer dropping process narration and raw tool
logs over specs, decisions, and numbers. Never compress away failures or corrections.
After compaction, treat recalled line numbers and old claims as stale — re-verify via
rg/Read before acting on them.
EOF
exit 0
