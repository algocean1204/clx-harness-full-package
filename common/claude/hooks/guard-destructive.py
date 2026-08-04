#!/usr/bin/env python3
"""PreToolUse guard: structurally block catastrophic/destructive commands.

Token-based (shlex): quoted strings become single tokens, so command text inside
messages/echo never false-positives, while quoted targets ("/") are still caught.
Runs in every permission mode including bypass. Malformed hook input exits 0 silently;
after a valid Bash command is accepted, evaluation errors fail closed. Chrome and agent
state denials have no override; other destructive operations require a one-time owner grant or
direct execution in the owner's own terminal.
Nested shells (`bash -c "rm -rf /"`, `zsh -lc "..."`) ARE re-parsed: the script is a
literal token here, so a destructive command inside it is statically visible and is
fed back through the same pipeline. Command substitutions $(...) / `...` are also re-parsed
so a destructive command inside one (`echo $(rm -rf /)`) is caught. Accepted limit: targets
whose VALUE is produced at runtime — `… | xargs rm -rf`, stdin-built commands, or a benign
substitution that yields the path (`rm -rf "$(printf /)"`) — can't be statically resolved.
"""
import datetime
import fnmatch
import hashlib
import json
import os
import re
import shlex
import sys
import time

# One marker directory, shared by every hook. The guard must never fail to load, so an absent
# clx_host (a partial install, an odd loader) falls back rather than raising.
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                    if "__file__" in globals() else os.path.expanduser("~/.claude/hooks"))
    from clx_host import TMP as _TMP
except Exception:
    import tempfile
    _TMP = "/tmp" if os.name == "posix" else tempfile.gettempdir()

ROOT_TARGETS = {"/", "/*", "~", "~/", "~/*", "$HOME", "$HOME/", "$HOME/*"}
# Top-level system dirs whose WHOLE-dir recursive wipe/rewrite is catastrophic; the non-SIP macOS ones
# (/Applications /usr/local /Library /opt) are reachable WITHOUT sudo, yet the guard blanket-blocks all
# `sudo rm` — so the unprivileged form must match too. EXACT match only denies; a specific subpath
# (/Applications/X.app, /usr/local/bin/foo) stays ALLOW. Cross-platform: FHS roots + macOS roots.
_CRITICAL_SYSDIRS = frozenset({
    "/usr", "/usr/local", "/usr/bin", "/usr/sbin", "/usr/lib",
    "/bin", "/sbin", "/lib", "/lib64", "/boot",
    "/etc", "/var", "/opt", "/dev", "/private",
    "/System", "/Library", "/Applications",
})
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1")
_CHROME_STATE = re.compile(
    r"(?:\$HOME|\$\{HOME[^}]*\}|~|/Users/[^/]+)/Library/Application Support/Google/Chrome(?:/|$)",
    re.IGNORECASE,
)
_CHROME_STATE_LOOSE = re.compile(
    r"Library/Application Support/Google/Chrome(?:/|$)", re.IGNORECASE
)
_KEYCHAIN_STATE = re.compile(
    r"(?:\$HOME|\$\{HOME[^}]*\}|~|/Users/[^/]+)/Library/Keychains(?:/|$)",
    re.IGNORECASE,
)
_KEYCHAIN_STATE_LOOSE = re.compile(r"Library/Keychains(?:/|$)", re.IGNORECASE)
_CHROME_MUTATORS = {
    "rm", "srm", "mv", "cp", "rsync", "ln", "unlink", "truncate", "touch",
    "sqlite3", "chmod", "chown", "chgrp", "install", "dd", "tee",
}
_CHROME_SCRIPT_MUTATION = re.compile(
    r"\b(?:rmtree|rmdir|remove|unlink|rename|replace|move|mkdir|makedirs|copy|copy2|copyfile|copytree|"
    r"symlink_to|write_text|write_bytes|writeFile|appendFile|mkdirSync|rmdirSync|rmSync|unlinkSync|"
    r"renameSync|copyFileSync|cpSync|writeFileSync|appendFileSync|truncate|terminate|kill|"
    r"open\s*\([^)]*['\"]?[wax+]|File\.(?:delete|rename|write)|FileUtils\.(?:mkdir_p|rm_rf|mv|cp))\b",
    re.IGNORECASE,
)
# perl/ruby spell the mode as a redirection string — `open(F, ">>", $path)`. This cannot live in
# _CHROME_SCRIPT_MUTATION: that alternation is wrapped in \b(?:…)\b, and a trailing `>` followed
# by `"` has no word boundary, so the branch could never fire there.
_SCRIPT_OPEN_WRITE = re.compile(r"open\s*\(\s*[^)]*?['\"]\s*>{1,2}", re.IGNORECASE)
_HEREDOC_EXECUTORS = {"osascript", "node", "perl", "ruby"}
_PROTECTED_AGENT_STATE = (
    "groksessions",
    "grokclxdelegates",
    "grokactivesessions",
    "claudesessionintent",
    "claudeprojects",
    "codexsessions",
)
_AGENT_CONFIG_ROOTS = {
    os.path.expanduser(f"~/{d}") for d in (".claude", ".codex", ".agents", ".grok")
}
# The old lookbehind was `(?<![>\d])`, and the `\d` silently exempted every fd-prefixed form:
# `echo x 2>> ledger` truncated or forged the approval store while `>> ledger` was denied. Only a
# preceding `>` or `&` may suppress a match now — those are the halves of `>>` and `>&`.
_ANY_REDIRECT = re.compile(r"(?<![>&])>>?[|!&]*\s*['\"]?([^\s'\"><|;&]+)")
# A redirection may precede the command word (`< /dev/null rm -rf /` is valid POSIX), which made
# the head `<` and matched no rule anywhere. Peeled before any head is taken.
_REDIR_LONE = re.compile(r"^\d?(?:<{1,3}|>{1,2})[|!]?$")
_REDIR_FUSED = re.compile(r"^\d?(?:<{1,3}|>{1,2})[|!]?&?\S+$")
# Anything that decides whether an action is authorized. The agent never writes these: a grant
# that can edit the grant checker turns one override into a permanent one. Prevention here is
# only as strong as static parsing (see the module header) — the point is that forging it takes
# a deliberate, named, guarded step instead of an ordinary append.
_ENFORCEMENT_FILES = ("user-approvals.txt", "pending-challenges.txt", "settings.json")
# The evidence ledger is what the Stop check measures against. If the agent can forge a row, the
# check is back to self-policing — so it joins the no-override class alongside the approval store.
# The other three markers GATE that check: selfcheck-stop returns early when clx-mutated-<key> is
# absent, so deleting the marker disarms the whole thing more cheaply than forging the ledger.
_EVIDENCE_MARKER = re.compile(r"clx-(?:evidence|mutated|selfcheck|handoff|approval)-[\w.-]*")


def _resolve_pathish(path):
    try:
        return os.path.normpath(os.path.expanduser(
            re.sub(r"\$\{?HOME\}?", "~", str(path)).strip("'\"")))
    except (TypeError, ValueError):
        return None


def _flag_value(toks, names, short=""):
    """Value of `--name V`, `--name=V`, or the fused `-oV` form."""
    out = []
    for i, tok in enumerate(toks):
        if tok in names and i + 1 < len(toks):
            out.append(toks[i + 1])
        for n in names:
            if n.startswith("--") and tok.startswith(n + "="):
                out.append(tok.split("=", 1)[1])
        if short and tok.startswith(short) and len(tok) > len(short):
            out.append(tok[len(short):])
    return out


def _write_targets(head, toks):
    """Paths this command WRITES — the output position only, never every argument it names.

    `curl -o`, `wget -O`, `patch`, `split`, `ex` and `find … -delete` were absent entirely: an
    ordinary-looking download rewrote the approval ledger and nothing matched it."""
    args = toks[1:]
    pos = [t for t in args if not t.startswith("-")]
    if head == "tee":
        return pos
    if head in ("rm", "srm", "trash", "shred", "truncate", "unlink", "chmod", "chown",
                "patch", "ex", "ed", "vi", "vim"):
        return pos
    if head in ("cp", "rsync", "ditto", "install", "ln", "mv", "split"):
        return pos[-1:] if len(pos) > 1 else []
    if head == "uniq":
        return pos[-1:] if len(pos) > 1 else []
    if head == "dd":
        return [a.split("=", 1)[1] for a in args if a.startswith("of=")]
    if head == "sed":
        return pos if any(a == "-i" or a.startswith("-i") or a == "--in-place"
                          or a.startswith("--in-place") for a in args) else []
    if head == "sort":
        return _flag_value(args, ("-o", "--output"), "-o")
    if head == "curl":
        return _flag_value(args, ("-o", "--output"), "-o") + _flag_value(args, ("-O",))
    if head == "wget":
        return _flag_value(args, ("-O", "--output-document"), "-O")
    if head == "find":
        return pos if any(a in ("-delete", "-exec", "-execdir") for a in args) else []
    return []


def _is_enforcement_file(path, cwd=None):
    """The approval ledger, the pending-challenge store, settings.json (whose `env` block reaches
    every hook child process, so a two-line edit there redirects the ledger), and the per-turn
    evidence ledger the Stop check measures against."""
    resolved = _resolve_pathish(path)
    if resolved is None:
        return False
    # `cd ~/.claude/security && uniq /etc/hosts user-approvals.txt` names the ledger by a bare
    # basename; without the cwd it resolved to the process directory and looked like any file.
    if cwd and not os.path.isabs(resolved) and not resolved.startswith(("$", "~")):
        resolved = os.path.normpath(os.path.join(cwd, resolved))
    # A Windows path arrives backslash-separated and normpath leaves it that way on POSIX, so
    # comparing against "/.claude" silently matched nothing and the whole check was a no-op there.
    # Lowercased throughout: the default macOS volume is case-INsensitive, so USER-APPROVALS.TXT
    # and ~/.CLAUDE/settings.json reach the real files while an exact compare waved them past.
    unified = resolved.replace("\\", "/").rstrip("/").lower()
    parent, _, base = unified.rpartition("/")
    if _EVIDENCE_MARKER.search(base):
        return True
    if unified == os.path.normpath(_APPROVAL_LEDGER).lower():
        return True
    # The CONTAINER counted for nothing: `rm -rf ~/.claude/security` took the ledger and the
    # challenge store together, and `rm -rf ~/.claude/hooks` disarmed every guard in one allowed
    # command. Anything at or under the security directory, and the hooks directory itself.
    if re.search(r"/\.claude/security(/|$)", unified) or unified.endswith("/.claude/hooks"):
        return True
    # `/security` alone matched any project's own security/settings.json and denied it with no
    # override; the enforcement store is only ever the one under an agent config root.
    if not (parent.endswith("/.claude") or parent.endswith("/.codex")):
        return False
    if base in _ENFORCEMENT_FILES:
        return True
    # A glob is not a different file: `rm ~/.claude/security/user-approvals*` hit the exact target
    # and the basename compare saw a name that matched nothing.
    return any(ch in base for ch in "*?[") and any(
        fnmatch.fnmatch(name, base) for name in _ENFORCEMENT_FILES)
_RSYNC_WRITE_PATH_OPTIONS = (
    "--backup-dir", "--partial-dir", "--temp-dir", "--log-file",
    "--write-batch", "--only-write-batch",
)
_OUTPUT_REDIRECT = re.compile(
    r"^(?:(?:\d+|\{[A-Za-z_][A-Za-z0-9_]*\})?(?:>>?|<>)|&>>?)[|!&]*(.*)$"
)


def _mentions_regular_chrome(text):
    compact = re.sub(r"[^a-z0-9]+", "", text.lower())
    return bool(re.search(r"library.*applicationsupport.*google.*chrome", compact)) or any(marker in compact for marker in (
        "libraryapplicationsupportgooglechrome", "comgooglechrome", "googlechrome"
    ))


def _compact_hits_protected(compact):
    return any(marker in compact for marker in _PROTECTED_AGENT_STATE) or (
        "grok" in compact and any(part in compact for part in ("sessions", "clxdelegates", "activesessions"))
    ) or ("claude" in compact and any(part in compact for part in ("sessionintent", "projects"))) \
        or ("codex" in compact and "sessions" in compact)


def _is_protected_agent_state(value):
    # Anchor the compact match to path tokens. Compacting the WHOLE command fired on prose:
    # a quoted payload fragment like "1i project-scoped" reads as "projects" once punctuation
    # is stripped and, paired with an unrelated ".claude" path elsewhere, false-blocked a
    # legit write to ~/.claude/skills. Quote-aware tokenize and keep only path-shaped tokens
    # — those with a '/' or a single unspaced word (a bare relative target such as the
    # `sessions` in `cd ~/.grok && rm -rf sessions`). A quoted multi-word fragment (interior
    # whitespace, no '/') is prose and is dropped. Variable-split real paths survive because
    # each half still lands in a path token. shlex failure falls back to the looser split.
    try:
        tokens = shlex.split(value)
    except ValueError:
        tokens = value.split()
    compact = "".join(
        re.sub(r"[^a-z0-9]+", "", token.lower())
        for token in tokens
        if "/" in token or not any(char.isspace() for char in token)
    )
    return _compact_hits_protected(compact)


def _protected_state_path(value, values, cwd=None):
    resolved = _expand_static_value(value, values)
    resolved = os.path.expanduser(os.path.expandvars(resolved))
    if cwd and resolved and not os.path.isabs(resolved) and not resolved.startswith(("$", "~")):
        resolved = os.path.join(cwd, resolved)
    normalized = os.path.normpath(resolved).replace("\\", "/").lower().rstrip("/")
    return bool(re.search(
        r"/\.(?:grok/(?:sessions|clx-delegates|active_sessions(?:\.json)?)|"
        r"claude/(?:session-intent|projects)|codex/sessions)(?:/|$)",
        normalized,
    ))


def _unquoted_output_targets(text):
    targets, quote, escaped, index = [], None, False, 0
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if escaped:
            escaped = False
            index += 1
            continue
        if quote:
            if char == "\\" and quote != "'":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char == "\\":
            escaped = True
            index += 1
            continue
        if char in ("'", '"'):
            quote = char
            index += 1
            continue
        if not (char == ">" and next_char != "(" or char == "<" and next_char == ">"):
            index += 1
            continue
        cursor = index + (2 if char == "<" else 1)
        if char == ">" and next_char == ">":
            cursor += 1
        while cursor < len(text) and text[cursor] in "|!&":
            cursor += 1
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        buf, word_quote, word_escaped = [], None, False
        while cursor < len(text):
            item = text[cursor]
            if word_escaped:
                buf.append(item)
                word_escaped = False
            elif word_quote:
                if item == "\\" and word_quote != "'":
                    word_escaped = True
                elif item == word_quote:
                    word_quote = None
                else:
                    buf.append(item)
            elif item == "\\":
                word_escaped = True
            elif item in ("'", '"'):
                word_quote = item
            elif item.isspace() or item in ";|&()":
                break
            else:
                buf.append(item)
            cursor += 1
        if buf:
            targets.append("".join(buf))
        index = max(cursor, index + 1)
    return targets


