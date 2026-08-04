#!/usr/bin/env python3
"""Local viewer and model switcher for the clx harness install.

Serves one page and one JSON snapshot of the live machine (~/.claude,
~/.codex, ~/.agents). Python stdlib only, no network calls, no LLM.
Binds 127.0.0.1 with a per-run token; exits after 30 idle minutes.

ONE file is ever written: ~/.agents/models.toml, and only its `model`/`effort`
lines, and only to values the installed backends were just detected to serve.
Every other filesystem access in this file is a read. The previous registry is
kept as models.toml.bak before each change.
"""
import argparse
import json
import os
import re
import secrets
import shlex
import subprocess
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# ponytail: nothing else in the distro defines this port, so the literal lives
# here as the documented default; override with CLX_SETUP_UI_PORT or --port.
DEFAULT_PORT = 23456
IDLE_TIMEOUT = 30 * 60  # on-demand tool, not a daemon
DOCTOR_TIMEOUT = 60

HOME = Path.home()  # never bake a username/path literal into the source
CLAUDE_DIR = HOME / ".claude"
CODEX_DIR = HOME / ".codex"
AGENTS_DIR = HOME / ".agents"
HERE = Path(__file__).resolve().parent


# --- snapshot (all reads, all failure-tolerant) ------------------------------

def safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def file_count(path):
    n = 0
    for child in path.rglob("*"):
        try:
            if child.is_file():
                n += 1
        except OSError:
            pass
    return n


def target_state(path):
    if not path.is_dir():
        return {"exists": False, "file_count": 0}
    return {"exists": True, "file_count": safe(lambda: file_count(path), 0)}


def subdir_names(path):
    return sorted(p.name for p in path.iterdir() if p.is_dir())


def harness_count():
    """Harnesses live one locale level down (harness-library/ko/<name>/); count those,
    falling back to top-level dirs for a flat layout."""
    root = AGENTS_DIR / "harness-library"
    if not root.is_dir():
        return 0
    total = 0
    for name in subdir_names(root):
        total += len(subdir_names(root / name))
    return total or len(subdir_names(root))


MAX_READ_BYTES = 2_000_000   # config files are small; anything larger is not worth reading


def read_config_text(path):
    """Read a config file the viewer reports on — but only a real, own-directory, bounded
    file. A symlink planted at a known config path would otherwise pull an arbitrary file
    (an ssh key, say) into the page."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_READ_BYTES:
        raise OSError("not a plain in-place config file: %s" % path.name)
    return path.read_text(encoding="utf-8")


def read_config_raw(path):
    """Same guard as read_config_text, but WITHOUT universal-newline translation. Reading a CRLF
    registry through read_text() hands back LF, so writing it out again silently converted the
    whole file — reformatting a file the user never asked us to touch."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_READ_BYTES:
        raise OSError("not a plain in-place config file: %s" % path.name)
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def read_settings():
    return json.loads(read_config_text(CLAUDE_DIR / "settings.json"))


def hook_basename(command):
    """Hook commands can be whole shell snippets; prefer the script-looking token."""
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    if not parts:
        return ""
    token = next((p for p in parts if "/" in p or "\\" in p), parts[0])
    return os.path.basename(token.rstrip("/\\"))


def parse_hooks(settings):
    out = []
    for event, entries in (settings.get("hooks") or {}).items():
        commands = []
        for entry in entries or []:
            for hook in (entry or {}).get("hooks") or []:
                base = hook_basename((hook or {}).get("command") or "")
                if base and base not in commands:
                    commands.append(base)
        out.append({"event": event, "commands": commands})
    return sorted(out, key=lambda h: h["event"])


def user_context():
    root = AGENTS_DIR / "user"
    if not root.is_dir():
        return {"exists": False, "files": []}
    # names only: this is the owner's private folder, contents are never read
    files = safe(lambda: sorted(
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
    ), [])
    return {"exists": True, "files": files}


MODELS_PATH = AGENTS_DIR / "models.toml"
MAX_BODY_BYTES = 4096       # the switch payload is three short strings
# Whatever we write ends up inside `key = "<value>"`. A quote or newline there does not just corrupt
# the line, it appends whole TOML tables — so the shape is enforced before anything is written,
# independently of whether the catalog happened to list an effort for this role.
SAFE_VALUE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")


