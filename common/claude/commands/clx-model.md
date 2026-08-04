---
description: View or change the model registry (~/.agents/models.toml) with validation and auto-propagation
argument-hint: [role=model-id ... | 비우면 현황 표시]
---

Invoke skill `clx-model` on:

$ARGUMENTS

No args → show the registry table. With changes → run the full pipeline (validate → update → propagate → re-verify → backup) and report outcome-first: role, old → new, validation evidence.