def _split_sql_statements(text):
    statements, buf, quote, line_comment, block_comment, index = [], [], None, False, False, 0
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
                buf.append(" ")
        elif block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                buf.append(" ")
                index += 1
        elif quote:
            buf.append(char)
            if char == quote:
                if next_char == quote:
                    index += 1
                    buf.append(text[index])
                else:
                    quote = None
        elif char == "-" and next_char == "-":
            line_comment = True
            buf.append(" ")
            index += 1
        elif char == "/" and next_char == "*":
            block_comment = True
            buf.append(" ")
            index += 1
        elif char in ("'", '"', "`", "["):
            quote = "]" if char == "[" else char
            buf.append(char)
        elif char == ";":
            statements.append("".join(buf).strip())
            buf = []
        else:
            buf.append(char)
        index += 1
    statements.append("".join(buf).strip())
    return [statement for statement in statements if statement]


def _sql_code_only(text, strip_identifiers=True):
    output, quote, index = [], None, 0
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if quote:
            output.append(" ")
            if char == quote:
                if next_char == quote:
                    output.append(" ")
                    index += 1
                else:
                    quote = None
        elif char == "'" or (strip_identifiers and char in ('"', "`", "[")):
            quote = "]" if char == "[" else char
            output.append(" ")
        else:
            output.append(char)
        index += 1
    return "".join(output)


def _sqlite_statement_read_only(statement):
    value = statement.strip()
    if re.fullmatch(
        r"\.(?:schema|tables|indexes|databases|dump|mode|show|dbinfo|sha3sum|headers|lint|eqp)(?:\s+\S+)*",
        value,
        re.IGNORECASE,
    ):
        return True
    structure = _sql_code_only(value)
    callable_code = _sql_code_only(value, strip_identifiers=False)
    if re.search(
        r"(?:^|[^A-Za-z0-9_])(?:[\"`\[])?(?:writefile|load_extension)(?:[\"`\]])?\s*\(",
        callable_code,
        re.IGNORECASE,
    ):
        return False
    if re.match(r"^\s*(?:select|explain)\b", structure, re.IGNORECASE):
        return True
    if re.match(r"^\s*with\b", structure, re.IGNORECASE):
        return bool(re.search(r"\bselect\b", structure, re.IGNORECASE)) and not re.search(
            r"\b(?:insert|update|delete|create|drop|alter|attach|detach|vacuum|reindex)\b|"
            r"\breplace\b(?!\s*\()",
            structure,
            re.IGNORECASE,
        )
    pragma = re.match(r"^\s*pragma\s+(.+?)\s*$", structure, re.IGNORECASE)
    if not pragma:
        return False
    body = pragma.group(1)
    return bool(re.fullmatch(
        r"(?:query_only\s*=\s*(?:on|1|true|yes)|busy_timeout\s*=\s*\d+|"
        r"(?:table_info|table_xinfo|index_info|index_xinfo|foreign_key_list|integrity_check|"
        r"quick_check|database_list|compile_options|function_list|module_list|pragma_list|"
        r"table_list|collation_list|data_version|schema_version|page_count|query_only|"
        r"foreign_keys|user_version|application_id|freelist_count)(?:\s*\([^)]*\))?)",
        body,
        re.IGNORECASE,
    ))


def _sed_print_only(args):
    scripts, expect_script, options = [], False, True
    for arg in args:
        if expect_script:
            scripts.append(arg)
            expect_script = False
        elif options and arg == "--":
            options = False
        elif options and arg in {"-n", "--quiet", "--silent", "-E", "-r"}:
            continue
        elif options and arg == "-e":
            expect_script = True
        elif options and arg.startswith("-ne"):
            if arg[3:]:
                scripts.append(arg[3:])
            else:
                expect_script = True
        elif options and arg.startswith("-e") and len(arg) > 2:
            scripts.append(arg[2:])
        elif options and arg.startswith("-"):
            if set(arg[1:]) <= {"n", "E", "r"}:
                continue
            return False
        elif not scripts:
            scripts.append(arg)
    address = r"(?:\d+|\$|/(?:\\.|[^/])*/)"
    command = rf"(?:{address}(?:\s*,\s*{address})?\s*)?(?:!\s*)?(?:p|=|l(?:\s+\d+)?)"
    pure_print = re.compile(rf"\s*{command}(?:\s*;\s*{command})*\s*;?\s*")
    return not expect_script and bool(scripts) and all(
        pure_print.fullmatch(script) or _sed_safe_substitution(script) for script in scripts
    )


def _sed_safe_substitution(script):
    value = script.strip()
    if len(value) < 4 or value[0] != "s" or value[1].isalnum() or value[1].isspace() or value[1] == "\\":
        return False
    delimiter, index = value[1], 2
    for _ in range(2):
        escaped = False
        while index < len(value):
            char = value[index]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == delimiter:
                index += 1
                break
            index += 1
        else:
            return False
    flags = value[index:].strip()
    if flags.endswith(";"):
        flags = flags[:-1].rstrip()
    return bool(re.fullmatch(r"[gp0-9IiMm]*", flags))


def _xxd_output_path(args):
    positional, index = [], 0
    options_with_value = {"-c", "-g", "-l", "-o", "-s", "-n"}
    while index < len(args):
        arg = args[index]
        if arg == "--":
            positional.extend(args[index + 1:])
            break
        if arg in options_with_value:
            index += 2
            continue
        if arg.startswith("-") and arg != "-":
            index += 1
            continue
        positional.append(arg)
        index += 1
    return positional[1] if len(positional) > 1 else ""


_READ_OK = object()   # sentinel: a simple command proven read-only w.r.t. protected paths
# Keywords that introduce or close a compound command. `{`/`}` and `!` are here too: they group
# and negate, they never touch a file. Wrappers like `time`/`exec` are NOT — _WRAPPERS re-checks
# their argv, and short-circuiting them here would skip that.
_SHELL_KEYWORDS = {"if", "elif", "else", "then", "fi", "while", "until", "do", "done",
                   "for", "case", "esac", "select", "{", "}", "!"}
# git subcommands that cannot write the working tree, the index, or refs. Deliberately excludes
# every ambiguous one — `branch`, `tag`, `remote`, `config` and `stash` are decided by their flags
# below, and anything absent (push, reset, clean, checkout, restore, switch, rm, add, commit,
# rebase, merge, worktree, submodule, gc, prune, filter-branch, update-ref) simply falls through.
# `symbolic-ref HEAD <ref>` moves HEAD and `reflog expire` deletes history — both were in this
# set and both write. They are out; branch/tag/remote/config/stash are decided by their flags.
_GIT_READ_SUBCOMMANDS = {
    "status", "log", "diff", "show", "rev-parse", "rev-list", "ls-files", "ls-tree", "cat-file",
    "describe", "blame", "annotate", "shortlog", "for-each-ref", "merge-base",
    "name-rev", "check-ignore", "count-objects", "whatchanged", "grep", "ls-remote", "var",
    "help", "version", "diff-tree", "diff-index", "verify-pack", "show-ref"}
# Environment prefixes that hand git a command to run; same class as `-c core.pager`.
_GIT_EXEC_ENV = re.compile(
    r"\bGIT_(?:PAGER|EDITOR|SEQUENCE_EDITOR|EXTERNAL_DIFF|SSH|SSH_COMMAND|ASKPASS|"
    r"PROXY_COMMAND|TEXTCONV_CACHE)\s*=")


def _protected_segment_reason(toks, seg_cwd=None):
    """Classify ONE simple command against protected agent state: _READ_OK when it is
    provably read-only on protected paths, a reason string when it provably writes into
    them, None when it cannot be proven read-only (caller falls through, fail closed).
    Redirects INTO protected paths are handled by the caller across the whole line."""
    # A shell keyword is not a command. `for f in <protected>/*.md; do wc -l "$f"; done` splits
    # into segments headed by `for`, `do` and `done`, none of which is in the read-only set
    # below — so every loop or `[ -f x ] && …` over a protected path fell through to the
    # fail-closed gate and a plain `wc -l` came back denied. Found by hitting it: an inventory
    # command that only counted lines was blocked and told to ask the owner for approval.
    toks = list(toks)
    # A subshell opens with a paren glued to the command (`(cd repo && git status)`), so the head
    # reads as `(cd` and matches nothing. Peel parens and keywords in ONE loop: they interleave —
    # `do (cd repo && …` is a keyword followed by a paren, and peeling only at the front missed it.
    while toks and (toks[0].startswith("(") or _norm_head(toks[0]) in _SHELL_KEYWORDS):
        if toks[0].startswith("("):
            toks = ([toks[0][1:]] if len(toks[0]) > 1 else []) + toks[1:]
            continue
        kw = _norm_head(toks[0])
        if kw in ("for", "case", "select"):
            # a word list runs nothing — unless it embeds a substitution, which does, and
            # split_sep() does not break `$(…)` out into its own segment
            if any("$(" in t or "`" in t for t in toks):
                return None
            # `case X in pat) cmd` carries its body on the SAME segment: `;;` is not a separator
            # split_sep() cuts on, so calling the whole header read-only hid `case a in a) rm -rf`.
            # The pattern list ends at the first token closing a paren; what follows is a command.
            body = next((toks[i + 1:] for i, t in enumerate(toks) if t.endswith(")")), [])
            return _protected_segment_reason(body) if body else _READ_OK
        toks = toks[1:]
    # A leading redirect is punctuation, not a command: peel it and judge what actually runs.
    # `done < file` leaves nothing behind and reads; `< /dev/null rm -rf /` leaves `rm -rf /`,
    # and returning READ_OK on the operator alone is what let that through.
    # Peeling the operator threw the TARGET away, so the same punctuation that used to hide the
    # command then hid the file it writes: `>> <ledger> echo "<digest>"` is a valid POSIX
    # self-mint of an owner approval, and `> /tmp/clx-evidence-<key> echo …` forges the ledger the
    # Stop hook measures [측정] claims against. Judge the target on the way past.
    while toks and (_REDIR_LONE.match(toks[0]) or _REDIR_FUSED.match(toks[0])):
        _op = toks[0]
        _lone = bool(_REDIR_LONE.match(_op)) and len(toks) > 1
        _tgt = toks[1] if _lone else re.sub(r"^\d?(?:<{1,3}|>{1,2})[|!]?&?", "", _op)
        if ">" in _op and _tgt and not _tgt.isdigit():
            if _is_enforcement_file(_tgt, seg_cwd):
                return "redirect onto enforcement config (ledger/challenge store/settings.json)"
            if _protected_state_path(_tgt, {}, seg_cwd):
                return "redirect into protected agent session/runtime state"
        toks = toks[2:] if _lone else toks[1:]
    if not toks:
        return _READ_OK            # bare `done` / `fi` / `then`, or a trailing `< file`
    head = _norm_head(toks[0])
    args = toks[1:]
    sed_reads_only = head == "sed" and _sed_print_only(args)
    rg_reads_only = head == "rg" and not any(arg == "--pre" or arg.startswith("--pre=") for arg in args)
    file_reads_only = head == "file" and not any(
        arg == "--compile" or (arg.startswith("-") and not arg.startswith("--") and "C" in arg[1:])
        for arg in args
    )
    sort_reads_only = head == "sort"
    if sort_reads_only:
        for position, arg in enumerate(args):
            path_value = ""
            if arg in {"-o", "-T", "--output", "--temporary-directory"} and position + 1 < len(args):
                path_value = args[position + 1]
            elif arg.startswith(("--output=", "--temporary-directory=")):
                path_value = arg.split("=", 1)[1]
            elif arg.startswith("-") and not arg.startswith("--"):
                for letter in ("o", "T"):
                    if letter in arg[1:]:
                        suffix = arg[arg.index(letter) + 1:]
                        path_value = suffix or (args[position + 1] if position + 1 < len(args) else "")
                        break
            if path_value and _protected_state_path(path_value, {}, seg_cwd):
                return "sort output/temp path enters protected agent session/runtime state"
        if any(arg == "--compress-program" or arg.startswith("--compress-program=") for arg in args):
            return "sort external program involving protected agent session/runtime state"
    # `git` is not read-only as a whole, but most of what an agent runs with it is. Judged by the
    # SUBCOMMAND, with the pre-subcommand options (`-C <dir>`, `-c k=v`) stepped over — without
    # this, a plain `git status` in the same command as a protected path fell through to the
    # fail-closed gate. Measured on the shapes actually typed this session: 12 of 15 real reads
    # were denied. Anything not proven read-only here still falls through as before.
    git_reads_only = False
    if head == "git":
        _sub, _k, _inject = "", 0, False
        while _k < len(args):
            _a = args[_k]
            # `-c core.pager=<cmd>` and `-c alias.x=!<cmd>` make git run <cmd> through sh, so a
            # "read-only" subcommand becomes arbitrary execution. Any config injection disqualifies
            # the whole invocation rather than trying to decide which keys are safe.
            if _a in ("-c", "--config-env") or _a.startswith(("-c", "--config-env=")):
                _inject = True
            # --exec-path=DIR fronts the PATH git uses for every helper it spawns. The two-token
            # form was skipped as an option pair and the fused form fell to the generic skip.
            if _a.startswith("--exec-path"):
                _inject = True
            if _a in ("-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
                      "--config-env"):
                _k += 2
                continue
            if _a.startswith("-"):
                _k += 1
                continue
            _sub = _a
            break
        _rest = args[_k + 1:]
        # `--output=<file>` on diff/show/log writes an arbitrary path; the env vars below hand git
        # a command to run for the same reason `-c core.pager` does.
        if any(a.startswith("--output") for a in _rest) or _inject:
            _sub = ""
        # Enumerating which SUBCOMMANDS read was only half the job: several of them take a flag
        # whose VALUE is a command line, so the subcommand stays read-only while git runs anything.
        # `grep -O<cmd>` / `--open-files-in-pager=<cmd>` open the pager, `ls-remote --upload-pack=`
        # and the fetch family's `--receive-pack=` run their side of the wire protocol locally, and
        # `--textconv`/`--ext-diff` route file contents through a configured program.
        if any(a in ("-O", "--textconv", "--ext-diff") or a.startswith(
                ("-O", "--open-files-in-pager", "--upload-pack", "--receive-pack",
                 "--textconv=", "--ext-diff=")) for a in _rest):
            _sub = ""
        if _sub == "help" and any(a in ("-w", "--web") for a in _rest):
            _sub = ""                      # `git help -w` launches the configured browser command
        if _sub in _GIT_READ_SUBCOMMANDS:
            git_reads_only = True
        elif _sub == "config":
            # a read flag must be the ONLY thing there: `config --get x user.name y` still writes
            git_reads_only = (any(a in ("--get", "--get-all", "--get-regexp", "-l", "--list")
                                  for a in _rest)
                              and len([a for a in _rest if not a.startswith("-")]) <= 1)
        elif _sub == "remote":
            git_reads_only = all(a in ("-v", "--verbose", "show", "get-url") or not a.startswith("-")
                                 for a in _rest) and not any(
                a in ("add", "remove", "rm", "rename", "set-url", "prune") for a in _rest)
        elif _sub == "branch":
            # `-a` LISTS branches here; it only means "annotate" for tag, which is why the two
            # subcommands cannot share one flag set. A bare positional CREATES a ref
            # (`git branch newname`), so listing is the no-positional form only.
            git_reads_only = (not any(
                a.startswith(("-d", "-D", "-m", "-M", "-c", "-C", "-u", "-f",
                              "--delete", "--move", "--copy", "--force", "--set-upstream",
                              "--unset-upstream", "--edit-description"))
                for a in _rest)
                and not [a for a in _rest if not a.startswith("-")])
        elif _sub == "tag":
            git_reads_only = (not any(
                a.startswith(("-d", "-a", "-s", "-f", "-m", "-F", "-u",
                              "--delete", "--annotate", "--sign", "--force", "--file"))
                for a in _rest)
                and not [a for a in _rest if not a.startswith("-")])
        elif _sub == "stash":
            git_reads_only = bool(_rest) and _rest[0] in ("list", "show")
    # awk reads only when its program provably runs nothing and writes nothing. The earlier form
    # looked for `system(`, `>`, `|&` and `| "` — and missed `system ("…")` with a space (legal for
    # a built-in), `"cmd" | getline` (which also executes), and `-f prog.awk`, whose program the
    # guard never sees at all. Any of those, and awk falls through to the write matchers.
    # `-f` was closed by a prefix test, which every OTHER spelling of "run a program I cannot see"
    # walks around: `--file=` does not start with `-f`, and gawk's `-l`/`--load` (shared object),
    # `-E` (program file, and it ends option parsing) and mawk's `-W exec` all load code too.
    awk_reads_only = head in ("awk", "gawk", "mawk", "nawk") and not any(
        (">" in a or "|" in a or "system" in a or "getline" in a or "close" in a
         or "ENVIRON" in a or a in ("-f", "-l", "-E", "-W", "-i")
         or a.startswith(("-f", "--file", "-l", "--load", "-E", "--exec", "-W",
                          "-i", "--include"))) for a in args)
    # `date -s` sets the system clock; every other form prints
    date_reads_only = head == "date" and not any(
        a == "-s" or a.startswith("--set") for a in args)
    # `uniq IN OUT` writes its SECOND positional — that is the whole finding. One positional or
    # none (`uniq -c`, `uniq f`, `… | uniq`) is the ordinary filter and must stay free, or a
    # pipeline over a transcript gets denied.
    uniq_reads_only = head == "uniq" and len([a for a in args if not a.startswith("-")]) <= 1
    xxd_output = _xxd_output_path(args) if head == "xxd" else ""
    if xxd_output and _protected_state_path(xxd_output, {}, seg_cwd):
        return "xxd output enters protected agent session/runtime state"
    xxd_reads_only = head == "xxd"
    plutil_reads_only = head == "plutil" and any(arg in {"-p", "-lint"} for arg in args) and not any(
        arg in {"-replace", "-insert", "-remove", "-convert", "-create", "-extract"} for arg in args
    )
    # `cd` writes nothing. Without it here, `cd ~/.claude && cat x` failed the "every segment is
    # provably read-only" test and fell through to the fail-closed branch — the prefix, not the
    # command, was what got the read denied.
    if head in {"cd", "echo", "printf", "ls", "cat", "stat", "du", "wc", "head", "tail", "grep", "shasum", "readlink", "md5", "jq", "cksum", "realpath", "hexdump", "diff", "cmp", "test", "[", "[[", "read", "true", "false", ":",
                # plain text filters: they read stdin/args and print. None of them opens a file
                # for writing, which is why they are safe as a set rather than case by case.
                # `uniq` is NOT here: its second positional is an OUTPUT file
                # (`uniq in out`), which made it a write primitive wearing a filter's name.
                # Every other name below was checked against its man page for an output flag.
                "cut", "tr", "nl", "rev", "comm", "join", "paste", "fold", "expand",
                "unexpand", "column", "od", "strings", "seq", "pwd", "printenv", "uname", "id",
                "whoami", "hostname", "basename", "dirname", "which", "type", "sha1sum",
                "sha256sum", "sha512sum", "md5sum", "b2sum", "col"
                } or rg_reads_only or git_reads_only or awk_reads_only or date_reads_only or file_reads_only or plutil_reads_only or sort_reads_only or xxd_reads_only or sed_reads_only or uniq_reads_only:
        return _READ_OK
    command_args = []
    for arg in args:
        if _OUTPUT_REDIRECT.match(arg):
            break
        command_args.append(arg)
    positional = [arg for arg in command_args if not arg.startswith("-")]
    if head in {"find", "gfind"} and not any(
        flag in args for flag in (
            "-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprint0", "-fprintf", "-fls",
        )
    ):
        return _READ_OK
    if head in {"cp", "rsync", "ditto"} and positional:
        if head == "rsync":
            if any(arg in {"--remove-source-files", "--remove-sent-files"} for arg in command_args):
                return "rsync source removal involving protected agent session/runtime state"
            for index, arg in enumerate(command_args):
                for option in _RSYNC_WRITE_PATH_OPTIONS:
                    option_value = ""
                    if arg == option and index + 1 < len(command_args):
                        option_value = command_args[index + 1]
                    elif arg.startswith(option + "="):
                        option_value = arg.split("=", 1)[1]
                    if option_value and _protected_state_path(option_value, {}, seg_cwd):
                        return "rsync auxiliary output into protected agent session/runtime state"
                if arg.startswith("-") and not arg.startswith("--") and "T" in arg[1:]:
                    suffix = arg[arg.index("T") + 1:].lstrip("=")
                    option_value = suffix or (command_args[index + 1] if index + 1 < len(command_args) else "")
                    if option_value and _protected_state_path(option_value, {}, seg_cwd):
                        return "rsync auxiliary output into protected agent session/runtime state"
        target_dir = next((arg.split("=", 1)[1] for arg in command_args if arg.startswith("--target-directory=")), "")
        for index, arg in enumerate(command_args[:-1]):
            if arg in {"--target-directory", "-t"}:
                target_dir = command_args[index + 1]
        destination = target_dir or positional[-1]
        if _protected_state_path(destination, {}, seg_cwd):
            return "copy/sync into protected agent session/runtime state"
        if "$" in destination or destination.startswith("~"):
            return "ambiguous copy/sync involving protected agent session/runtime state"
        return _READ_OK
    if head == "sqlite3":
        db = next((arg for arg in positional if _protected_state_path(arg, {}, seg_cwd)), "")
        statements = []
        after_db = False
        for arg in args:
            if arg == db:
                after_db = True
                continue
            if after_db and _OUTPUT_REDIRECT.match(arg):
                break
            if after_db and not arg.startswith("-"):
                statements.append(arg)
        command_values = [args[i + 1] for i, arg in enumerate(args[:-1]) if arg == "-cmd"]
        statements.extend(command_values)
        sql_statements = [
            sql
            for statement in statements
            for sql in _split_sql_statements(statement)
        ]
        if db and sql_statements and all(_sqlite_statement_read_only(sql) for sql in sql_statements):
            return _READ_OK
    return None


