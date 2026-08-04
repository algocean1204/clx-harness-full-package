#!/usr/bin/env bash
# update-vendored.sh — refresh vendored upstreams (public plugins + harness library).
# Run occasionally, review `git status` / `git diff`, then commit yourself. NEVER pushes.
set -euo pipefail
cd "$(dirname "$0")"
command -v rsync >/dev/null || { echo "rsync required"; exit 1; }
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
V=common/claude/plugins-vendored

sync() { rsync -a --delete --exclude .git "$1"/ "$2"/; }
sedi() { sed -i.bak "$@" && rm -f "${@: -1}.bak"; }   # portable in-place sed

echo "[1/4] ponytail (DietrichGebert/ponytail)"
git clone -q --depth 1 https://github.com/DietrichGebert/ponytail "$TMP/ponytail"
sync "$TMP/ponytail" "$V/ponytail"

echo "[2/4] claude-plugins-official: skill-creator plugin-dev typescript-lsp pyright-lsp jdtls-lsp"
git clone -q --depth 1 https://github.com/anthropics/claude-plugins-official "$TMP/official"
for p in skill-creator plugin-dev typescript-lsp pyright-lsp jdtls-lsp; do
  sync "$TMP/official/plugins/$p" "$V/$p"
done

echo "[3/4] anthropics/skills (document-skills)"
git clone -q --depth 1 https://github.com/anthropics/skills "$TMP/skills"
for d in skills spec template; do [ -d "$TMP/skills/$d" ] && sync "$TMP/skills/$d" "$V/document-skills/$d"; done
for f in README.md THIRD_PARTY_NOTICES.md; do [ -f "$TMP/skills/$f" ] && cp "$TMP/skills/$f" "$V/document-skills/$f"; done

echo "[4/4] harness-library (revfactory/harness-100 ko)"
git clone -q --depth 1 https://github.com/revfactory/harness-100 "$TMP/h100"
sync "$TMP/h100/ko" common/agents/harness-library/ko
cp "$TMP/h100/LICENSE" common/agents/harness-library/LICENSE
NEW=$(git -C "$TMP/h100" rev-parse HEAD)
sedi -E "s/pinned at upstream commit \`[0-9a-f]+\`/pinned at upstream commit \`$NEW\`/" common/agents/harness-library/README.md

echo
echo "== changed files =="
git status --short | head -40
echo
echo "Next: review with 'git diff', run the sanitize self-check from README.md, then commit manually."
echo "Note: LSP/document-skills metadata lives in $V/.claude-plugin/marketplace.json — if upstream changed its marketplace entry, port it there by hand."
