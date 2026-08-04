#!/bin/sh
# SessionEnd: archive THIS logical session's single bounded intent core into
# forgetforge so the session's intent/workflow survives teardown. Archive-only:
# clearing Active task / DoD sections is the session-intent skill's job, not this hook's.
#
# Key = validated full-UUID session_id only (session_intent_paths.py). Never key as
# "unknown", never read another SID, never promote/move into a shared seed, never
# delete the on-disk core. UUID directories stay as small recovery state because
# resume may reuse the same SID; no automatic age deletion/GC without a proven
# archive-success ownership signal (deliberate Cycle 98 choice).
HOOKDIR=$(cd "$(dirname "$0")" && pwd)
_J=$(cat)  # SessionEnd JSON — stdin is single-use; read once
# Resolve SID + paths only via the helper (full UUID; empty when invalid/missing)
SID=$(printf '%s' "$_J" | python3 "$HOOKDIR/session_intent_paths.py" --from-stdin sid 2>/dev/null)
[ -n "$SID" ] || exit 0
CORE=$(printf '%s' "$_J" | python3 "$HOOKDIR/session_intent_paths.py" --from-stdin core 2>/dev/null)
[ -n "$CORE" ] && [ -s "$CORE" ] || exit 0
command -v forgetforge >/dev/null 2>&1 || exit 0
# node_type=session keeps archives out of recall/hot-injection (they'd crowd real
# memories at year volume); still reachable via graph paths. 90d TTL, prune sweeps.
# FAIL-CLOSED: no bare-store fallback — storing without --node-type/--expire-days leaks a
# permanent, recall-eligible row (exactly what node_type=session avoids). If the flagged
# store fails (e.g. an old CLI without these flags), skip archiving rather than pollute recall.
# Keep on-disk files after archive (ordinary resume / same-SID recovery).
forgetforge store "session-intent-$SID" --content-file "$CORE" --importance 0.6 \
  --node-type session --session-id "$SID" --expire-days 90 >/dev/null 2>&1 || true
# Keep the intent-patterns ledger's mistake nodes fresh (idempotent; fail-open).
python3 "$HOOKDIR/forgetforge-sync.py" >/dev/null 2>&1 || true
# This session's standing-block sentinel has no further use. The name carries a digest
# suffix (standing_blocks.sentinel), so match by prefix.
rm -f "${TMPDIR:-/tmp}/clx-standing-$SID"-* "/tmp/clx-standing-$SID"-* 2>/dev/null || true
# Sweep markers older than a day: a turn that armed the self-check but never mutated a file
# leaves its flag behind, and those would otherwise accumulate one per prompt.
find /tmp "${TMPDIR:-/tmp}" -maxdepth 1 -type f \
  \( -name 'clx-selfcheck-*' -o -name 'clx-mutated-*' -o -name 'clx-standing-*' \
     -o -name 'clx-handoff-*' -o -name 'clx-evidence-*' \) \
  -mmin +1440 -delete 2>/dev/null || true
exit 0