def _protected_agent_state_reason(text):
    """Fail closed on ambiguous protected-state writes; direct reads/backup-out remain
    available. Reads stay free in EVERY shape: when every simple command across pipelines,
    ';', '&&' and '||' is provably read-only on protected paths, allow — flags and pipeline
    structure are irrelevant. A single command proven to write into protected state blocks;
    anything the classifier cannot prove read-only falls through to the mutation matcher."""
    # Issuing a challenge grants nothing: only a later, exact owner echo can mint a ledger entry.
    # Treat the candidate command as data only for the direct, canonical issuer path. Shell
    # wrappers, aliases, shadow scripts, and compound commands continue through the normal scan.
    _issuer = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clx_grant.py")
    _parts = list(segments(text))
    if (
        len(_parts) == 1
        and len(_parts[0]) >= 3
        and _parts[0][0] == _issuer
        and _parts[0][1] == "issue"
        and not os.path.islink(_issuer)
    ):
        return None
    # The cwd has to be resolved BEFORE the "is this about protected state at all" test, not
    # after: `cd ~/.claude && cp /etc/hosts projects/victim` names no protected path in its own
    # text, so the whole analysis used to return immediately and the copy landed unexamined.
    _seg_cwd = ""
    for _seg in segments(text):
        if _seg and _norm_head(_seg[0]) in ("cd", "pushd"):
            _arg = next((t for t in _seg[1:] if not t.startswith("-")), "")
            _seg_cwd = os.path.expanduser(os.path.expandvars(_arg))
            break
    _cands = re.findall(r"[\w~$.{}/\\-]+", text) if _seg_cwd else []
    if not _is_protected_agent_state(text):
        if not any(_protected_state_path(c, {}, _seg_cwd) or _is_enforcement_file(c, _seg_cwd)
                   for c in _cands):
            return None
    # An enforcement file named RELATIVE to a `cd` never reaches check(), which is per-segment and
    # has no cwd: `cd ~/.claude/security && uniq /etc/hosts user-approvals.txt` truncated the
    # approval ledger through a bare basename.
    if _seg_cwd:
        for _seg in segments(text):
            _h = _norm_head(_seg[0]) if _seg else ""
            if any(_is_enforcement_file(t, _seg_cwd) for t in _write_targets(_h, _seg)):
                return "write to enforcement config (ledger/challenge store/settings.json)"
    # A redirect/tee whose output lands in a protected path blocks in every shape.
    for target in _unquoted_output_targets(text):
        if _protected_state_path(target, {}, None):
            return "redirect into protected agent session/runtime state"
    # …and the same target resolved against a `cd`. Every redirect check in this file worked on
    # absolute paths only, so `cd <security dir> && echo x >> <ledger>` — a complete self-mint of
    # an owner approval — was allowed while the `tee` form denied. Token-based, not text-based:
    # `text` here has already been through shlex, so a QUOTED message reads as a real redirect.
    if _seg_cwd:
        for _seg in segments(text):
            for _j, _tok in enumerate(_seg):
                if any(c.isspace() for c in _tok):
                    continue                   # message text, not an operator
                _cand = list(_ANY_REDIRECT.findall(_tok))
                if _tok.rstrip("|!&") in (">", ">>", "&>", "&>>") and _j + 1 < len(_seg):
                    _cand.append(_seg[_j + 1])
                if any(_is_enforcement_file(c, _seg_cwd) for c in _cand):
                    return "redirect onto enforcement config (ledger/challenge store/settings.json)"
    if _GIT_EXEC_ENV.search(text):
        return "git invoked with an environment variable that runs a command"
    parts = list(segments(text))
    statuses = []
    for toks in parts:
        status = _protected_segment_reason(toks, _seg_cwd or None)
        if isinstance(status, str):
            return status
        statuses.append(status)
    if parts and all(status is _READ_OK for status in statuses):
        return None
    # A known destroyer aimed at a protected path is PROVEN, not uncertain — it must not fall
    # into the grantable catch-all below, which exists for commands the parser cannot read.
    # Static assignments are resolved first: `D=~/.claude/projects; rm -rf $D` is the same act
    # as writing the path out, and treating it as "ambiguous" would let a grant open it.
    # Assignments must come from the RAW text: segments() drops a bare `D=…` segment, so reading
    # them off `parts` left `$D` unresolved and a plain `rm` looked merely ambiguous.
    _values = {}
    for _seg in split_sep(text):
        try:
            _stoks = shlex.split(_seg)
        except ValueError:
            _stoks = _seg.split()
        _j = 1 if _stoks and _stoks[0] in ("export", "readonly", "typeset", "declare") else 0
        while _j < len(_stoks):
            assign = re.match(r"^([A-Za-z_]\w*)=(.*)$", _stoks[_j], re.DOTALL)
            if not assign:
                break
            _values[assign.group(1)] = _expand_static_value(assign.group(2), _values)
            _j += 1
    for toks in parts:
        i = 0
        head = _norm_head(toks[i]) if i < len(toks) else ""
        positional = [t for t in toks[i + 1:] if not t.startswith("-")]
        # tee writes every argument; the others write their last one
        targets = (positional if head == "tee"
                   else positional[-1:] if head in ("cp", "rsync", "ditto", "install", "ln")
                   else positional[-1:] if head == "uniq" and len(positional) > 1
                   else positional if head in ("rm", "srm", "shred", "trash", "truncate",
                                               "unlink", "dd", "mv") else [])
        if any(_protected_state_path(t, _values, _seg_cwd or None) for t in targets):
            return "destructive write to protected agent session/runtime state"
    if re.search(
        r"(?:\b(?:rm|srm|mv|unlink|truncate|touch|chmod|chown|chgrp|install|dd|tee|mkdir|rmdir|"
        r"vacuum|reindex|rmtree|copytree|copyfile|cp|rsync|ditto|rename|symlink|system|spawn|"
        r"execFileSync|write_text|write_bytes|writeFileSync|appendFileSync|sed|ln|tar)\b|"
        # SQL keywords, minus the method-call form: `sys.path.insert(`, `str.replace(`,
        # `dict.update(` are ordinary code, and denying them denied plain reads. SQL never writes
        # `INSERT(`, and the shell shapes that matter (`find … -delete`) are not call-shaped
        # either. Split paths stay blocked by their own verb (`rmtree`, `rm`), not by these.
        r"\b(?:delete|drop|update|insert|replace|create|alter|attach|detach|analyze)\b(?!\s*\()|"
        r"\bremove\s*\(|"
        # sqlite dot-commands take a space-separated argument (`.read setup.sql`, `.restore db`).
        # The CALL form `.read()`/`.output()` is the Python/JS method — reading, not executing.
        r"\.\s*(?:write|append)\s*\(|\.(?:restore|import|read|output|once|backup|shell)\b(?!\s*\()|"
        r"\b(?:wal_checkpoint|incremental_vacuum)\b|"
        r"\bpragma\b\s+\w+\s*=|(?:>|>>|&>))",
        text,
        re.IGNORECASE | re.DOTALL,
    ):
        return "ambiguous mutation of protected agent session/runtime state"
    # Nothing protected actually NAMED, and nothing above proved a write: this is a read.
    # `_is_protected_agent_state` deliberately ORs its markers across the WHOLE command, so
    # `cd ~/.claude/hooks && grep session-intent guard.py` engaged the no-override class with a
    # `.claude` token here and the word `session-intent` there, then failed closed on a plain
    # grep. A guard that blocks reads buys nothing and teaches the agent to route around it —
    # which is how this was found: `grep session-intent guard-destructive.py` blocked itself.
    # Candidates come from the RAW text, because an interpreter program is a single shell token
    # (`ruby -e '…File.expand_path("~/.grok/sessions")'` has no token that resolves alone), and
    # bare words resolve against a leading `cd`. This gate sits AFTER the write matchers on
    # purpose: a split path (`root=Path.home()/".grok"; rmtree(root/"sessions")`) names nothing
    # resolvable, and must stay blocked by the verb rather than pass here.
    _cwd = ""
    for _seg in parts:
        if _seg and _norm_head(_seg[0]) in ("cd", "pushd"):
            _arg = next((t for t in _seg[1:] if not t.startswith("-")), "")
            _cwd = os.path.expanduser(os.path.expandvars(_expand_static_value(_arg, _values)))
            break
    for _cand in re.findall(r"[\w~$.{}/\\-]+", text):
        # also as home-relative: `Path.home().joinpath(".claude/session-intent/a")` yields the
        # bare `.claude/session-intent/a`, which is protected but matches nothing on its own
        if (_protected_state_path(_cand, _values, _cwd or None)
                or _protected_state_path(os.path.join("~", _cand), _values, None)):
            return "unrecognized operation involving protected agent session/runtime state"
    return None


def _mentions_chrome_state(text):
    compact = re.sub(r"[^a-z0-9]+", "", text.lower())
    return bool(re.search(r"library.*applicationsupport.*google.*chrome", compact))


def _mentions_keychain_state(text):
    return bool(_KEYCHAIN_STATE.search(text))