def write_file(path, text, mode=None):
    """Path.write_text(newline=) is 3.10+, and stock macOS ships 3.9 — the friend-facing default.
    open() has taken newline since forever."""
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    if mode is not None:
        os.chmod(path, mode)


def detector():
    """Reuse the installed detector instead of re-implementing catalog rules here — the page must
    never offer a model the command-line checker would then reject. Absent before install."""
    path = CLAUDE_DIR / "hooks" / "model-registry-check.py"
    if not path.is_file():
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location("clx_model_registry_check", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True     # loading it must not drop a __pycache__ into ~/.claude/hooks
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def model_offers():
    mod = detector()
    if mod is None:
        return {"available": False, "roles": []}
    data = mod.offers()
    data["available"] = True
    return data


WRITE_LOCK = threading.Lock()   # ThreadingHTTPServer: two clicks must not interleave read/write


def write_role(role, model, effort):
    """Replace the model/effort lines inside one [roles.<name>] block, leaving every comment,
    key order and unrelated role untouched. Line-targeted on purpose: a parse-and-dump would
    silently drop the comments that explain the pins."""
    text = read_config_raw(MODELS_PATH)
    newline = "\r\n" if "\r\n" in text else "\n"   # a CRLF registry must stay CRLF
    lines = text.splitlines(keepends=True)
    header = "[roles.%s]" % role
    start = next((i for i, ln in enumerate(lines) if ln.strip().startswith(header)), None)
    if start is None:
        raise KeyError("role not in registry: %s" % role)
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].lstrip().startswith("[")), len(lines))
    changed = 0
    for i in range(start + 1, end):
        stripped = lines[i].lstrip()
        for key, value in (("model", model), ("effort", effort)):
            # `model="x"` is legal TOML too — requiring a space silently skipped the line and
            # reported success while changing nothing
            if value is None or not re.match(re.escape(key) + r"\s*=", stripped):
                continue
            head, sep, tail = lines[i].partition("=")
            if not sep:
                continue
            comment = tail.split("#", 1)
            suffix = ("  #" + comment[1].rstrip("\r\n")) if len(comment) > 1 else ""
            lines[i] = '%s= "%s"%s%s' % (head, value, suffix, newline)
            changed += 1
    if not changed:
        raise KeyError("no model/effort line inside %s" % header)
    # A rename only needs the DIRECTORY to be writable, so the atomic write below would happily
    # replace a chmod-ed 444 registry and hand it back at 644. Someone who locked the file meant it.
    if not os.access(MODELS_PATH, os.W_OK):
        raise OSError("registry is not writable: %s" % MODELS_PATH.name)
    mode = MODELS_PATH.stat().st_mode & 0o777
    # never leave it half-written: stage a sibling, carry the original mode, then rename over it.
    # The backup carries the mode too — a 0600 registry must not be backed up world-readable.
    write_file(MODELS_PATH.with_suffix(".toml.bak"), text, mode)
    staged = MODELS_PATH.with_suffix(".toml.new")
    try:
        write_file(staged, "".join(lines), mode)
        os.replace(staged, MODELS_PATH)
    except Exception:
        if staged.exists():          # a truncated staging file must not outlive the failure
            staged.unlink()
        raise
    return changed


