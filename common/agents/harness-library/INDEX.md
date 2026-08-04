# harness-library INDEX (thin overlay)

Full 100-harness catalog with one-liners: **[ko/README.md](ko/README.md)** (upstream table, reuse — do not duplicate here).
Case gallery: [ko/harness-100-cases.md](ko/harness-100-cases.md).

## Existing-asset-priority badges

These harnesses overlap assets already in this environment. The library keeps them (nothing deleted), but prefer the native asset unless the user names the harness explicitly:

| Harness | Overlapping native asset | Overlap |
|---|---|---|
| 21-code-reviewer | `/code-review` + standing UX panel agents | strong |
| 28-security-audit | `/security-review` | strong |
| 36-design-system | design stack (apple-design · frontend-design · impeccable · astryx · theme-factory) | strong |
| 13-presentation-designer | `pptx` skill | partial |
| 24-test-automation | `test-driven-development` + `verification-before-completion` | partial |
| 32-data-analysis | `clx-dataset-work` | partial |
| 14-translation-localization | native multilingual output rules | partial |

## Install contract (`/harness use <id>`)

1. Source: `~/.agents/harness-library/ko/<id>/.claude/` → target: CURRENT project `.claude/`.
2. Non-destructive: existing target files are NEVER overwritten — conflicts are reported and skipped.
3. Transforms applied to the INSTALLED copy only (library stays pristine upstream):
   - every `skills/*/skill.md` → `SKILL.md` (case-sensitive FS / Windows safety)
   - installed `CLAUDE.md` gets a one-line core-binding header: subagents ≤10 concurrent / ≤2 tiers, no external CLIs from subagents, no AI attribution in commits — global core rules win on conflict.
4. Report: installed file count, skipped conflicts, overlap badge warning if applicable.