def _call_arguments(text, open_at):
    depth, quote, escaped, buf = 0, None, False, []
    for ch in text[open_at:]:
        if escaped:
            buf.append(ch); escaped = False; continue
        if ch == "\\" and quote:
            buf.append(ch); escaped = True; continue
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch; buf.append(ch); continue
        if ch == "(":
            depth += 1
            if depth > 1:
                buf.append(ch)
            continue
        if ch == ")":
            depth -= 1
            if depth == 0:
                return "".join(buf)
            buf.append(ch); continue
        if depth:
            buf.append(ch)
    # Group-normalization may conservatively peel a trailing ')' token before this
    # helper sees an interpreter script; keep the collected bounded arguments.
    return "".join(buf)


def _split_call_arguments(text):
    out, buf, depth, quote, escaped = [], [], 0, None, False
    for ch in text:
        if escaped:
            buf.append(ch); escaped = False; continue
        if ch == "\\" and quote:
            buf.append(ch); escaped = True; continue
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch; buf.append(ch); continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            out.append("".join(buf)); buf = []; continue
        buf.append(ch)
    out.append("".join(buf))
    return out


def _script_mutates_chrome(text):
    """Bind interpreter mutation calls to their path arguments/receiver."""
    if _mentions_regular_chrome(text) and re.search(
        r"\b(?:terminate|pkill|kill|killall)\b", text, re.IGNORECASE
    ):
        return True
    if _mentions_chrome_state(text) and re.search(
        r"\b(?:chmod|chown|utime|unlink|rename|truncate|rmdir)\b", text, re.IGNORECASE
    ):
        return True
    call_re = re.compile(r"(?P<name>[A-Za-z_]\w*)\s*\(", re.IGNORECASE)
    two_paths = {"rename", "replace", "move", "copy", "copy2", "copyfile", "copytree",
                 "renamesync", "copyfilesync", "cpsync", "mv", "cp", "symlink_to"}
    receiver_only = {"write_text", "write_bytes", "mkdir", "rmdir", "unlink", "symlink_to"}
    read_only = {
        "print", "log", "str", "repr", "len", "path", "home", "join", "joinpath",
        "expanduser", "homedir", "require", "read_text", "read_bytes", "exists",
        "is_file", "is_dir", "stat", "lstat", "listdir", "scandir", "glob",
        "iterdir", "resolve", "name", "process_iter", "get", "getenv", "fetch",
    }
    for match in call_re.finditer(text):
        name = match.group("name").lower()
        args = _split_call_arguments(_call_arguments(text, match.end() - 1))
        if name in read_only:
            continue
        if name == "open" and (len(args) < 2 or not re.search(r"['\"][^'\"]*[wax+]", args[1], re.IGNORECASE)):
            continue
        stmt_start = max(text.rfind(";", 0, match.start()), text.rfind("\n", 0, match.start())) + 1
        receiver = text[stmt_start:match.start()]
        targets = []
        if receiver.rstrip().endswith("."):
            targets.append(receiver)
            if name in two_paths:
                targets.extend(args[:2])
            elif name not in receiver_only:
                targets.extend(args[:1])
        elif args:
            targets.extend(args[:2] if name in two_paths else args[:1])
        if any(_mentions_chrome_state(target) for target in targets):
            return True
    return False


def _chrome_capability_reason(text, toks=None):
    """Block capabilities only when their executable target is regular Chrome."""
    toks = toks or []
    head = _norm_head(toks[0]) if toks else ""
    args = toks[1:] if toks else []
    if head.lower() == "chrome-cdp":
        return "chrome-cdp can quit regular Chrome and link its real profile"
    if not _mentions_regular_chrome(text):
        return None
    if head in ("kill", "pkill", "killall"):
        return "process termination of the user's regular Chrome"
    if head == "osascript" and re.search(r"\b(?:tell\s+(?:application|app)|quit\s+app)\b", text, re.IGNORECASE) and re.search(r"\bquit\b", text, re.IGNORECASE):
        return "AppleScript quit of the user's regular Chrome"
    if head in _CHROME_MUTATORS and any(_mentions_chrome_state(arg) for arg in args):
        # Copying the profile OUT (destination outside it) is a backup, not a mutation — the
        # owner has lost this store more than once. Still guarded, but grantable rather than
        # absolute, so an explicit approval can clear it. Anything landing INSIDE stays absolute.
        if head in ("cp", "rsync", "ditto", "tar"):
            positional = [a for a in args if not a.startswith("-")]
            if len(positional) >= 2 and not _mentions_chrome_state(positional[-1]):
                return "copy-out of the user's Chrome profile state"
        return "mutation/copy of the user's Chrome profile state"
    if re.match(r"^(?:python\d*(?:\.\d+)?|node|ruby|perl)$", head) and _script_mutates_chrome(text):
        return "scripted mutation of the user's Chrome profile state"
    if head == "find" and any(flag in args for flag in ("-delete", "-exec", "-execdir", "-ok", "-okdir")):
        return "find mutation under the user's Chrome profile state"
    if head in ("defaults", "plutil") and re.search(r"\b(?:write|delete|import|rename|replace|insert|remove)\b", text, re.IGNORECASE):
        return "mutation of the user's Chrome preferences"
    if head == "sed" and re.search(r"(?:\s-i\b|--in-place\b)", text, re.IGNORECASE):
        return "sed in-place mutation of the user's Chrome profile state"
    if head == "perl" and re.search(r"\s-[^\s]*i", text, re.IGNORECASE):
        return "perl in-place mutation of the user's Chrome profile state"
    if head == "xattr" and re.search(r"\s-(?:w|d|c)\b", text, re.IGNORECASE):
        return "xattr mutation of the user's Chrome profile state"
    if re.search(r"(?:^|\s)(?:>|>>|&>)\s*", text):
        return "redirect into the user's Chrome profile state"
    user_data = None
    for index, arg in enumerate(args):
        if arg.startswith("--user-data-dir="):
            user_data = arg.split("=", 1)[1]
        elif arg == "--user-data-dir" and index + 1 < len(args):
            user_data = args[index + 1]
    real_user_data = bool(user_data) and _mentions_chrome_state(os.path.expandvars(os.path.expanduser(user_data)))
    launches_regular = (
        head.lower() in {"google chrome", "google-chrome", "chrome"}
        or head == "open" and re.search(
            r"(?:^|\s)(?:-a|--application)\s+(?:['\"])?Google\s+Chrome(?:['\"])?(?:\s|$)",
            text,
            re.IGNORECASE,
        )
    )
    if launches_regular and not user_data:
        return "automation against a regular Chrome profile"
    if real_user_data:
        return "automation against a regular Chrome profile"
    return None


def _expand_static_value(value, values):
    """Conservatively resolve simple shell assignment chains used as later path targets."""
    out = value
    for _ in range(min(len(values) + 2, 16)):
        prior = out
        for name, resolved in values.items():
            if resolved is None:
                continue
            out = out.replace("${" + name + "}", resolved)
            out = re.sub(r"\$" + re.escape(name) + r"\b", lambda _m, v=resolved: v, out)
        out = os.path.expandvars(os.path.expanduser(out))
        if out == prior:
            break
    return out


def _expand_script_env(text, values):
    for name, value in values.items():
        if not value:
            continue
        quoted = repr(value)
        patterns = (
            r"os\.environ(?:\.get)?\(\s*['\"]" + re.escape(name) + r"['\"]\s*\)",
            r"os\.getenv\(\s*['\"]" + re.escape(name) + r"['\"]\s*\)",
            r"os\.environ\[\s*['\"]" + re.escape(name) + r"['\"]\s*\]",
            r"process\.env(?:\." + re.escape(name) + r"|\[\s*['\"]" + re.escape(name) + r"['\"]\s*\])",
            r"ENV(?:\.fetch\(\s*['\"]" + re.escape(name) + r"['\"]\s*\)|\[\s*['\"]" + re.escape(name) + r"['\"]\s*\])",
            r"\$ENV\{\s*['\"]" + re.escape(name) + r"['\"]\s*\}",
        )
        for pattern in patterns:
            text = re.sub(pattern, quoted, text)
    return text


def _chrome_static_assignment_reason(text):
    """Bind simple VAR=/VAR+= assignments to shell mutator targets across separators.

    This preserves protection for `P=...Chrome; rm "$P"` without correlating an
    unrelated Chrome read/documentation segment with a later /tmp mutation.
    """
    values = {}
    for segment in split_sep(text):
        literal_dynamic = set(re.findall(
            r"(?:^|\s)([A-Za-z_]\w*)\+?='[^']*(?:\$|~)[^']*'", segment
        ))
        try:
            toks = shlex.split(segment)
        except ValueError:
            toks = segment.split()
        i = 0
        if toks and toks[0] in ("export", "readonly", "typeset", "declare"):
            i = 1
        while i < len(toks):
            match = re.match(r"^([A-Za-z_]\w*)(\+?=)(.*)$", toks[i], re.DOTALL)
            if not match:
                break
            name, op, value = match.groups()
            resolved = None if name in literal_dynamic else _expand_static_value(value, values)
            prior = values.get(name, "")
            values[name] = (
                (prior or "") + resolved if op == "+=" and resolved is not None else resolved
            )
            i += 1
        if i >= len(toks):
            continue
        expanded_segment = [_expand_static_value(token, values) for token in toks[i:]]
        if expanded_segment != toks[i:]:
            reason = check(expanded_segment)
            if reason:
                return reason
        env_pos = next((pos for pos in range(i, len(toks)) if _norm_head(toks[pos]) == "env"), None)
        if env_pos is not None:
            i = env_pos + 1
            while i < len(toks) and toks[i].startswith("-"):
                i += 1
            while i < len(toks):
                inline = re.match(r"^([A-Za-z_]\w*)=(.*)$", toks[i], re.DOTALL)
                if not inline:
                    break
                name, value = inline.groups()
                values[name] = _expand_static_value(value, values)
                i += 1
        if i >= len(toks):
            continue
        head = _norm_head(toks[i])
        expanded_args = [_expand_static_value(token, values) for token in toks[i + 1:]]
        if head == "open":
            for pos, arg in enumerate(expanded_args):
                target = arg.split("=", 1)[1] if arg.startswith("--user-data-dir=") else (
                    expanded_args[pos + 1] if arg == "--user-data-dir" and pos + 1 < len(expanded_args) else ""
                )
                if target and _mentions_chrome_state(target):
                    return "automation against a regular Chrome profile via static assignment"
        payload = _expand_script_env(_expand_static_value(" ".join(toks[i + 1:]), values), values)
        if (
            head in _SHELLS and _mentions_chrome_state(payload)
            and re.search(r"\b(?:" + "|".join(sorted(_CHROME_MUTATORS)) + r")\b", payload)
            or re.match(r"^(?:python\d*(?:\.\d+)?|node|ruby|perl)$", head)
            and _script_mutates_chrome(payload)
        ):
            return "scripted mutation of the user's Chrome profile state via static assignment"
        if head not in _CHROME_MUTATORS:
            continue
        positional = [_expand_static_value(t, values)
                      for t in expanded_args if not t.startswith("-")]
        for resolved in positional:
            if _CHROME_STATE.search(resolved) or _CHROME_STATE_LOOSE.search(resolved):
                # same split as the direct path: destination outside the profile = backup
                if head in ("cp", "rsync", "ditto", "tar") and len(positional) >= 2 and not (
                        _CHROME_STATE.search(positional[-1])
                        or _CHROME_STATE_LOOSE.search(positional[-1])):
                    return "copy-out of the user's Chrome profile state"
                return "mutation/copy of the user's Chrome profile state via static assignment"
    return None


def split_sep(cmd):
    """Split on shell separators (; && || | & newline) that are OUTSIDE quotes, so a quoted
    `-c 'a; rm -rf /'` script (or an echoed "a; b" message) is NOT cut apart mid-quote — a
    plain regex split did that, leaving dangling quotes that defeated target matching. Quote
    tracking only, no backslash grammar: on desync shlex downstream falls back conservatively.
    A lone '&' backgrounds the preceding command and STARTS a new one, so `echo x & rm -rf /`
    must split (else the destructive tail hides behind a benign head); '&>' / '>&' are redirects,
    not separators."""
    out, buf, q, i, n = [], [], None, 0, len(cmd)
    while i < n:
        ch = cmd[i]
        if ch == "\\" and q != "'" and i + 1 < n:
            # Outside single quotes a backslash escapes the next char (it's a literal), so
            # `\"` must NOT toggle quote state and `\;`/`\&` are NOT separators. Without this,
            # `echo \"; rm -rf /` opened a phantom quote that swallowed the ; and hid the rm.
            if cmd[i + 1] == "\n":     # backslash-newline = line continuation; shell removes BOTH
                i += 2                 # (`rm -rf \<nl>/` runs `rm -rf /`) — else shlex glues \n onto the target
                continue
            buf.append(ch)
            buf.append(cmd[i + 1])
            i += 2
        elif q:
            buf.append(ch)
            if ch == q:
                q = None
            i += 1
        elif ch in ("'", '"'):
            q = ch
            buf.append(ch)
            i += 1
        elif ch == "|" and buf and (buf[-1] == ">" or (buf[-1] == "&" and len(buf) >= 2 and buf[-2] == ">")):
            buf.append(ch)          # >| / >>| / >&| clobber-override redirect, not a pipe
            i += 1
        elif ch == "\n" or ch == ";" or ch == "|":
            if cmd[i:i + 2] == "||":
                i += 1
            out.append("".join(buf))
            buf = []
            i += 1
        elif ch == "&":
            if cmd[i:i + 2] == "&&":
                out.append("".join(buf))
                buf = []
                i += 2
            elif cmd[i + 1:i + 2] == ">" or (buf and buf[-1] == ">"):
                buf.append(ch)          # &> or >& redirect — keep in the segment
                i += 1
            else:
                out.append("".join(buf))  # lone & = background operator = separator
                buf = []
                i += 1
        else:
            buf.append(ch)
            i += 1
    out.append("".join(buf))
    return out


def strip_heredocs(cmd):
    """Drop heredoc bodies — literal text like example commands inside `cat <<EOF`
    must not be parsed as commands (false-positive class). Opener lines stay.
    EXCEPTION: when the heredoc feeds a SHELL that runs stdin as its script
    (`bash <<EOF … EOF`, `sh <<-EOF`, `bash -s <<EOF`), the body IS that script and is
    statically visible — keep it so its destructive lines segment+check like `bash -c`.
    Data/interpreter consumers (cat/tee/make/python) still strip."""
    out, skip_until = [], None
    for ln in cmd.split("\n"):
        if skip_until is not None:
            if ln.strip() == skip_until:
                skip_until = None
            continue
        m = HEREDOC.search(ln)
        out.append(ln)
        if m and not _heredoc_feeds_shell(ln[:m.start()]):
            skip_until = m.group(2)
    return "\n".join(out)


