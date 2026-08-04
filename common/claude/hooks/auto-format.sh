#!/bin/bash
# PostToolUse Edit|Write|Bash: format the edited file iff its project has a formatter config, and
# mark the turn as having done real work. Fail-silent.
# Bash is in the matcher because a turn that changes the world through `python3 - <<PY`, sed, cp or
# git set NO marker before — so the Stop self-check never fired on exactly the turns that most
# needed it. Bash calls carry no file_path, so they mark and return without formatting anything.
# pid comes back already keyed by standing_blocks.safe_key so this marker and the Python
# side (intent-lock arm, selfcheck-stop read) always agree, even on an odd prompt_id.
# Field order matters: TAB is IFS whitespace, so `read` collapses a RUN of tabs into one delimiter
# and any empty field shifts everything after it. file_path is the only one that can be empty
# (a Bash call has none), so it goes LAST where a trailing empty costs nothing.
IFS=$'\t' read -r pid mutating tmpdir big f < <(python3 -c "
import sys, json, os, re, fnmatch
sys.path.insert(0, os.path.expanduser('~/.claude/hooks'))
from standing_blocks import safe_key
import clx_host
d = json.load(sys.stdin)
ti = d.get('tool_input') or {}
tool = d.get('tool_name') or ''
# 'the turn did real work' must not mean 'the turn ran a command' — a read-only rg on a turn that
# then correctly stops at the two-stage approval gate would be pushed past the user's approval.
if tool == 'Bash':
    cmd = ti.get('command') or ''
    mut = bool(re.search(r'(^|[|;&\`(]\s*)(rm|mv|cp|mkdir|rmdir|ln|touch|chmod|chown|install|tee|dd|'
                         r'truncate|patch|make|rsync|unzip|tar)\b'
                         # A redirect writes only when it lands somewhere real. Discarding stderr
                         # into /dev/null, or merging descriptors, is ordinary punctuation on a
                         # read-only command; counting it made a plain three-repo git-status loop
                         # register as a mutation, and the Stop gate then demanded verification of
                         # a command that changed nothing. The angle bracket excludes itself so
                         # backtracking cannot re-match the first half of a doubled redirect as a
                         # lone one after the pair was excluded. (No backticks in this block: it is
                         # a double-quoted shell string and they would run as command substitution.)
                         r'|>>?\s*(?!/dev/(?:null|stdout|stderr|tty|fd/)|&|>)[^|\s]'
                         r'|sed\s+-i|perl\s+-i|python3?\s+-\s*<<|<<\s*.?PY'
                         # options may sit between git and its subcommand: git -C DIR commit left
                         # no marker at all, which is the dangerous direction to be wrong in
                         r'|git\s+(?:-\S+\s+(?:[^-\s]\S*\s+)?)*'
                         r'(add|commit|push|merge|rebase|reset|checkout|apply|mv|rm|tag|init)\b'
                         r'|(npm|pnpm|yarn|pip3?|uv|brew|cargo|go)\s+(i|install|add|remove|uninstall|publish)\b',
                         cmd))
    # Running an arbitrary script is the blind spot: a plain 'python3 build.py' can rewrite the
    # tree and matches none of the patterns above, so the turn left NO marker and skipped every
    # check. NOTE: this block is a double-quoted shell string — backticks here would become
    # command substitution and the shell would RUN them on every tool call. No backticks, no '$'.
    # Its effect is unknowable statically, so it counts as WORK ('?') but never as a proven
    # mutation — proven ones anchor the evidence gate, and marking a test run would demand
    # verification after every test.
    if not mut and re.search(r'^\s*(?:\S*/)?(?:python\d?(?:\.\d+)?|node|deno|bun|ruby|perl|'
                             r'bash|sh|zsh)\s+[^-\s]\S*', cmd):
        mut = '?'
else:
    mut = True                      # Edit / Write / NotebookEdit always change a file
fp = ti.get('file_path', '') or ''
# Evidence ledger: what actually RAN this turn, so the Stop check measures instead of asking.
# Only metadata — tool, error flag, output length, command/path prefix — never raw output, the
# same discipline browser-audit uses. Appended here (not via a new shell field) so the tab-field
# order above stays untouched. Best-effort: a ledger write must never break formatting.
key = safe_key(d.get('prompt_id'))
try:
    res = d.get('tool_response', d.get('tool_result'))
    body = res.get('content') if isinstance(res, dict) else res
    err = bool(isinstance(res, dict) and res.get('is_error'))
    text = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False) if body else ''
    subject = (ti.get('command') or fp or '').replace('\t', ' ').replace('\n', ' ')[:160]
    if key:
        with open(os.path.join(clx_host.TMP, 'clx-evidence-' + key), 'a', encoding='utf-8') as fh:
            fh.write('\t'.join((tool, 'err' if err else 'ok', str(len(text)),
                                '1' if mut is True else ('?' if mut == '?' else '0'), subject)) + '\n')
