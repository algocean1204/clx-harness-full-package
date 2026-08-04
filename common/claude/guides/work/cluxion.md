# Cluxion Suite — Routing Guide

Load when: `/supercoder` or `/preprocess` invoked; user says 슈퍼코더 / 전처리 / cluxion; or preprocessing genuinely needed (fuzzy/multi-item intake). Supercoder is explicit slash-only (`disable-model-invocation`, 2026-07-25); clx-preprocess may self-load.

The cluxion custom plugins ship in the `plugins-vendored/` local marketplace (see README "플러그인은 전부 실물 동봉"). On-demand only — never always-on. `[SUPERCODER MODE]` banners and consensus theater stay banned; evidence over narration.

## Capability / tradeoff matrix

| Skill | Function | Strengths | Weaknesses / cost | Route when | Skip when |
|---|---|---|---|---|---|
| `clx-preprocessing:clx-preprocess` | Clarification contracts, queueing, loop_auto drain, doctor diagnostics, surface-specific JSON contracts | Turns fuzzy or multi-item intake into a machine-checkable contract; stabilizes downstream work | Contract ceremony adds latency; zero value on already-clear tasks | Ambiguous scope, queued work bundles, broken-loop diagnosis | Task already precise; single obvious edit. Human-style interviewing → `clx-grill-me` instead |
| `clx-supercoder:clx-supercoder` | Planning with bounded reads, hash-verified patches, syntax/lint/test gates, evidence brief | Patch integrity on large or risky multi-file edits; strong anti-hallucination discipline | Slowest path for small diffs; gates are overkill for one-liners | Explicit `/supercoder` only (worth invoking on multi-file, unfamiliar-codebase, correctness-critical work) | Trivial single-line edits (direct + ponytail ladder); non-code work; UI work (design chain owns it) |
| `clx-ultracode` | — | — | — | **Codex-only** (not installed on Claude; marketplace entry only). Adversarial consensus on Claude → `ensemble-consensus` | Always, on Claude |

## Interplay

- Ponytail governs code size (minimal diff); supercoder governs patch discipline — they compose, not conflict.
- Fuzzy intake AND heavy edit → `clx-preprocess` first, then `clx-supercoder`.
- Goal/loop turns: skill output must still end in same-turn implementation + evidence (see `goals`).

## Edit pipeline (mandatory after changing any cluxion plugin)

1. Bump version in ALL manifests — `pyproject.toml`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `plugin.yaml` (root AND `src/*/plugin.yaml` if present). The preprocessing doctor's `version_files_synced` fails on any drift; rg needs `--hidden` to see the dot-dirs.
2. Build with the repository's release family: SC/PP/FF run `bash scripts/build_local_wheel.sh`; HC/UC run `rm -rf dist && uv build --wheel`. Do not substitute plain `uv build` for a merged native wheel.
3. Resolve and install exactly one source-version-matching absolute wheel (never a wildcard/source directory/stale wheel):
   ```bash
   case "$(basename "$PWD")" in
     clx-supercoder) PREFIX=cluxion_agentplugin_supercoder; OUT=dist-merged ;;
     clx-preprocessing) PREFIX=cluxion_agentplugin_preprocessing; OUT=dist-merged ;;
     clx-autoclearmemory) PREFIX=cluxion_agentplugin_autoclearmemory; OUT=dist-merged ;;
     clx-hermes-call) PREFIX=cluxion_hermes_call_cli; OUT=dist ;;
     clx-ultracode) PREFIX=cluxion_agentplugin_effort_ultracode; OUT=dist ;;
     *) echo "not a cluxion plugin repo" >&2; exit 1 ;;
   esac
   VERSION="$(awk -F'"' '/^version = "/ {print $2; exit}' pyproject.toml)"
   WHEEL="$(OUT="$OUT" PREFIX="$PREFIX" VERSION="$VERSION" python3 -c 'import os; from pathlib import Path; w=list(Path(os.environ["OUT"]).glob(os.environ["PREFIX"]+"-"+os.environ["VERSION"]+"-*.whl")); assert len(w)==1, w; print(w[0].resolve())')"
   uv pip install -e . --python .venv/bin/python
   uv tool install --force "$WHEEL"
   ```
   `uv sync` alone does not update the PATH CLI. Verify `<cli> --version` equals `$VERSION`.
   The glob only proves the FILENAME; when a stale install is still suspected, check the wheel's
   own metadata against pyproject: `python3 ~/.claude/hooks/verify-wheel-contract.py "$WHEEL"`.
4. Reinstall via the real marketplace link on BOTH platforms: `claude plugin uninstall/install <name>@<marketplace>` AND `codex plugin marketplace upgrade` + `codex plugin remove/add <name>@<marketplace>` — codex caches drift 4 releases behind otherwise.
5. Verify: plugin `doctor` (0 unexpected warns) + `pytest -k 'doctor or catalog'` minimum.
6. Immediately after marketplace reinstalls, run `hooks/cache-slim.sh` and verify the live plugin caches are slim; this is a mandatory deployment step. Backup maintenance runs it only as an hourly fallback, not on every backup invocation. Then run `hooks/push-skillbook.sh` to sync the skillbook monorepo — owner-only, it pushes to a private mirror and is not part of the distribution.

## Accepted duplication (do not re-flag)

`doctor/framework.py` is ~70-90% identical across all 5 cluxion plugins. This is DELIBERATE,
not a defect to consolidate: they are 5 independently-published PyPI packages, so each needs a
self-contained doctor framework — a shared `cluxion-doctor-core` dependency would couple their
release cycles for no functional gain. The known `DoctorResult.summary()` drift (present in 3/5)
is cosmetic: no code parses or branches on the doctor JSON `summary` key (verified). Do not
"fix" this by refactoring 5 plugins.

## Known cosmetic backend diffs (verified equivalent — do not re-flag as bugs)

Rust-native vs pure-Python fallback were verified equivalent on data/scoring/ordering
(forgetforge bit-identical; preprocessing queue 30/32 byte-equal). The only differences are
cosmetic and NOT correctness bugs:
- supercoder repo-map: pure-Python tier outlines Python only (tree-sitter tiers add rust/js/ts).
  This is documented fail-open capability degradation, not a defect.
- preprocessing queue error paths: rust prefixes `queue store error: `, python does not (same
  exception type/semantics). Cosmetic.

## Native backends (Rust-first status, 2026-07-06)

forgetforge_engine / cluxion_queue / supercoder_index natives are BUILT and live in the uv
tool venvs (doctor native probes pass); shipped wheels bundle them via the merged-wheel
machinery. Effort-Ultracode and Hermes-call-cli are pure python BY DESIGN — no hot path, no
rust dir; accepted Rust-first exceptions. Zero JS in user-authored skill/plugin tooling.