def executable_heredocs(cmd):
    """Yield interpreter/AppleScript heredoc bodies; data heredocs remain inert prose."""
    lines = cmd.split("\n")
    i = 0
    while i < len(lines):
        opener = lines[i]
        match = HEREDOC.search(opener)
        if not match:
            i += 1
            continue
        delimiter = match.group(2)
        try:
            tokens = shlex.split(opener[:match.start()])
        except ValueError:
            tokens = opener[:match.start()].split()
        while tokens and (re.match(r"^[A-Za-z_]\w*=", tokens[0]) or _norm_head(tokens[0]) in _WRAPPERS):
            tokens = tokens[1:]
        head = _norm_head(tokens[0]) if tokens else ""
        body = []
        i += 1
        while i < len(lines) and lines[i].strip() != delimiter:
            body.append(lines[i])
            i += 1
        if head in _HEREDOC_EXECUTORS or re.match(r"^python\d*(?:\.\d+)?$", head):
            yield [head, "\n".join(body)]
        i += 1


def substitution_bodies(cmd):
    """Command substitution $(...) / `...` AND process substitution <(...) / >(...) / zsh =(...)
    all execute their inner command, so a destructive command inside one (`echo $(rm -rf /)`,
    `cat <(rm -rf /)`, `cat =(rm -rf /)`) is statically visible and must be re-checked. Returns the
    inner command strings, transitively (nested). Bounded so a pathological deep nest can't blow the
    5s budget. `=(` counts only at a WORD BOUNDARY so an array assignment `arr=(…)` is not a procsub."""
    out, seen, queue = [], set(), [cmd]
    if len(cmd) > 100_000:
        return out
    while queue and len(out) < 256:
        c = queue.pop()
        i, outer_quote, outer_escaped = 0, None, False
        while i < len(c):
            char = c[i]
            if outer_escaped:
                outer_escaped = False
                i += 1
                continue
            if outer_quote == "'":
                if char == "'":
                    outer_quote = None
                i += 1
                continue
            if char == "\\":
                outer_escaped = True
                i += 1
                continue
            if char == "'" and outer_quote is None:
                outer_quote = "'"
                i += 1
                continue
            if char == '"':
                outer_quote = None if outer_quote == '"' else '"'
                i += 1
                continue
            # zsh =(cmd) runs cmd into a temp file (sibling of <()/>()); only at a word boundary,
            # else `arr=(...)`/`files=(*.txt)` array assignments would be mis-read as procsub.
            eq_sub = (i + 1 < len(c) and c[i] == "=" and c[i + 1] == "("
                      and (i == 0 or not (c[i - 1].isalnum() or c[i - 1] == "_")))
            if (i + 1 < len(c) and c[i] in "$<>" and c[i + 1] == "(") or eq_sub:
                depth, j, quote, escaped = 1, i + 2, None, False
                while j < len(c) and depth:
                    char = c[j]
                    if escaped:
                        escaped = False
                    elif quote:
                        if char == "\\" and quote != "'":
                            escaped = True
                        elif char == quote:
                            quote = None
                    elif char == "\\":
                        escaped = True
                    elif char in ("'", '"'):
                        quote = char
                    elif char == "(":
                        depth += 1
                    elif char == ")":
                        depth -= 1
                    j += 1
                body = c[i + 2:j - 1] if depth == 0 else c[i + 2:j]
                if body and body not in seen:
                    seen.add(body)
                    out.append(body)
                    queue.append(body)
                i = j
                continue
            if char == "`":
                j, escaped = i + 1, False
                while j < len(c):
                    if escaped:
                        escaped = False
                    elif c[j] == "\\":
                        escaped = True
                    elif c[j] == "`":
                        break
                    j += 1
                body = c[i + 1:j]
                if body and body not in seen:
                    seen.add(body)
                    out.append(body)
                    queue.append(body)
                i = j + 1
                continue
            i += 1
    return out


def segments(cmd):
    for seg in split_sep(cmd):
        seg = seg.strip()
        if not seg:
            continue
        # shlex on huge segments blows the 5s PreToolUse timeout (fail-open).
        # Destructive heads live at the front; a bounded prefix keeps detection intact.
        if len(seg) > 100_000:
            seg = seg[:100_000]
        try:
            toks = shlex.split(seg)
        except ValueError:
            toks = seg.split()
        while toks and re.match(r"^[A-Za-z_]\w*=", toks[0]):
            toks = toks[1:]
        if toks:
            yield toks


# Exec-wrapper commands that run their trailing argv as a new command — a destructive
# command hidden behind one (env/timeout/nice/…) must be re-checked, exactly as sudo is.
# Otherwise `env FOO=1 rm -rf /` or `timeout 5 git reset --hard` slip past.
_WRAPPERS = {"env", "nice", "nohup", "command", "stdbuf", "setsid",
             "time", "ionice", "chrt", "timeout", "xargs", "exec",
             "watch", "coproc", "flock", "parallel", "busybox", "toybox", "script",
             "arch", "su", "caffeinate",  # caffeinate: macOS-native exec-wrapper (keep-awake)
             "strace", "ltrace", "nsenter", "unbuffer", "proxychains",  # exec-tracers (portability; Linux hosts)
             "noglob", "nocorrect"}  # zsh precommand modifiers — the Bash tool runs via zsh, next token is the command

# Destroyer heads that homebrew coreutils/findutils ship g-prefixed (grm/gcp/gdd/gtee/gshred/
# gchmod/gchown/gchgrp/gfind — all present on this host). check() de-g's these so `grm -rf /` hits
# the rm rule. `gdisk` is IN the set → NOT de-g'd (it is its own destroyer); grep/git/gzip/gmake/gsed
# de-g to non-members → untouched.
_DESTROYER_HEADS = {"rm", "srm", "dd", "tee", "shred", "wipefs", "sgdisk", "parted", "fdisk",
                    "gdisk", "cp", "chmod", "chown", "chgrp", "find"}


def _norm_head(name):
    """Basename with a leading zsh `=` (=rm) and a homebrew g-destroyer prefix (grm) peeled, so a
    g/=-prefixed destroyer matches the plain name — used where a raw token is tested against a head."""
    h = os.path.basename(name)
    if h[:1] == "=" and len(h) > 1:
        h = os.path.basename(h[1:])
    if h not in _DESTROYER_HEADS and h[:1] == "g" and h[1:] in _DESTROYER_HEADS:
        h = h[1:]
    return h


_BARE_GLOB = re.compile(r"^([*?\[{]|\.[*?\[])")   # a path component that matches broadly (no literal anchor)


def _literal_prefix(p):
    """Path up to (excluding) the first BARE-glob component, so a recursive `**` form is reduced to
    its real anchor: `/**/*`→`/`, `~/**/*`→`~`, `~/proj/**/*`→`~/proj`, `~/tmp*`→`~/tmp*` (no bare
    component). zsh `**` is default-on, so `~/**/*` descends the whole home tree like `~/*`."""
    out = []
    for c in p.split("/"):
        if _BARE_GLOB.match(c):
            break
        out.append(c)
    if not out:
        return "."            # first component is a bare glob → relative (`*`, `{}`): cwd, NOT root
    return "/".join(out) or "/"   # leading-empty component (absolute `/**/*`) → "/"


def _git_abbrev(gflags, *names):
    """git accepts any unambiguous prefix of a long option (`--ha`==`--hard`, `--for`==`--force`).
    True if a --flag is a prefix of a destructive option name. No false positive on a RUNNING command:
    if git ran the abbreviation and it prefixes a destructive name, it can only have resolved TO that
    option (a benign competitor would make it ambiguous → git refuses). Ambiguous prefixes never run,
    so blocking them is harmless. Mirrors the short-cluster fused-flag handling for long options."""
    for f in gflags:
        if not f.startswith("--") or len(f) <= 2:
            continue
        key = f[2:].split("=", 1)[0]
        if key and any(n.startswith(key) for n in names):
            return True
    return False

# Shells that run their `-c <string>` argument as a script. The string is a literal
# token, so a destructive command inside it (`bash -c 'rm -rf /'`, `zsh -lc '…'`) is
# statically visible — re-feed it through the pipeline instead of trusting the shell head.
_SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish", "csh", "tcsh"}
_SHELLSTR_WRAPPERS = {"env", "flock", "script", "su", "watch", "parallel"}   # hand a STRING to a shell


def _heredoc_feeds_shell(prefix):
    """True if the command on a heredoc opener line (text before `<<`) is a shell that runs its
    stdin as a script (`bash <<EOF`, `bash -s <<EOF`, behind assignments/exec-wrappers too), so the
    body must be checked not stripped. Data/interpreter heads (cat/tee/make/python) → False → strip."""
    try:
        toks = shlex.split(prefix)
    except ValueError:
        toks = prefix.split()
    while toks and (re.match(r"^[A-Za-z_]\w*=", toks[0]) or _norm_head(toks[0]) in _WRAPPERS):
        toks = toks[1:]
    return bool(toks) and _norm_head(toks[0]) in _SHELLS


def _shell_c_reason(head, args, cd_root=False, cd_chrome=False):
    """If this is `<shell> -c/-lc/… <script>`, re-check the script string. The `-c` may be
    fused into a short-flag cluster (`-lc`, `-ic`), so match any single-dash flag containing
    'c'; the script is the first positional token after it. segments() handles chains,
    assignments, wrappers and further nesting, so recursion terminates (each level is a
    strictly smaller substring) and can only ever flag a genuinely destructive shape.
    cd_root pre-arms the inner scan for an outer `cd <root> && <shell> -c '…'`."""
    if head not in _SHELLS:
        return None
    # here-string: `bash <<< 'rm -rf /'` (or fused `bash <<<'rm -rf /'`) feeds the string to the
    # shell as its stdin script — statically visible, same class as -c. Re-scan the payload token.
    for i, a in enumerate(args):
        if a == "<<<":
            nxt = next((x for x in args[i + 1:] if not x.startswith("-")), None)
            if nxt is not None:
                return _scan_segments(segments(strip_heredocs(nxt)), cd_root=cd_root, cd_chrome=cd_chrome)
        elif a.startswith("<<<"):
            return _scan_segments(segments(strip_heredocs(a[3:])), cd_root=cd_root, cd_chrome=cd_chrome)
    ci = next((j for j, a in enumerate(args)
               if a.startswith("-") and not a.startswith("--") and "c" in a), None)
    if ci is None:
        return None
    for a in args[ci + 1:]:
        if a.startswith("-"):
            continue
        static = _chrome_static_assignment_reason(strip_heredocs(a))
        if static:
            return static
        return _scan_segments(segments(strip_heredocs(a)), cd_root=cd_root, cd_chrome=cd_chrome)
    return None


def _shellstr_wrapper_reason(head, args, cd_root=False, cd_chrome=False):
    """Wrappers that hand a command STRING to a shell instead of exec-ing a plain argv, so a
    destructive command inside one quoted token is invisible to _wrapped_reason (which treats
    it as an opaque command name). Re-segment the string. env -S/--split-string splits its value;
    flock -c runs the next token via sh -c; watch runs its positional command via sh -c.
    Recursion terminates (inner is a strictly smaller substring). cd_root pre-arms the inner scan
    for an outer `cd <root> && flock/su/watch/… '…'`."""
    def _refeed(tokens):
        return _scan_segments(
            segments(strip_heredocs(" ".join(tokens))), cd_root=cd_root, cd_chrome=cd_chrome
        )

    if head == "env":
        for i, a in enumerate(args):
            rest = None
            if a in ("-S", "--split-string"):
                rest = args[i + 1:]
            elif a.startswith("--split-string="):
                rest = [a.split("=", 1)[1]] + args[i + 1:]
            elif not a.startswith("--") and re.match(r"^-[A-Za-z]*S", a):
                frag = a[a.index("S") + 1:]
                rest = ([frag] if frag else []) + args[i + 1:]
            if rest is not None:
                return _refeed(rest)
        return None

    if head in ("flock", "script", "su"):     # flock/script/su -c <str> run the string via a shell
        ci = next((j for j, a in enumerate(args)
                   if a.startswith("-") and not a.startswith("--") and "c" in a), None)
        if ci is not None:
            for a in args[ci + 1:]:
                if a.startswith("-"):
                    continue
                return _refeed([a])
        return None

    if head == "watch":                       # watch [opts] <command…> — command runs via sh -c
        i = 0
        while i < len(args):
            a = args[i]
            if a in ("-n", "--interval"):      # only -n/--interval takes a value
                i += 2
                continue
            if a.startswith("-"):
                i += 1
                continue
            break
        return _refeed(args[i:]) if i < len(args) else None

    if head == "parallel":                    # parallel <template> ::: args — template runs via sh
        for a in args:                        # re-check each positional before :::; a quoted
            if a in (":::", "::::", ":::+", "::::+"):   # template is one opaque token _wrapped_
                break                                   # reason misses (option arity is irrelevant
            if a.startswith("-"):                       # here — bare non-option values re-feed
                continue                                # harmlessly as a non-destructive head).
            r = _refeed([a])
            if r:
                return r
        return None

    return None


def _wrapped_reason(toks):
    """A wrapper execs its trailing argv, but option arity differs per wrapper (env -i is
    valueless, env -u NAME takes one, timeout DURATION is positional…). Guessing which token
    is the command is fragile — a mis-guess either skips the real command or treats a value
    as it. So instead re-check EVERY plausible command start in the tail: any suffix beginning
    at a bare token (not an option, not a VAR=VAL assignment, not a pure number). check() only
    flags known-destructive shapes, so scanning extra suffixes can't create a false block, and
    a phantom-value skip can no longer hide `rm -rf /`."""
    tail = toks[1:]
    for i, t in enumerate(tail):
        if t.startswith("-"):
            continue
        if re.match(r"^[A-Za-z_]\w*=", t):            # env VAR=VAL
            continue
        if re.match(r"^\d+(\.\d+)?[smhd]?$", t):      # timeout DURATION / chrt PRIO
            continue
        r = check(tail[i:])                            # strictly shorter → terminates
        if r:
            return r
    return None


# sudo's own options precede the command; these take a separate value token (-u user, -g
# group, …). Non-value options (-E/-H/-n/-i/--preserve-env) take none. Skipping these lets us
# find the REAL command, so `sudo -u root rm …` can't hide rm behind the -u value.
_SUDO_VALUE_OPTS = {"-u", "-g", "-U", "-C", "-p", "-r", "-t", "-h", "-R", "-D"}


def _sudo_command(toks):
    """Return the argv sudo actually runs (skipping sudo's options + their values), or None."""
    i = 1
    while i < len(toks):
        t = toks[i]
        if t == "--":
            i += 1
            break
        if t in _SUDO_VALUE_OPTS:
            i += 2
            continue
        if t.startswith("-"):        # non-value option or --long=value (self-contained)
            i += 1
            continue
        break
    return toks[i:] if i < len(toks) else None


# Shell grouping / control keywords that PREFIX a command list — a destructive command
# inside `( rm -rf / )`, `{ rm -rf /; }`, `! rm -rf /`, `then rm -rf /` must be re-checked,
# not hidden behind the `(`/`{`/keyword head. (Array assignments `arr=(rm …)` are already
# peeled by segments()' assignment-strip, so this can't false-block them.)
_GROUPING_LEAD = {"(", "{", "!", "then", "else", "elif", "do", "if",
                  "while", "until", "for", "case"}
_FN_HEAD = re.compile(r"^[\w.-]*\(\)\{?$")   # function-def head: `()`/`name()`/`f(){` (zsh anon + named fn)


