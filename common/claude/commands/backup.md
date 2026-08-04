---
description: Back up a folder to its private GitHub repo (.backup-repo marker; first run asks & configures)
argument-hint: <folder path (default: current project root)>
---

Invoke skill `clx-repo-backup` and run its full pipeline on:

$ARGUMENTS

If no folder is given, use the current project root. First run without a marker/repo: ask, configure, then back up — one pipeline, never half-done. Report outcome-first in one line.