def apply_switch(payload):
    """Validate against freshly detected reality, then write. Returns (status, body)."""
    role = str(payload.get("role") or "")
    model = str(payload.get("model") or "")
    effort = payload.get("effort")
    effort = str(effort) if effort not in (None, "") else None
    # shape first, catalog second: a role whose backend exposes no effort tiers has an empty
    # allow-list, and that used to let any string through into the TOML
    for field, value in (("model", model), ("effort", effort)):
        if value is not None and not SAFE_VALUE.match(value):
            return 400, {"error": "bad-value", "field": field}
    # detect, validate and write under one lock: without it two clicks read the same registry and
    # the second write drops the first one's change
    with WRITE_LOCK:
        # a detector that raises must become a JSON error, not a dead handler thread and a
        # browser staring at "connection reset"
        try:
            offers = model_offers()
        except Exception as exc:
            return 500, {"error": "detect-failed", "detail": exc.__class__.__name__}
        if not offers.get("available"):
            return 409, {"error": "detector-missing"}
        row = next((r for r in offers["roles"] if r["role"] == role), None)
        if row is None:
            return 400, {"error": "unknown-role", "role": role}
        option = next((o for o in row["options"] if o["model"] == model), None)
        if option is None:
            return 400, {"error": "model-not-served", "model": model,
                         "served": [o["model"] for o in row["options"]]}
        if effort is not None and option["efforts"] and effort not in option["efforts"]:
            return 400, {"error": "effort-not-supported", "effort": effort,
                         "supported": option["efforts"]}
        try:
            write_role(role, model, effort)
        except (OSError, KeyError) as exc:
            # never echo an absolute path back to a page that gets screenshotted
            return 500, {"error": "write-failed", "detail": str(exc).replace(str(HOME), "~")}
        # re-detect ONCE and guard it: the write already landed, so a detector that raises here
        # must not kill the handler and leave the browser thinking nothing happened
        return 200, {"ok": True, "models": safe(lambda: read_config_text(MODELS_PATH)),
                     "offers": safe(model_offers, {"available": False, "roles": []})}


def run_doctor():
    script = CLAUDE_DIR / "hooks" / "config-doctor.py"
    if not script.is_file():
        return {"available": False}
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=DOCTOR_TIMEOUT, cwd=str(HOME),
        )
    except subprocess.TimeoutExpired:
        return {"available": True, "exit_code": None,
                "tail": ["config-doctor.py timed out after %ds" % DOCTOR_TIMEOUT]}
    except OSError as exc:
        return {"available": True, "exit_code": None, "tail": ["failed to run: %s" % exc]}
    lines = ((proc.stdout or "") + (proc.stderr or "")).splitlines()
    return {"available": True, "exit_code": proc.returncode, "tail": lines[-20:]}