def _strip_grouping(toks):
    t = list(toks)
    while t and t[-1] in (")", "}", ";", ";;"):        # standalone closers/terminators
        t = t[:-1]
    if t and t[-1].endswith(")"):                      # fused subshell closer: `/)` → `/`
        t[-1] = t[-1].rstrip(")")                       # NOT `}`: that's `${HOME:?}` expansion, not a group
    while t:                                           # leading openers / control keywords
        h = t[0]
        if h in _GROUPING_LEAD:
            t = t[1:]
        elif _FN_HEAD.match(h):                        # fn-def head `()`/`name()`/`f(){` → peel, brace body follows
            t = t[1:]
        elif h == "function":                          # `function name { … }` → drop keyword (+ name if present)
            t = t[2:] if len(t) > 1 and re.match(r"^[\w.-]+$", t[1]) else t[1:]
        elif len(t) > 1 and t[1] == "()" and re.match(r"^[\w.-]+$", h):  # `name ()` split fn-def head
            t = t[2:]
        elif h and h[0] in "({":                       # fused opener: `(rm` → `rm`
            exp = _brace_expand(h) if h[0] == "{" else [h]
            if len(exp) > 1:                           # brace EXPANSION `{rm,ls}` runs `rm ls`; real head = first alt
                t = exp + t[1:]                        # (a `{ cmd; }` GROUP has a space so `{` is its own token)
            else:
                t = [h[1:]] + t[1:]                    # fused subshell/group opener `(rm` / `{cmd`
        # A redirection is legal BEFORE the command word, and `< /dev/null rm -rf /` then made the
        # head `<` — no rule in this file matched it, so every destructive check was skipped. Peel
        # the operator (and its operand when they are separate tokens) and judge what runs.
        elif _REDIR_LONE.match(h):
            t = t[2:] if len(t) > 1 else []
        elif _REDIR_FUSED.match(h):
            t = t[1:]
        else:
            break
    return t


_RAW_DEV = re.compile(r"^/dev/(r?disk|sd|nvme|hd|vd|mmcblk|mapper/)")
_HOME_RE = re.compile(r"\$\{HOME(?:[%#][^}]*|:[-?][^}]*)?\}|\$HOME\b")


def _norm_target(t):
    """Resolve a path target: $HOME forms → ~, strip a trailing /* glob, expanduser + normpath."""
    hn = _HOME_RE.sub("~", t)
    n = hn[:-2] or "/" if hn.endswith("/*") else hn
    n = os.path.normpath(os.path.expanduser(n))
    return re.sub(r"^//+", "/", n)


def _hits_root_or_home(t):
    """True if t resolves to /, home, or an ANCESTOR dir of home (/Users) — a target whose
    recursive rewrite/deletion destroys the system or the whole home."""
    n = _norm_target(t)
    home = os.path.expanduser("~")
    return bool(n) and ((home + os.sep).startswith(n.rstrip("/") + os.sep) or n in _CRITICAL_SYSDIRS)


def _brace_expand(t):
    """Single-brace static expansion: `a{x,y}z` -> [axz, ayz]. Unmasks `{/,}` `{~,}` `{$HOME,}`
    where a root/home target hides inside a brace alternative (os.path.dirname otherwise treats
    `{` as the dir and the target checks miss it). Requires a comma — `{foo}` stays literal."""
    m = re.search(r"\{([^{}]*,[^{}]*)\}", t)
    if not m:
        return [t]
    pre, post = t[:m.start()], t[m.end():]
    return [pre + alt + post for alt in m.group(1).split(",")]


def _hits_raw_dev(t):
    """A raw disk device target, INCL. one hidden behind brace expansion (`/dev/{r,}disk0` →
    /dev/rdisk0 /dev/disk0; zsh MULTIOS writes both). Mirrors the rm rule's brace-expand so a
    dd/tee/cp/mkfs/redirect device write can't be masked. Plain `/dev/null` → no match → ALLOW."""
    return any(_RAW_DEV.match(x) for x in _brace_expand(t))


_CD_SHELL_MOD = {"builtin", "eval", "noglob", "nocorrect"}   # precommand modifiers that run the cd/pushd
# BUILTIN in the CURRENT shell so cwd really changes (verified live). NOT `command` (runs external
# /usr/bin/cd in a subshell → cwd unchanged) nor fork wrappers (timeout/nohup/env fork or fail on cd).


def _cd_root_home(toks):
    """A `cd`/`pushd` segment landing in /, home, or a home ancestor. Returns True (root/home cd —
    arms the cwd-wipe check), False (cd elsewhere / `cd -` / bare `pushd` / `popd` — unknown cwd,
    disarms), or None (not a cwd-changer). Bare `cd` (no path) goes to $HOME so it arms; bare
    `pushd`/`popd` swap/pop the dir stack → unknown → disarm."""
    if not toks:
        return None
    while len(toks) > 1 and os.path.basename(toks[0]) in _CD_SHELL_MOD:   # peel builtin/eval/noglob cd
        toks = toks[1:]
    head = os.path.basename(toks[0])
    if head == "popd":
        return False                                         # pops the stack → cwd unknown → disarm
    if head not in ("cd", "pushd"):
        return None
    rest = toks[1:]
    if "-" in rest:                                          # `cd -` → previous dir, unknown → don't arm
        return False
    paths = [a for a in rest if not a.startswith("-")]       # skip cd -L/-P, pushd +N/-N rotation
    if not paths:
        return True if head == "cd" else False               # bare cd → $HOME (arm); bare pushd → swap (unknown)
    return _hits_root_or_home(paths[0])


def _cd_chrome_state(toks):
    """Track whether a shell chain enters the user's regular Chrome data tree."""
    if not toks:
        return None
    while len(toks) > 1 and os.path.basename(toks[0]) in _CD_SHELL_MOD:
        toks = toks[1:]
    head = os.path.basename(toks[0])
    if head == "popd":
        return False
    if head not in ("cd", "pushd"):
        return None
    paths = [a for a in toks[1:] if not a.startswith("-")]
    if not paths:
        return False
    target = os.path.normpath(os.path.expanduser(os.path.expandvars(paths[0])))
    chrome = os.path.expanduser("~/Library/Application Support/Google/Chrome")
    if os.path.isabs(target):
        return target == chrome or target.startswith(chrome + os.sep)
    return None


def _chrome_cwd_reason(toks):
    """Block writes after `cd` enters regular Chrome, including nested shell strings."""
    if not toks:
        return None
    head = _norm_head(toks[0])
    args = toks[1:]
    joined = " ".join(args)
    if head in _CHROME_MUTATORS or head == "find" and any(
        flag in args for flag in ("-delete", "-exec", "-execdir", "-ok", "-okdir")
    ):
        return f"{head} mutation inside the user's Chrome profile state"
    if any(re.search(r">[|!&]*[^>]*$", tok) for tok in toks if not any(c.isspace() for c in tok)):
        return "redirect inside the user's Chrome profile state"
    if re.match(r"^(?:python\d*(?:\.\d+)?|node|ruby|perl)$", head) and _CHROME_SCRIPT_MUTATION.search(joined):
        return f"{head} mutation inside the user's Chrome profile state"
    if head == "sed" and any(arg == "-i" or re.match(r"^-[A-Za-z]*i", arg) for arg in args):
        return "sed in-place mutation inside the user's Chrome profile state"
    if head == "perl" and any(re.match(r"^-[A-Za-z]*p?i", arg) for arg in args):
        return "perl in-place mutation inside the user's Chrome profile state"
    if head == "plutil" and any(
        arg in ("-replace", "-insert", "-remove", "-create", "-convert") for arg in args
    ):
        return "plutil mutation inside the user's Chrome profile state"
    if head == "xattr" and any(arg in ("-w", "-d", "-c") for arg in args):
        return "xattr mutation inside the user's Chrome profile state"
    if head in _SHELLS:
        return _shell_c_reason(head, args, cd_chrome=True)
    if head in _SHELLSTR_WRAPPERS:
        return _shellstr_wrapper_reason(head, args, cd_chrome=True)
    return None


def _is_cwd_broad(t):
    """A cwd-relative target that expands to (nearly) every entry: `*` `.` `./` `./*` `.[!.]*`
    `.??*` `*.log` … A specific name (`foo`, `./foo`, `.git`) is NOT broad. Mirrors the absolute
    broad-glob rule (line ~454) so `cd / && rm -rf *` matches `rm -rf /*` policy exactly."""
    b = t.strip().rstrip("/")
    if b in ("", ".", "*"):
        return True
    return bool(re.match(r"^([*?\[{]|\.[*?\[])", os.path.basename(b)))


def _is_broad_wipe_head(toks):
    """Directly `rm -r[f] *|.|./*|.[!.]*` or `find . -delete/-exec rm` (specific-file deletes safe).
    De-g homebrew g-coreutils so `cd ~ && grm -rf *` / `gfind . -delete` wipe-after-cd is caught."""
    head = os.path.basename(toks[0])
    if head[:1] == "=" and len(head) > 1:              # zsh EQUALS: `cd ~ && =rm -rf *`
        head = os.path.basename(head[1:])
    if head not in _DESTROYER_HEADS and head[:1] == "g" and head[1:] in _DESTROYER_HEADS:
        head = head[1:]
    args = toks[1:]
    targets = [a for a in args if not a.startswith("-")]
    if head in ("rm", "srm"):
        recursive = any(f == "--recursive" or (f.startswith("-") and not f.startswith("--") and "r" in f.lower())
                        for f in args if f.startswith("-"))
        return recursive and any(_is_cwd_broad(t) for t in targets)   # ANY broad target wipes the root/home cwd (a benign sibling target like `rm -rf ls *` doesn't make `*` safe); a pure specific-file delete has none
    if head == "find":
        return "." in targets and (
            "-delete" in args
            or (any(f in ("-exec", "-execdir", "-ok", "-okdir") for f in args)
                and any(_norm_head(a) in ("rm", "srm") for a in args)))
    return False


def _broad_cwd_wipe(toks):
    """After a cd into root/home, a cwd-relative broad delete wipes it — directly OR behind any
    exec-wrapper (`timeout 5 rm -rf *`, `nohup rm -rf *`, `caffeinate rm -rf *`, `env X=1 rm -rf *`).
    Peel wrapper heads (mirroring _wrapped_reason's option/assignment/number-skipping suffix scan)
    so the resolved rm/find is seen; nesting recurses. `rm -rf foo` (specific file) stays safe."""
    if not toks:
        return False
    if _is_broad_wipe_head(toks):
        return True
    head = os.path.basename(toks[0])
    if head[:1] == "=" and len(head) > 1:                     # zsh EQUALS: `cd / && =bash -c '…'`
        head = os.path.basename(head[1:])
    # A shell / shell-string wrapper runs its -c/positional STRING in the INHERITED (already root/home)
    # cwd, so a broad wipe inside it wipes root exactly like a bare one. Re-scan the string with cd_root
    # pre-armed (an inner `cd /elsewhere` still disarms). Covers `cd / && bash -c 'rm -rf *'` etc.
    if head in _SHELLS and _shell_c_reason(head, toks[1:], cd_root=True):
        return True
    if head in _SHELLSTR_WRAPPERS and _shellstr_wrapper_reason(head, toks[1:], cd_root=True):
        return True
    wrap = head if head in _WRAPPERS else (head[1:] if head.startswith("g") and head[1:] in _WRAPPERS else "")
    if wrap:
        for i in range(1, len(toks)):
            t = toks[i]
            if t.startswith("-") or re.match(r"^[A-Za-z_]\w*=", t) or re.match(r"^\d+(\.\d+)?[smhd]?$", t):
                continue                       # wrapper option / VAR=VAL / DURATION → skip
            if _broad_cwd_wipe(toks[i:]):      # first+subsequent bare tokens: resolved cmd (recurse for nesting)
                return True
    return False


def _scan_segments(seg_list, cd_root=False, cd_chrome=False):
    """check() over a segment sequence WITH cross-segment cwd tracking: a `cd`/`pushd <root/home>`
    followed by a broad cwd wipe (`rm -rf *`, `find . -delete`) is caught, which the per-segment
    check() alone can't see. Used for the top-level command, $(...) bodies, AND `sh -c '…'` bodies,
    so `bash -c 'cd ~ && rm -rf *'` is blocked exactly like the bare form. cd_root pre-armed by a
    caller propagates an OUTER `cd <root>` into a shell-string body (`cd / && bash -c 'rm -rf *'`)."""
    for toks in seg_list:
        gtoks = _strip_grouping(toks)   # peel (/{/! so `(cd /` and `{ cd /` expose the real head
        cd = _cd_root_home(gtoks)
        if cd is not None:
            cd_root = cd
            chrome = _cd_chrome_state(gtoks)
            if chrome is not None:
                cd_chrome = chrome
            continue
        chrome = _cd_chrome_state(gtoks)
        if chrome is not None:
            cd_chrome = chrome
            continue
        if cd_root and _broad_cwd_wipe(gtoks):
            return "rm/find broad wipe of filesystem root or home (cwd set by a prior cd)"
        if cd_chrome:
            r = _chrome_cwd_reason(gtoks)
            if r:
                return r
        r = check(toks)
        if r:
            return r
    return None


def _find_exec_reason(args):
    """find's -exec/-ok argv launders a destructive command past the literal-`rm` check by
    running it through a shell (`-exec sh -c 'rm -rf /'`) or a g-prefixed name (`-exec grm …`).
    Slice each exec command (up to its `;`/`+` terminator) and re-feed through check(), which
    unwraps shells + de-g's — same as a top-level `sh -c '…'`. A `{}` placeholder or a non-root
    rm string is ALLOWed by check() itself, so the accepted find-exec `{}` limit is preserved."""
    i = 0
    while i < len(args):
        if args[i] in ("-exec", "-execdir", "-ok", "-okdir"):
            j = i + 1
            while j < len(args) and args[j] not in (";", "+"):
                j += 1
            cmd = args[i + 1:j]
            if cmd:
                r = check(cmd)
                if r:
                    return r
            i = j + 1
        else:
            i += 1
    return None