except Exception:
    pass
# Harness names must not reach a user's file. ponytail asks for a '# ponytail:' marker on every
# deliberate simplification; that convention is for THIS harness, and it shipped into a customer
# repo where the label means nothing. Rule (rules/engineering.md) prevents; this catches. Only
# files OUTSIDE the three agent trees are checked, and only the text just written.
try:
    _warn = []
    # A CHECKOUT of this harness is not someone else's project: 219 of its 2890 files carry
    # 'clx-' because that is what the repository is, and the detector fired on every write to one.
    # Same two-marker test the Stop hook uses — a lone AGENTS.md could be coincidence, that plus a
    # sibling hooks directory is this config. Dotted for the live trees, plain for a checkout.
    # The walk was capped at 6 ancestors, and this repository's own vendored plugins sit 7-9 deep
    # (plugins-vendored/<plugin>/skills/<name>/scripts/...), so writes to the harness's OWN files
    # were classified as someone else's project and drew a false leak warning. Walk every ancestor;
    # it is a handful of stats and the whole cost measured under 0.1 ms.
    # The DOTTED pair used to be in this list, and $HOME satisfies it — so once the walk climbed
    # past 6 ancestors, every file under the user's home was 'the harness's own checkout' and all
    # five checks below went silent on 100% of real writes. The live trees never needed a marker
    # test: _outside already excludes /.claude/, /.codex/ and /.agents/ by path. $HOME and / are
    # never roots.
    _harness_root = False
    _home = os.path.expanduser('~').rstrip('/')
    _p = os.path.dirname(fp or '')
    while _p and _p not in ('/', _home):
        for _m, _s in (('common/agents/AGENTS.md', 'common/claude/hooks'),
                       ('agents/AGENTS.md', 'claude/hooks')):
            if os.path.isfile(os.path.join(_p, _m)) and os.path.isdir(os.path.join(_p, _s)):
                _harness_root = True
                break
        _parent = os.path.dirname(_p)
        if _harness_root or _parent == _p:
            break
        _p = _parent
    _outside = (fp and not _harness_root
                and not any(('/.' + _d + '/') in fp for _d in ('claude', 'codex', 'agents')))
    _new = (ti.get('content') or ti.get('new_string') or '') if _outside else ''
    if _new:
        for _m in ('ponytail:', 'clx-', 'clx_'):
            if _m in _new:
                _warn.append('harness name ' + repr(_m) + ' written into ' + fp
                             + ' — rules/engineering.md forbids it in a project file. '
                               'Keep the insight, drop the label.')
                break
    # Three write-time checks for the self-exemption class (core rule 3). Warnings only — a false
    # positive must never cost a keystroke. Signatures are EXACT sinks or exact value mismatches,
    # never 'suspicious-looking code': measured on 20,388 real source files here, the credential
    # pattern fires 6 times (all test fixtures) and the TLS pattern 0, while a loose 'this literal
    # also appears in a config file' rule fired 31,526 times. That number is why the config check
    # below demands a DECLARED source, a key match AND a differing value.
    _code = _new and os.path.splitext(fp)[1] in (
        '.py', '.ts', '.tsx', '.js', '.jsx', '.rs', '.swift', '.java', '.go', '.kt', '.rb')
    _test = re.search(r'(^|/)(tests?|__tests__|spec|fixtures?|examples?|migrations?)(/|$)'
                      r'|(^|/)(test_|conftest|[^/]*_test|[^/]*\.test|[^/]*\.spec)', fp or '')
    # Code you did not write is not code you can fix. Without this, one glob signal reached into
    # every dependency on the machine — the exact wallpaper the per-row opt-in exists to prevent.
    _vendor = re.search(r'(^|/)(\.venv|venv|site-packages|node_modules|vendor|third_party|'
                        r'dist|build|\.git|target|Pods|\.tox|\.mypy_cache)(/|$)', fp or '')
    if _code and not _test and not _vendor:
        _cred = re.search(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'
                          r'|\b(?:sk-[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}'
                          r'|gh[po]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}'
                          r'|xai-[A-Za-z0-9]{20,})\b', _new)
        if _cred:
            _warn.append('a credential literal (' + _cred.group(0)[:12]
                         + '…) was written into ' + fp + ' — move it to the environment or a '
                           'secret store; a key in source outlives the commit that removes it.')
        _tls = re.search(r'verify\s*=\s*False\b|CERT_NONE\b|_create_unverified_context\b'
                         r'|rejectUnauthorized\s*:\s*false\b'
                         r'|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*[\'\"]?0'
                         r'|danger_accept_invalid_(?:certs|hostnames)\s*\(\s*true', _new)
        if _tls:
            _warn.append('TLS verification is disabled by ' + repr(_tls.group(0))
                         + ' in ' + fp + ' — \'this endpoint is internal\' is the exemption this '
                           'check exists for. Pin a CA or fix the certificate instead.')
        # Config shadow: only in a repo that DECLARES a single source of truth in its own docs.
        # Opt-in by declaration is what keeps this silent everywhere else, structurally rather
        # than by tuning a regex.
        _root, _prev = os.path.dirname(fp), ''
        while _root and _root != _prev and not os.path.isdir(os.path.join(_root, '.git')):
            _root, _prev = os.path.dirname(_root), _root
        _ssot = ''
        if _root and os.path.isdir(os.path.join(_root, '.git')):
            for _doc in ('AGENTS.md', 'CLAUDE.md', 'README.md'):
                _dp = os.path.join(_root, _doc)
                if not os.path.isfile(_dp):
                    continue
                with open(_dp, encoding='utf-8', errors='replace') as _fh:
                    for _line in _fh.read(200000).splitlines():
                        if re.search(r'single source of truth|유일한 출처|단일 소스', _line, re.I):
                            _hit = re.search(r'\`?([\w.-]+\.(?:json|toml|ya?ml|ini))\`?', _line)
                            if _hit:
                                _ssot = _hit.group(1)
                                break
                if _ssot:
                    break
        if _ssot:
            _sp = ''
            for _dirpath, _dirs, _names in os.walk(_root):
                _dirs[:] = [_d for _d in _dirs if _d not in
                            ('.git', 'node_modules', '.venv', 'target', 'dist', 'build')]
                if _ssot in _names:
                    _sp = os.path.join(_dirpath, _ssot)
                    break
            if _sp and os.path.abspath(_sp) != os.path.abspath(fp):
                with open(_sp, encoding='utf-8', errors='replace') as _fh:
                    _cfg = _fh.read(200000)
                _declared = {}
                for _m2 in re.finditer(r'[\"\']?([\w.-]{2,40})[\"\']?\s*[:=]\s*[\"\']([^\"\'\n]{1,80})[\"\']',
                                       _cfg):
                    _declared[re.sub(r'[^a-z0-9]', '', _m2.group(1).lower())] = _m2.group(2)
                for _m3 in re.finditer(r'^\s*(?:pub\s+)?(?:const|let|var|final|static)?\s*'
                                       r'([A-Za-z_][\w]{2,40})\s*(?::[^=\n]+)?=\s*[\"\']([^\"\'\n]{1,80})[\"\']',
                                       _new, re.M):
                    _norm = re.sub(r'[^a-z0-9]', '', _m3.group(1).lower())
                    _norm = re.sub(r'^(default|fallback)', '', _norm) or _norm
                    if _norm in _declared and _declared[_norm] != _m3.group(2):
                        _warn.append(_m3.group(1) + ' = ' + repr(_m3.group(2)) + ' in ' + fp
                                     + ' disagrees with ' + _ssot + ' (' + repr(_declared[_norm])
                                     + '), which this repo declares as its single source. '
                                       'A default is not an exception — let the loader own it.')
                        break
    # Recall at the keystroke. Presence in context is demonstrably not salience — every defect
    # this session was written with the relevant rule already loaded — so a row that carries a
    # path SIGNAL is surfaced at the moment such a file is written. Rows without a signal are
    # never matched, which is what keeps this from becoming wallpaper: recall opts in per row.
    if _code and not _test and not _vendor:
        _led = os.path.expanduser('~/.claude/guides/work/intent-patterns.md')
        try:
            with open(_led, encoding='utf-8') as _fh:
                for _row in _fh:
                    if not _row.startswith('| 20'):
                        continue
                    # markdown escapes a literal pipe as backslash-pipe; splitting on every pipe
                    # shifted every cell right of it, so a row with NO signal picked up the rule
                    # text as its glob and matched against fragments of prose. chr(92) rather than
                    # a literal backslash: this block is a double-quoted shell string.
                    _row2 = _row.replace(chr(92) + '|', chr(1))
                    _c = [x.strip().replace(chr(1), '|')
                          for x in _row2.strip().strip('|').split('|')]
                    if len(_c) < 6 or not _c[4]:
                        continue
                    _bt = chr(96)   # never write this character literally in this block
                    # fnmatch anchors the WHOLE string and fp is absolute, so a repo-relative
                    # signal ('src/**/*.py') silently matched nothing — the failure mode with no
                    # symptom. Try the anchored form too.
                    if any(fnmatch.fnmatch(fp, _g) or fnmatch.fnmatch(fp, '*/' + _g.lstrip('/'))
                           for _g in (_h.strip(' ' + _bt) for _h in _c[4].split(',')) if _g):
                        _warn.append('past failure on this kind of file (' + _c[1] + '): '
                                     + _c[3][:220])
                        break
        except OSError:
            pass
    # This whole python block runs under 2>/dev/null, so a warning written here would vanish.
    # Hand it to the shell through a file; the shell's stderr is the channel that survives.
    if _warn and key:
        with open(os.path.join(clx_host.TMP, 'clx-leak-' + key), 'w', encoding='utf-8') as fh:
            for _w in _warn:
                fh.write('auto-format: ' + _w + '\n')
