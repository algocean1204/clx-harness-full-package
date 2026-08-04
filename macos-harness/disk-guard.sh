#!/bin/bash
# SessionStart: jetsam guard — warn only when free disk < 30G, silent (zero context cost) otherwise.
free_kb=$(df -k / | awk 'NR==2 {print $4}')
case "$free_kb" in ''|*[!0-9]*) exit 0 ;; esac  # df hiccup — stay silent, no fake warning
if [ "$free_kb" -lt 31457280 ]; then
  echo "DISK GUARD: only $((free_kb / 1048576))G free (<30G). Heavy data work risks jetsam kills — free space first (check APFS snapshots: tmutil listlocalsnapshots /)."
fi
exit 0