def check(toks):
    # BEFORE peeling: _strip_grouping discards a leading redirect's target, and the enforcement
    # redirect test far below only ever sees the peeled remainder. `> <ledger> echo hi` truncates
    # the approval store, and every grouping shape (subshell, if/for body) reaches here the same
    # way. Enforcement config is the no-override class, so this runs first and unconditionally.
    # Joining the tokens back with spaces re-fuses a QUOTED message across the seam, so a commit
    # message documenting one of these redirects was itself denied, with no override. A real
    # redirect operator carries no interior whitespace — shell metachars split tokens — which is
    # the same test the raw-device loop below already applies to message text.
    for _tok in (t for t in toks if not any(c.isspace() for c in t)):
        for _t in _ANY_REDIRECT.findall(_tok):
            if _is_enforcement_file(_t):
                return "redirect onto enforcement config (ledger/challenge store/settings.json)"
    for _j, _tok in enumerate(toks):                  # bare operator: the target is the next token
        if _REDIR_LONE.match(_tok) and ">" in _tok and _j + 1 < len(toks):
            if _is_enforcement_file(toks[_j + 1]):
                return "redirect onto enforcement config (ledger/challenge store/settings.json)"
    stripped = _strip_grouping(toks)
    if stripped != toks:                               # grouping peeled → re-check the real head
        return check(stripped) if stripped else None

    # Output redirection to a RAW disk device destroys it regardless of the command:
    # `cat x > /dev/disk0`, `dd if=/dev/zero > /dev/rdisk0`, `echo >/dev/sda`. Safe device
    # sinks (/dev/null, /dev/stdout, /dev/tty, 2>&1) don't match _RAW_DEV, so they ALLOW.
    for j, tok in enumerate(toks):
        # A genuine fused redirect (`cmd>/dev/disk0`) or a bare `>` operator token has NO interior
        # whitespace — shell metachars split tokens. A quoted MESSAGE that merely mentions
        # `>/dev/disk0` (echo/commit text) is one shlex token WITH spaces; skip those so message
        # text never false-positives. zsh redirect-op suffixes ([|!&]*): bash >| clobber, zsh >!
        # clobber-override, >& redirect-both. Target = rest after the op, or the next token when
        # the op ends this one. fd-dup >&2 keeps group="2" (not a raw dev) → ALLOW.
        if any(c.isspace() for c in tok):
            continue
        m = re.search(r"(?:>>?)[|!&]*([^>]*)$", tok)
        if not m:
            continue
        tgt = m.group(1) or (toks[j + 1] if j + 1 < len(toks) else "")
        if _hits_raw_dev(tgt):
            return "redirect to a raw disk device"
        if _CHROME_STATE.search(tgt):
            return "redirect into the user's Chrome profile state"

    head = os.path.basename(toks[0])
    # zsh EQUALS (`=rm` → PATH location of rm) runs on the Bash tool's /bin/zsh; peel a leading `=`
    # first so `=rm`/`=grm`/`=nohup` hit the destroyer/g-strip/wrapper rules like the plain head.
    if head[:1] == "=" and len(head) > 1:
        head = os.path.basename(head[1:])
    # De-g a homebrew g-prefixed destroyer (grm/gdd/gchmod/gfind…) so it hits the same head rule as
    # the plain name — the cycle-30 g-strip only covered _WRAPPERS, leaving grm -rf / etc. ALLOW.
    if head not in _DESTROYER_HEADS and head[:1] == "g" and head[1:] in _DESTROYER_HEADS:
        head = head[1:]
    args = toks[1:]
    flags = [a for a in args if a.startswith("-")]
    targets = [a for a in args if not a.startswith("-")]

    joined = " ".join(toks)
    chrome_reason = _chrome_capability_reason(joined, toks)
    if chrome_reason:
        return chrome_reason

    # macOS `security` reads or mutates Keychain/auth state. That state is user-only:
    # even diagnostics can prompt, expose secrets, or change the login-keychain lock state.
    if head == "security":
        return "macOS Keychain/auth state is manual-only"

    # Reading or copying the backing store can expose credential material and can race
    # securityd. Documentation-only output remains available.
    script_reads_keychain = (
        re.match(r"^(?:python\d*(?:\.\d+)?|node|ruby|perl)$", head)
        and _KEYCHAIN_STATE_LOOSE.search(joined)
    )
    if head not in {"echo", "printf"} and (
        any(_mentions_keychain_state(arg) for arg in args) or script_reads_keychain
    ):
        return "direct Keychain store access is manual-only"

    lifecycle = {"login", "logout", "update", "upgrade", "install"}
    agent_lifecycle = head in {"claude", "codex", "grok"} and (
        bool(args) and args[0] in lifecycle
        or len(args) > 1 and args[0] == "auth" and args[1] in lifecycle
    )
    gh_lifecycle = head == "gh" and len(args) > 1 and args[0] == "auth" and args[1] in {
        "login", "logout", "switch", "refresh", "setup-git",
    }
    if agent_lifecycle or gh_lifecycle:
        return "auth/app lifecycle mutation is manual-only"

    if head in ("sudo", "doas", "pkexec") and len(toks) > 1:
        # sudo/doas/pkexec are privileged runners; options (-u root, -E, --preserve-env, …) precede
        # the command. The old `check(toks[1:])` made an option string the head → matched no rule →
        # total bypass. Suffix-scan the tail (shape-strict, catches destructive forms past any option
        # arity), then resolve the real command for the blanket privileged-rm. doas/pkexec option
        # arity differs but the tail suffix-scan is arity-agnostic, so it still catches rm.
        r = _wrapped_reason(toks)
        if r:
            return r
        cmd = _sudo_command(toks)
        if cmd and os.path.basename(cmd[0]) == "rm":
            return f"{head} rm"
        return None

    # Homebrew installs GNU coreutils g-prefixed (gtimeout/gnice/gnohup/gstdbuf/gtime); a `gX`
    # head is wrapper X, so `gtimeout 5 rm -rf /` must not slip. Only coreutils de-g to a real
    # wrapper, so this can't false-block a common g-command (git→"it", grep→"rep", etc.).
    wrap = head if head in _WRAPPERS else (head[1:] if head.startswith("g") and head[1:] in _WRAPPERS else "")
    if wrap and len(toks) > 1:
        r = _shellstr_wrapper_reason(wrap, args)   # env -S / flock -c / watch: string→shell
        if r:
            return r
        r = _wrapped_reason(toks)
        if r:
            return r

    if head == "eval" and len(toks) > 1:
        # eval concatenates its args and re-parses them as a command line (`eval "rm -rf /"`,
        # `eval rm -rf /`, `eval "a; rm -rf /"`) — join and re-feed through the pipeline. A leading
        # `--` (end-of-options) is consumed by the shell builtin; drop it so the cmd isn't hidden.
        e_args = args[1:] if args[0] == "--" else args
        for inner in segments(" ".join(e_args)):
            r = check(inner)
            if r:
                return r

    if head == "trap" and args:
        # `trap '<cmd>' SIGNAL` runs <cmd> on the signal — re-check the handler. A leading `--`
        # (POSIX end-of-options) shifts the handler to the next token; skip it so it isn't hidden.
        h_args = args[1:] if args[0] == "--" else args
        for inner in (segments(h_args[0]) if h_args else []):
            r = check(inner)
            if r:
                return r

    if head in _SHELLS and len(toks) > 1:
        r = _shell_c_reason(head, args)
        if r:
            return r

    if head in ("rm", "srm") and flags:       # srm = macOS secure-remove, same recursive wipe
        home = os.path.expanduser("~")

        def _wipes_home(p):
            # True if p IS / or home, OR an ANCESTOR dir of home (/Users, /home): deleting it —
            # or glob-expanding its children — destroys home. `$HOME/../*` → /Users → wipes home.
            return bool(p) and (home + os.sep).startswith(p.rstrip("/") + os.sep)

        for t in [c for t0 in targets for c in _brace_expand(t0)]:
            # normalize: $HOME / ${HOME} / ${HOME:?} / ${HOME:-x} / ${HOME%/*} / ${HOME#..} all
            # statically resolve toward the home dir (:+ is the alternate-value form, excluded);
            # trailing '/*' glob strip, then normpath collapses . / .. / dup slashes so traversal
            # that lands on root/home/ancestor (`/./*`, `/*/..`, `~/foo/../`, `$HOME/../*`) is caught.
            hn = re.sub(r"\$\{HOME(?:[%#][^}]*|:[-?][^}]*)?\}|\$HOME\b", "~", t)
            norm = hn[:-2] or "/" if hn.endswith("/*") else hn
            norm = os.path.expanduser(norm)
            norm = os.path.normpath(norm)
            norm = re.sub(r"^//+", "/", norm)   # normpath preserves a POSIX leading // — force one
            if t in ROOT_TARGETS or _wipes_home(norm) or norm in _CRITICAL_SYSDIRS:
                return "rm (flagged) on filesystem root, home, or a critical system dir"
            # Broad glob that matches (nearly) ALL children of / or home (or a home ANCESTOR) is
            # catastrophic: `/?*`, `/*`, `/[!.]*`, `~/.[!.]*`, `$HOME/../*` (→ /Users/*), and the zsh
            # recursive forms `/**/*`, `~/**/*`, `/**/`. Anchor on the LITERAL PREFIX (up to the first
            # bare-glob component) so `**` is reduced to its real root; the final component must itself
            # be a bare glob so anchored patterns (`~/tmp*`, `~/**/node_modules`) stay ALLOW.
            gpref = re.sub(r"^//+", "/", os.path.normpath(os.path.expanduser(_literal_prefix(hn))))
            if (_wipes_home(gpref) or gpref in _CRITICAL_SYSDIRS) and _BARE_GLOB.match(os.path.basename(hn.rstrip("/"))):
                return "rm (flagged) broad glob on filesystem root, home, or critical system dir children"

    # Format a raw device (mkfs.* on Linux, newfs_* on macOS). Gate on a /dev target so benign
    # `command -v mkfs`, `mkfs --help`, and formatting a plain file image are not false-blocked.
    if (head.startswith("mkfs") or head.startswith("newfs")) and any(_hits_raw_dev(a) for a in args):
        return "filesystem format of a raw device"

    if head == "diskutil" and targets:
        v0 = targets[0].lower()
        if v0 in ("erasedisk", "erasevolume", "partitiondisk", "reformat", "zerodisk",
                  "securedisk", "secureerase"):
            return "disk erase/partition (diskutil)"
        # macOS APFS / CoreStorage subverbs: deleteContainer|deleteVolume|eraseVolume|delete…
        if v0 in ("apfs", "ap", "corestorage", "cs") and len(targets) > 1 and \
                targets[1].lower().startswith(("delete", "erase", "destroy")):
            return "apfs/cs volume erase (diskutil)"

    # Only a RAW block device (disk/rdisk/sd/nvme…), not pseudo sinks (/dev/null,zero,stdout,tty) —
    # match _RAW_DEV like the redirect path, else `dd of=/dev/null` benchmarks false-block.
    if head == "dd" and any(a.startswith("of=") and _hits_raw_dev(a.split("=", 1)[1]) for a in args):
        return "raw write to a device"

    # Pure raw-device writers: a /dev argument is always the destruction.
    if head in ("tee", "shred", "wipefs", "sgdisk", "parted", "fdisk", "gdisk"):
        if any(_hits_raw_dev(a) for a in args):
            return head + " on a raw disk device"
    # cp clobbers only its DESTINATION (last positional) — reading FROM a device (imaging) is benign.
    if head == "cp" and targets and _hits_raw_dev(targets[-1]):
        return "cp onto a raw disk device"
    # asr restore reimages its --target device; hdiutil partition/erasedisk/burn repartitions one.
    if head == "asr" and any(t.lower() == "restore" for t in targets) and any(_hits_raw_dev(a) for a in args):
        return "asr restore onto a raw disk device"
    if head == "hdiutil" and targets and targets[0].lower() in ("partition", "erasedisk", "burn") \
            and any(_hits_raw_dev(a) for a in args):
        return "hdiutil partition/erase of a raw disk device"

    # chmod/chown/chgrp -R on / or home recursively rewrites every file's perms/owner → unusable
    # ( -R only; chmod's lowercase -r is a permission bit, not recursion).
    if head in ("chmod", "chown", "chgrp") and any(
        f == "-R" or f == "--recursive" or (f.startswith("-") and not f.startswith("--") and "R" in f)
        for f in flags
    ) and any(_hits_root_or_home(t) for t in targets):
        return head + " -R on filesystem root or home"

    # `find <root/home> … -delete` or `-exec/-execdir/-okdir rm …` annihilates everything under
    # it. BSD find (macOS) runs commands via -execdir/-okdir too, so the sibling flags must block.
    if head == "find" and any(_hits_root_or_home(t) for t in targets) and (
        "-delete" in args
        or (any(f in ("-exec", "-execdir", "-ok", "-okdir") for f in args)
            and any(_norm_head(a) in ("rm", "srm") for a in args))
    ):
        return "find -delete/-exec rm on filesystem root or home"

    # A shell-wrapped or g-prefixed -exec command hides `rm` from the literal-token check above
    # (`find / -exec sh -c 'rm -rf /'`); re-feed each exec argv so it is judged like any command.
    if head == "find":
        r = _find_exec_reason(args)
        if r:
            return r

    if head == "git" and args:
        # Strip git GLOBAL options before the subcommand — else `git -C <path> reset --hard`
        # made the path (a non-dash arg) look like the subcommand and every rule silently
        # no-op'd. -C/-c/--git-dir/--work-tree/--namespace/--exec-path/--super-prefix take a
        # separate value token; other global flags (-p, --no-pager, --bare…) take none.
        GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace",
                          "--exec-path", "--super-prefix"}
        i = 0
        while i < len(args):
            a = args[i]
            if a in GIT_VALUE_OPTS:
                i += 2
                continue
            if a.startswith("--") and "=" in a and a.split("=", 1)[0] in GIT_VALUE_OPTS:
                i += 1
                continue
            if a.startswith("-") and a != "--":
                i += 1
                continue
            break
        gargs = args[i:]
        sub = gargs[0] if gargs else None
        grest = gargs[1:]
        gflags = [a for a in grest if a.startswith("-")]
        gtargets = [a for a in grest if not a.startswith("-")]
        if sub == "push":
            # A leading '+' on a refspec (git push origin +main / +HEAD:main / +refs/heads/main)
            # is git's force-update mechanism — equivalent to --force for that ref. Strip it for
            # the main-detection and count it as forced, else `+main` slipped past the -f-only check.
            refs = [t[1:] if t.startswith("+") else t for t in gtargets]
            # fused short clusters (-fu/-uf/-fq/-fd) carry force too — match 'f' anywhere in a
            # short cluster like the git-clean check does; long --force* stay exact-token.
            forced = any(re.match(r"^-[a-zA-Z]*f", f) for f in gflags) \
                or _git_abbrev(gflags, "force", "force-with-lease") \
                or any(t.startswith("+") for t in gtargets)
            # --mirror force-updates AND deletes EVERY remote ref (main included) with no refspec —
            # a whole-remote overwrite. Block it regardless of an explicit main target.
            if _git_abbrev(gflags, "mirror"):
                return "git push --mirror (force-overwrites/deletes all remote refs)"
            # --all with force updates EVERY local branch (main/master included) on the remote — no
            # refspec, so to_main never fires; same whole-remote history-clobber class as --mirror.
            if forced and _git_abbrev(gflags, "all"):
                return "force-push --all (force-overwrites main/master among all branches)"
            to_main = any(t in ("main", "master") or t.endswith(":main") or t.endswith(":master")
                          or t.endswith("/main") or t.endswith("/master") for t in refs)
            if forced and to_main:
                return "force-push to main/master"
            deleting = _git_abbrev(gflags, "delete") or any(re.match(r"^-[a-zA-Z]*d", f) for f in gflags) or any(
                t.startswith(":") and (t in (":main", ":master") or t.endswith("/main") or t.endswith("/master"))
                for t in gtargets)
            if deleting and to_main:
                return "remote deletion of main/master"
        if sub == "reset" and _git_abbrev(gflags, "hard"):
            return "git reset --hard (destroys uncommitted work)"
        # `git branch -D main` force-deletes the trunk with unmerged commits — same
        # history-loss class as a force-push. `-d` (safe, merged-only) and `-D` on a feature
        # branch stay ALLOW: routine cleanup, and git itself refuses the unsafe -d case.
        if sub == "branch" and any(f == "-D" or _git_abbrev([f], "delete") and "-D" in gflags
                                   for f in gflags) and any(
                t in ("main", "master") or t.endswith("/main") or t.endswith("/master")
                for t in gtargets):
            return "git branch -D on main/master (force-deletes the trunk)"
        # checkout/restore with a '.' pathspec discards EVERY uncommitted tracked change —
        # same unrecoverable data loss as reset --hard. Gate on '.' (whole-tree discard) only,
        # so a targeted `git restore foo.py` / `git checkout main` / `git checkout dev -- f.py`
        # stays ALLOW, mirroring the broad-glob-vs-specific-path philosophy used for rm.
        if sub in ("checkout", "restore") and "." in gtargets:
            return "git checkout/restore . (discards all uncommitted work)"
        # force branch-switch (checkout -f / switch -f / switch --discard-changes) discards ALL
        # uncommitted tracked changes → same unrecoverable loss as reset --hard. Only checkout's
        # targeted pathspec form `git checkout -f -- <paths>` (nothing but flags before the `--`)
        # stays ALLOW like `git restore foo.py`. switch has NO pathspec mode, so any forced switch
        # DENYs; and a ref before the `--` (git checkout -f main --) is still a whole-tree
        # branch-switch discard → DENY (closes the trailing-`--` bypass).
        if sub in ("checkout", "switch") and (
            any(re.match(r"^-[a-zA-Z]*f", f) for f in gflags)
            or _git_abbrev(gflags, "force")
            or (sub == "switch" and _git_abbrev(gflags, "discard-changes"))
        ):
            pathspec_only = (
                sub == "checkout" and "--" in grest
                and not any(not t.startswith("-") for t in grest[:grest.index("--")])
            )
            if not pathspec_only:
                return "git checkout/switch --force (discards all uncommitted work)"
        if sub == "clean" and (any(re.match(r"^-[a-zA-Z]*f", f) for f in gflags) or _git_abbrev(gflags, "force")):
            return "git clean -f (deletes untracked files)"
        # -n means --no-verify only for commit; for push it's --dry-run, for merge --no-stat.
        # Fused clusters carry -n too (`-anm` = -a -n -m), like the clean/push force fix (cycle-25).
        if sub in ("commit", "push", "merge") and (
            _git_abbrev(gflags, "no-verify") or (sub == "commit" and any(re.match(r"^-[a-zA-Z]*n", f) for f in gflags))
        ):
            return "git hook bypass (--no-verify / -n)"

    # Deleting a whole agent-config ROOT (~/.claude, ~/.codex, ~/.agents, ~/.grok) wipes the
    # harness itself — rules, skills, hooks, owner context. Never legitimate agent work
    # (the sanctioned reinstall path MOVES the old tree aside). A path INSIDE one of them
    # stays ALLOW so ordinary maintenance — dropping a stale skill dir — still works.
    if head in ("rm", "srm", "trash") and flags:
        for t in [c for t0 in targets for c in _brace_expand(t0)]:
            resolved = re.sub(r"\$\{HOME(?:[%#][^}]*|:[-?][^}]*)?\}|\$HOME\b", "~", t)
            resolved = os.path.normpath(os.path.expanduser(resolved.rstrip("/")))
            if resolved in _AGENT_CONFIG_ROOTS:
                return "deletion of an agent-config root (~/.claude, ~/.codex, ~/.agents, ~/.grok)"

    # The approval ledger records what the USER authorized; the challenge store and settings.json
    # decide how that record is read. Appending used to be the "sanctioned flow" — that made the
    # agent able to mint its own approval, so EVERY write is refused now. The owner runs a command
    # directly in their own terminal or returns a challenge line; UserPromptSubmit is primary and
    # the trusted Codex transcript fallback covers a skipped event.
    # Writers only. `cat`/`echo`/`printf` write nothing on their own — they need a redirect, and
    # _ANY_REDIRECT below catches that — so listing them here would block plain reads.
    # Judged by the OUTPUT position, not by "the name appears somewhere in the argv". Checking
    # every positional denied `cp <settings> /tmp/backup.json`, `sed -n 1,20p <settings>` and
    # `dd if=<ledger> of=/dev/null` — all pure reads. A guard that blocks reading teaches the
    # agent to reach for a verb that is not on the list, and the list is what this file is.
    for _t in _write_targets(head, toks):
        if _is_enforcement_file(_t):
            return "write to enforcement config (ledger/challenge store/settings.json)"
    # An interpreter payload that names one of these files and calls a write. Same treatment the
    # Chrome path already gets (_CHROME_SCRIPT_MUTATION) and for the same reason: a one-liner is
    # the obvious way around a verb list. Static analysis cannot see a runtime-built path — that
    # ceiling is documented in the module header and is why minting, not this, is the real gate.
    if re.match(r"^(?:python\d*(?:\.\d+)?|node|ruby|perl|deno|bun)$", head):
        joined = " ".join(toks)
        # The path must sit INSIDE the write call's own parentheses. Matching "a write happens"
        # and "this name appears somewhere" independently blocked scripts that write file A while
        # merely mentioning file B — it fired on an edit to hooks-selftest.sh that quoted the
        # settings path in a string.
        for call in re.finditer(r"(?:open|write_text|write_bytes|writeFileSync|appendFileSync|"
                                r"File\.write)\s*\(([^)]{0,400})", joined, re.IGNORECASE):
            args = call.group(1)
            if not (_CHROME_SCRIPT_MUTATION.search(call.group(0))
                    or _SCRIPT_OPEN_WRITE.search(call.group(0))):
                continue
            if any(_is_enforcement_file(m) for m in re.findall(
                    r"[\w./~$-]*(?:user-approvals\.txt|pending-challenges\.txt|"
                    r"clx-evidence-[\w.-]*|settings\.json)", args)):
                return ("interpreter write to enforcement config "
                        "(ledger/challenge store/settings.json)")
    # `> f`, `>> f`, `&> f` — a redirect writes no matter which command produced it.
    for _tok in (t for t in toks if not any(c.isspace() for c in t)):
        if any(_is_enforcement_file(target) for target in _ANY_REDIRECT.findall(_tok)):
            return "redirect onto enforcement config (ledger/challenge store/settings.json)"

    if head == "chmod":
        mode_777 = any(t == "777" for t in targets)
        sys_target = any(
            t.startswith("/") and not t.startswith(("/tmp", "/private/tmp", "/Users", "/var/tmp"))
            for t in targets if t != "777"
        )
        if mode_777 and sys_target:
            return "chmod 777 on system paths"

    return None