except Exception:
    pass
# the size test rides along here: 'stat -f%z' is BSD and 'stat -c%s' is GNU, and the wrong one
# returns 0, which silently disabled the >1MB skip on every Linux machine
print(key, '1' if mut is True else ('?' if mut == '?' else '0'), clx_host.TMP,
      '1' if clx_host.file_size(fp) > 1048576 else '0', fp, sep='\t')" 2>/dev/null)
# self-check gate: mark that this prompt's turn actually changed something (read by selfcheck-stop.py)
# The marker directory comes from clx_host so the shell and Python sides can never disagree.
[ -n "$pid" ] && [ -n "$tmpdir" ] && { [ "$mutating" = 1 ] || [ "$mutating" = "?" ]; } && touch "$tmpdir/clx-mutated-$pid" 2>/dev/null
# surface a harness-name leak the python block detected (its own stderr is discarded)
if [ -n "$pid" ] && [ -n "$tmpdir" ] && [ -s "$tmpdir/clx-leak-$pid" ]; then
  cat "$tmpdir/clx-leak-$pid" >&2
  rm -f "$tmpdir/clx-leak-$pid"
fi
# absolute paths only: dirname "." is "." forever, and the root walk below would spin on a relative one
case "$f" in /*) ;; *) exit 0 ;; esac
[ -f "$f" ] || exit 0
[ "$big" = 1 ] && exit 0   # generated bundles would waste the 30s hook timeout

root=$(dirname "$f")
while [ "$root" != "/" ] && [ ! -e "$root/package.json" ] && [ ! -e "$root/pyproject.toml" ] && [ ! -e "$root/ruff.toml" ] && [ ! -e "$root/Cargo.toml" ] && [ ! -d "$root/.git" ]; do
  root=$(dirname "$root")
done

case "$f" in
  *.py)
    # --force-exclude: ruff obeys the project's `exclude` only for EXPLICIT paths when asked, and a
    # hook always passes an explicit path — without it, vendored/generated files get rewritten.
    if command -v ruff >/dev/null 2>&1 && { [ -f "$root/ruff.toml" ] || grep -qs '\[tool\.ruff' "$root/pyproject.toml"; }; then
      ruff format --force-exclude "$f" >/dev/null 2>&1
      ruff check --fix --force-exclude --quiet "$f" >/dev/null 2>&1
    fi ;;
  *.rs)
    if command -v rustfmt >/dev/null 2>&1 && [ -f "$root/Cargo.toml" ]; then
      rustfmt "$f" >/dev/null 2>&1
    fi ;;
  *.js|*.jsx|*.ts|*.tsx|*.css|*.scss|*.json|*.html|*.vue|*.svelte|*.md)
    # Require a real prettier CONFIG (rc/config file, or a TOP-LEVEL "prettier" key in
    # package.json) — a bare `"prettier"` substring also matches a devDependencies entry, which
    # is not config and would reformat repos that never opted into prettier.
    if ls "$root"/.prettierrc* "$root"/prettier.config.* >/dev/null 2>&1 \
       || python3 -c "import json,sys;sys.exit(0 if 'prettier' in json.load(open(sys.argv[1])) else 1)" "$root/package.json" 2>/dev/null; then
      (cd "$root" && npx --no-install prettier --write --ignore-unknown "$f") >/dev/null 2>&1
    fi ;;
esac
exit 0
