---
name: clx-supercoder
description: Hash-verified patch discipline for coding tasks — bounded reads, ambiguity-refusing patches, syntax rollback, lint/test gates, and an evidence brief. Explicit user invocation ONLY — /supercoder or a named clx-supercoder request; never auto-loaded by the model. Skip non-code work.
disable-model-invocation: true
---

# Cluxion Supercoder

Call the package CLI. It returns JSON contracts; the host agent owns file reads, edits, terminal commands, and final answers.

## Plan

```bash
cluxion-supercoder check
cluxion-supercoder plan --json-stdin
```

Minimum stdin:

```json
{"prompt":"<user request>","cwd":"<workspace>"}
```

If the result is `mode=bypass`, continue without Supercoder. If the result is `mode=coding_queue`, follow this workflow:

1. Use the plan and embedded `repo_map` for orientation; call `repo-map` when more map context is needed.
2. Call `read-window` before each edit and use the returned `file_hash`.
3. Call `patch` with exact `old_text`, `new_text`, and `expected_hash` (alias: `expected_file_hash`). Each successful patch is syntax-gated automatically — a patch that breaks parsing is rolled back — and lint findings ride along in `lint`.
4. After all patches land, call `syntax-gate`, `lint-gate`, and `test-gate` on the full `files_changed` list; the host must run any suggested tests in the terminal.
5. Call `brief` with `files_changed`, `tests_run`, `verification_status`, and remaining risks.

## JSON Commands

Full command/JSON contract examples: `references/commands.md` (read on demand).

## Doctor

```bash
cluxion-supercoder check
cluxion-supercoder doctor
cluxion-supercoder doctor --json
```
