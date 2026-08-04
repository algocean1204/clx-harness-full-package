## JSON Commands

```bash
cluxion-supercoder read-window --json-stdin
cluxion-supercoder patch --json-stdin
cluxion-supercoder cursor-map --json-stdin
cluxion-supercoder repo-map --json-stdin
cluxion-supercoder syntax-gate --json-stdin
cluxion-supercoder lint-gate --json-stdin
cluxion-supercoder test-gate --json-stdin   # suggest-only: returns the test command to run, not per-file pass/fail (the HOST runs the tests)
cluxion-supercoder brief --json-stdin
```

Hashes in outputs are bare 64-char sha256 hex; hash inputs also accept an optional `sha256:` prefix.

Examples:

```bash
printf '{"cwd":"<workspace>","path":"src/app.py","start_line":1,"max_lines":40}' |
  cluxion-supercoder read-window --json-stdin
```

```json
{"ok":true,"path":"src/app.py","start_line":1,"end_line":12,"content":"...","content_hash":"<64-hex>","file_hash":"<64-hex>"}
```

`max_lines` is capped at 120 (`line_budget_exceeded:inspect` above that); read larger files in successive windows.

```bash
printf '{"cwd":"<workspace>","path":"src/app.py","old_text":"old\\n","new_text":"new\\n","expected_hash":"<64-hex>"}' |
  cluxion-supercoder patch --json-stdin
```

```json
{"ok":true,"file_path":"/workspace/src/app.py","strategy":"exact","message":"patch applied","expected_hash":"<64-hex>","matched_hash":"<64-hex>","similarity":1.0,"syntax":{"checked":true,"error_count":0,"language":"python","valid":true},"lint":{"clean":true,"finding_count":0,"tool":"ruff","truncated":false}}
```

`lint` appears only when a linter for the file's language is available.

```bash
printf '{"cwd":"<workspace>","files_changed":["src/app.py"]}' |
  cluxion-supercoder syntax-gate --json-stdin
```

```json
{"ok":true,"files":[{"path":"src/app.py","checked":true,"language":"python","valid":true,"error_count":0,"errors":[]}]}
```

```bash
printf '{"cwd":"<workspace>","files_changed":["src/app.py"]}' |
  cluxion-supercoder lint-gate --json-stdin
```

```json
{"ok":true,"files":[{"path":"src/app.py","checked":true,"language":"python","tool":"ruff","clean":true,"finding_count":0,"findings":[],"truncated":false}]}
```

```bash
printf '{"cwd":"<workspace>","files_changed":["src/app.py"]}' |
  cluxion-supercoder test-gate --json-stdin
```

```json
{"ok":true,"mode":"suggest_or_run","command":"pytest -q tests/test_app.py","targets":["tests/test_app.py"],"files_changed":["src/app.py"],"source":"mapped_from_files_changed"}
```

```bash
printf '{"files_changed":["src/app.py"],"tests_run":[{"command":"pytest -q tests/test_app.py","status":"passed"}],"verification_status":"passed","remaining_risks":[]}' |
  cluxion-supercoder brief --json-stdin
```

```json
{"ok":true,"brief":{"files_changed":["src/app.py"],"tests_run":[{"command":"pytest -q tests/test_app.py","status":"passed"}],"verification_status":"passed","remaining_risks":[]}}
```

## Failure paths

A failed `patch` returns `ok:false` with a `strategy` and a `retry` object
(`attempt`, `max_attempts`, `repeated_input`, `escalate`, `guidance`):

- `no_match` — `old_text` not found, or several fuzzy candidates scored too close to pick one (ambiguity refusal). Re-read the window and copy `old_text` exactly; widen it with surrounding lines to disambiguate.
- `stale_file` — the file changed after `read-window`; rebuild the cursor and use the fresh `file_hash`.
- `syntax_rejected` — the candidate failed parsing and was rejected before any file write; fix `new_text` using the returned `syntax_errors`.
- `syntax_reverted` — an unexpected post-write check failed and the file was restored to its pre-patch content.
- `missing_file` / `empty_old_text` — verify the path (`cursor-map`) / send non-empty `old_text`.

Follow `retry.guidance`; never resend a failed patch unchanged. Retry state is persisted per workspace+file (15-minute TTL, cleared on success), so the attempt budget accumulates across one-shot CLI calls. When `escalate` is true the retry budget (3) is exhausted — stop patching and re-plan a smaller edit.