def snapshot():
    settings = safe(read_settings, {}) or {}
    return {
        "installed": {
            ".claude": safe(lambda: target_state(CLAUDE_DIR), {"exists": False, "file_count": 0}),
            ".codex": safe(lambda: target_state(CODEX_DIR), {"exists": False, "file_count": 0}),
            ".agents": safe(lambda: target_state(AGENTS_DIR), {"exists": False, "file_count": 0}),
        },
        "plugins": safe(lambda: sorted(settings.get("enabledPlugins") or {}), []),
        "skills": safe(lambda: subdir_names(CLAUDE_DIR / "skills"), []),
        "hooks": safe(lambda: parse_hooks(settings), []),
        "harness_library": safe(harness_count, 0),
        "user_context": safe(user_context, {"exists": False, "files": []}),
        "models": safe(lambda: read_config_text(MODELS_PATH)),
        "model_offers": safe(model_offers, {"available": False, "roles": []}),
        # config-doctor takes seconds; it is fetched separately so the page — and the model
        # switcher on it — is usable immediately instead of after a blank wait.
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


# --- server -----------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "clx-setup-ui"
    sys_version = ""

    timeout = 15          # a half-open connection must not hold a worker thread forever

    def __getattr__(self, name):
        # every verb except GET (do_GET is a real attribute, so it wins here). Answer 403
        # rather than 405 when unauthenticated, so a non-GET verb cannot be used to confirm
        # the server exists without holding the token.
        if name.startswith("do_"):
            return self._reject_other_method
        raise AttributeError(name)

    def _reject_other_method(self):
        url = urlparse(self.path)
        if not self.allowed(parse_qs(url.query)):
            self.send_error(403, "forbidden")
            return
        self.send_error(405, "method not allowed")

    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def host_ok(self):
        port = self.server.server_address[1]
        hosts = {"127.0.0.1:%d" % port, "localhost:%d" % port}
        if (self.headers.get("Host") or "") not in hosts:
            return False
        origin = self.headers.get("Origin")
        return not origin or origin in {"http://%s" % h for h in hosts}

    def allowed(self, query):
        if not self.host_ok():
            return False
        token = (query.get("t") or [""])[0]
        return secrets.compare_digest(token, self.server.token)

    def do_GET(self):
        url = urlparse(self.path)
        authed = self.allowed(parse_qs(url.query))
        if url.path == "/" and self.host_ok():
            # The shell is static markup with no machine data in it; every byte about this
            # machine comes from the token-gated /api/* calls below. Serving it unauthenticated
            # is what makes a plain browser refresh work — the page strips the token from the
            # URL, so a gated "/" turned F5 into a raw 403.
            try:
                body = (HERE / "index.html").read_bytes()
            except OSError:
                self.send_error(500, "index.html missing")
                return
            if authed:
                self.server.last_seen = time.monotonic()
            self.respond(body, "text/html; charset=utf-8")
            return
        if not authed:
            self.send_error(403, "forbidden")
            return
        # only an AUTHENTICATED request keeps the server alive — otherwise anything that can
        # reach the port could hold it open past the idle timeout
        self.server.last_seen = time.monotonic()
        if url.path == "/api/snapshot":
            body = json.dumps(snapshot(), ensure_ascii=False).encode("utf-8")
            self.respond(body, "application/json; charset=utf-8")
        elif url.path == "/api/doctor":
            body = json.dumps(safe(run_doctor, {"available": False}),
                              ensure_ascii=False).encode("utf-8")
            self.respond(body, "application/json; charset=utf-8")
        else:
            self.send_error(404, "not found")

    def do_POST(self):
        # a real attribute, so it wins over __getattr__'s blanket rejection
        url = urlparse(self.path)
        if not self.allowed(parse_qs(url.query)):
            self.send_error(403, "forbidden")
            return
        self.server.last_seen = time.monotonic()
        if url.path != "/api/model":
            self.send_error(404, "not found")
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if not 0 < length <= MAX_BODY_BYTES:
            self.send_error(413, "body must be 1..%d bytes" % MAX_BODY_BYTES)
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self.send_error(400, "body must be JSON")
            return
        if not isinstance(payload, dict):
            self.send_error(400, "body must be a JSON object")
            return
        status, body = apply_switch(payload)
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.respond(raw, "application/json; charset=utf-8", status)

    def respond(self, body, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def idle_watch(httpd):
    while True:
        time.sleep(30)
        if time.monotonic() - httpd.last_seen > IDLE_TIMEOUT:
            httpd.shutdown()
            return


def main():
    env_port = os.environ.get("CLX_SETUP_UI_PORT", "").strip()
    parser = argparse.ArgumentParser(description="Read-only clx harness setup viewer.")
    parser.add_argument("--port", type=int,
                        # isdigit() is True for '²' and other non-decimal digits, which int() rejects
                        default=int(env_port) if env_port.isascii() and env_port.isdigit()
                        else DEFAULT_PORT)
    parser.add_argument("--no-open", action="store_true",
                        help="print the URL instead of opening a browser")
    args = parser.parse_args()
    if not 0 < args.port < 65536:
        print("port must be 1..65535 (got %s)" % args.port, file=sys.stderr)
        return 1

    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as exc:
        print("port %d unavailable (%s) - free it or pass --port N" % (args.port, exc),
              file=sys.stderr)
        return 1

    httpd.token = secrets.token_urlsafe(16)
    httpd.last_seen = time.monotonic()
    threading.Thread(target=idle_watch, args=(httpd,), daemon=True).start()
    port = httpd.server_address[1]
    url = "http://127.0.0.1:%d/?t=%s" % (port, httpd.token)
    # Nobody should have to retype a random token. Open it directly; only when a person is
    # actually watching (a TTY), so test harnesses and CI never launch a browser.
    opened = False
    if not args.no_open and sys.stdout.isatty():
        try:
            import webbrowser
            opened = webbrowser.open(url)
        except Exception:
            opened = False
    print("clx setup-ui on http://127.0.0.1:%d" % port, flush=True)
    print("  %s" % ("browser opened" if opened else "open this once (the token is single-run):"),
          flush=True)
    if not opened:
        print("  %s" % url, flush=True)
    print("  refresh works after that; Ctrl-C or 30 idle minutes to stop", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