# User-approval override ledger (see _consume_approval). CLX_APPROVAL_LEDGER overrides the path
# for clean testing; defaults to the real store.
_APPROVAL_LEDGER = os.environ.get("CLX_APPROVAL_LEDGER") or os.path.expanduser(
    "~/.claude/security/user-approvals.txt"
)


# Denials the classifier could not PROVE are writes. They are conservative fallbacks — an
# unparseable compound command that merely mentions a protected path lands here — so a misfire
# must be clearable by an explicit owner grant instead of being absolute.
_GRANTABLE_UNCERTAINTY = (
    "ambiguous mutation of protected agent session/runtime state",
    "unrecognized operation involving protected agent session/runtime state",
    "copy-out of the user's Chrome profile state",
)


def _is_protected_reason(reason):
    """No-override (user-only) denials: Chrome profile mutation, Keychain/auth, auth/app
    lifecycle, PROVEN writes to protected agent session/runtime state, enforcement config, and
    the internal fail-closed sentinel. These IGNORE any approval token. Everything else is the
    overridable class (git-destructive, rm, disk, and classifier uncertainty)."""
    if reason in _GRANTABLE_UNCERTAINTY:
        return False
    return (
        "Chrome" in reason
        or "Keychain/auth state" in reason
        or "direct Keychain store access" in reason
        or "auth/app lifecycle" in reason
        or "protected agent session/runtime state" in reason
        or "enforcement config" in reason
        or reason == "guard evaluation failed closed"
    )


def _claim_once(digest):
    """Close the read-modify-write window on the ledger.

    Reading the file, flipping the line and rewriting it is three steps; two tool calls landing
    together both read PENDING and both get allowed. Measured at 9 double-spends in 25 rounds
    before this existed. O_CREAT|O_EXCL is indivisible on POSIX and Windows alike, so exactly one
    caller wins. The marker is released after the flip — the USED state is the durable record,
    the marker only serializes the update. A caller that dies mid-flip would strand it, so
    markers older than a minute are swept first."""
    marker = os.path.join(_TMP, f"clx-approval-{digest}")
    try:
        if os.path.exists(marker) and time.time() - os.path.getmtime(marker) > 60:
            os.unlink(marker)
    except OSError:
        pass
    try:
        os.close(os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        return marker
    except OSError:
        return None


def _consume_approval(command):
    """One-time user override: if a PENDING ledger line's sha256 matches this EXACT command
    (utf-8, as received), flip it to USED via an atomic full-file rewrite and return True.
    Fail closed — unreadable/corrupt ledger, no match, or any I/O error yields no override and
    never crashes the guard. Callers must skip this for protected (no-override) denials."""
    digest = hashlib.sha256(command.encode("utf-8")).hexdigest()
    claim = _claim_once(digest)
    if claim is None:            # another call is consuming this exact approval right now
        return False
    try:
        return _consume_locked(digest)
    finally:
        try:
            os.unlink(claim)
        except OSError:
            pass


def _consume_locked(digest):
    try:
        with open(_APPROVAL_LEDGER, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        for idx, line in enumerate(lines):
            parts = line.split(None, 3)   # sha, state, iso, first-80-chars-of-command
            if len(parts) >= 2 and parts[0] == digest and parts[1] == "PENDING":
                rest = parts[3] if len(parts) >= 4 else ""
                used = datetime.datetime.now().astimezone().isoformat()
                lines[idx] = f"{digest} USED {used} {rest}".rstrip()
                tmp = f"{_APPROVAL_LEDGER}.tmp.{os.getpid()}"
                with open(tmp, "w", encoding="utf-8") as out:
                    out.write("\n".join(lines) + "\n")
                os.replace(tmp, _APPROVAL_LEDGER)   # atomic swap; no torn ledger
                return True
    except Exception:
        return False
    return False


def _capture_codex_transcript_approval(hook_data, command):
    """Recover the trusted owner prompt when Codex skips UserPromptSubmit.

    Only Codex supplies turn_id. The transcript path must resolve under this user's Codex
    sessions tree, and only the newest real user_message event is eligible. The existing grant
    module still owns challenge expiry, single-use claims, and ledger minting.
    """
    if not isinstance(hook_data.get("turn_id"), str) or not hook_data["turn_id"]:
        return False
    transcript = hook_data.get("transcript_path")
    if not isinstance(transcript, str) or not transcript.endswith(".jsonl"):
        return False
    try:
        root = os.path.realpath(os.path.expanduser("~/.codex/sessions"))
        path = os.path.realpath(transcript)
        if os.path.commonpath((root, path)) != root or not os.path.isfile(path):
            return False
        with open(path, "rb") as handle:
            size = os.fstat(handle.fileno()).st_size
            start = max(0, size - 1024 * 1024)
            handle.seek(start)
            raw = handle.read()
        lines = raw.splitlines()
        if start and lines:
            lines = lines[1:]
        prompt = ""
        for line in reversed(lines):
            try:
                item = json.loads(line)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if not isinstance(item, dict):
                continue
            payload = item.get("payload")
            if (
                item.get("type") == "event_msg"
                and isinstance(payload, dict)
                and payload.get("type") == "user_message"
            ):
                prompt = payload.get("message")
                break
        if not isinstance(prompt, str) or not prompt:
            return False
        from clx_grant import capture

        note = capture(prompt)
        return note.startswith("APPROVAL CAPTURED") and _consume_approval(command)
    except Exception:
        return False


def _deny(reason):
    protected = _is_protected_reason(reason)
    # Addressed to the OWNER, not to the agent — the agent reads this text too, and the old
    # wording read as a how-to ("approve the exact command into the ledger…"). The agent's only
    # legitimate move is to issue a challenge and let the owner decide.
    suffix = "" if protected else (
        " The agent must not work around this: no ledger edit, no settings change, no variant"
        " retry. To allow it, issue a challenge — `hooks/clx_grant.py issue \"<exact command>\"`"
        " — show the printed line, and let the owner send it back. The owner may instead run the"
        " exact command directly in their own terminal.")
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"guard-destructive: blocked — {reason} (policy: guides/work/git.md).{suffix}",
        }
    }))


try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
if not isinstance(data, dict) or data.get("tool_name") != "Bash":
    sys.exit(0)
tool_input = data.get("tool_input")
cmd = (tool_input or {}).get("command", "") if isinstance(tool_input, dict) else ""
if not isinstance(cmd, str) or not cmd:
    sys.exit(0)
raw_cmd = cmd   # exact received command — the string the approval sha256 is computed over

try:
    # ANSI-C quoting $'literal' (no escapes) == 'literal' — normalize so `rm -rf $'/'` is seen
    # as `rm -rf '/'`. Forms WITH backslash escapes ($'\x2f') are a runtime-resolved value =
    # accepted static limit, left untouched.
    cmd = re.sub(r"\$'([^'\\]*)'", r"'\1'", cmd)

    why = None
    for heredoc_tokens in executable_heredocs(cmd):
        why = _protected_agent_state_reason(" ".join(heredoc_tokens)) or check(heredoc_tokens)
        if why:
            break
    stripped = strip_heredocs(cmd)
    if not why:
        why = _protected_agent_state_reason(stripped)
    if not why:
        why = _chrome_static_assignment_reason(stripped)
    # split_sep() checks each &&/;/| segment independently, but `cd` changes cwd for LATER segments;
    # a cwd-relative broad wipe (`rm -rf *`) after a `cd` into root/home is a home/root wipe the
    # per-segment check can't see. Track that cd so `cd ~ && rm -rf *` is caught, `cd /tmp && rm -rf *`
    # and bare `rm -rf *` (cwd unknown) stay ALLOW.
    if not why:
        why = _scan_segments(segments(stripped))

    if not why:
        # scan heredoc-STRIPPED text: a $(...) inside a heredoc body is literal (quoted <<'EOF')
        # or a contrived edge (unquoted <<EOF) — treat it like segments() does, not a false block.
        for body in substitution_bodies(stripped):   # $(...) / `...` bodies the shell executes
            why = _protected_agent_state_reason(body) or _scan_segments(segments(body))
            # `$(echo git push -f origin main)`: the body itself is a harmless echo, but its
            # OUTPUT becomes the command the shell runs. Re-scan the printed payload as a
            # command so the expansion cannot launder a blocked one. Only for pure printers —
            # anything else is a runtime-resolved value, the documented static limit.
            if not why:
                for printed in segments(body):
                    if printed and printed[0] in ("echo", "printf") and len(printed) > 1:
                        payload = " ".join(printed[1:]).strip("'\"")
                        why = _scan_segments(segments(payload))
                        if why:
                            why += " (via command substitution)"
                            break
            if why:
                break

except Exception:
    why = "guard evaluation failed closed"
    try:  # diagnosis only — the deny itself stays no-override by design
        import traceback
        with open("/tmp/guard-destructive-error.txt", "a", encoding="utf-8") as _fh:
            _fh.write(traceback.format_exc() + "\n")
    except Exception:
        pass
if why:
    # Overridable denials (git-destructive, rm, disk, …) clear on a one-time verbatim user
    # approval recorded in the ledger. Protected agent session/runtime-state (and Chrome,
    # Keychain, auth-lifecycle) denials IGNORE any token — never consult the ledger for them.
    if not _is_protected_reason(why):
        if _consume_approval(raw_cmd) or _capture_codex_transcript_approval(data, raw_cmd):
            sys.exit(0)
    _deny(why)
sys.exit(0)
