#!/usr/bin/env python3
"""Ask the installed delegation backends what they serve, and flag a stale ~/.agents/models.toml pin.

The registry is hand-pinned, so nothing noticed when Codex shipped a newer generation: /gpt kept
delegating to the cheapest model of its own family. This detects that. It never rewrites the
registry — silently swapping a delegation model is worse than a loud warning; use /clx-model.

A role whose CLI is absent is skipped, not failed (core rule 2: a machine may omit external CLIs).
Prints OK/WARN/FAIL lines; exit 1 on any FAIL. config-doctor re-emits these into its own tally.
"""
import json
import os
import re
import shutil
import subprocess
import sys

try:
    import tomllib as toml
except ModuleNotFoundError:
    try:
        import tomli as toml
    except ModuleNotFoundError:
        toml = None

HOME = os.path.expanduser("~")
REGISTRY = f"{HOME}/.agents/models.toml"
CODEX_CONFIG = f"{HOME}/.codex/config.toml"
AGENT_TIERS = {"opus", "sonnet", "haiku", "fable"}
fails = []


def flat_toml(path):
    """tomllib arrived in 3.11 and stock macOS still ships 3.9, where this would otherwise no-op
    silently — exactly the blind spot it exists to remove. Reads only `key = "string"` lines and
    `[section]` headers, which is all the registry and the one Codex key need. Not a TOML parser:
    it would mangle a '#' inside a value, and no id or path we read contains one."""
    top, sections, cur = {}, {}, None
    with open(path, encoding="utf-8-sig") as fh:
        for raw in fh:
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                cur = sections.setdefault(line[1:-1].strip(), {})
                continue
            key, sep, val = line.partition("=")
            if not sep:
                continue
            val = val.strip()
            if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
                (top if cur is None else cur)[key.strip()] = val[1:-1]
            elif val in ("true", "false"):   # owner_pinned is a bare bool, not a string
                (top if cur is None else cur)[key.strip()] = val == "true"
    return top, sections


def load_roles():
    if toml:
        # utf-8-sig, not tomllib's own file reader: a BOM (any editor on Windows) makes
        # tomllib.load raise, and a registry that opens fine everywhere else is not invalid
        with open(REGISTRY, encoding="utf-8-sig") as fh:
            return toml.loads(fh.read()).get("roles", {})
    _, sections = flat_toml(REGISTRY)
    return {name[len("roles."):]: cfg for name, cfg in sections.items() if name.startswith("roles.")}


def codex_catalog_path():
    if not os.path.isfile(CODEX_CONFIG):
        return None
    try:
        if toml:
            with open(CODEX_CONFIG, "rb") as fh:
                return toml.load(fh).get("model_catalog_json")
        return flat_toml(CODEX_CONFIG)[0].get("model_catalog_json")
    except Exception:
        return None


def ok(msg):
    print(f"OK   {msg}")


def warn(msg):
    print(f"WARN {msg}")


def fail(msg):
    fails.append(msg)
    print(f"FAIL {msg}")


def generation(slug):
    """('gpt', 5, 6) for gpt-5.6-sol. None when the vendor does not use major.minor naming."""
    m = re.match(r"([a-z]+)-(\d+)\.(\d+)", slug or "")
    return (m.group(1), int(m.group(2)), int(m.group(3))) if m else None


def grok_offer():
    """`grok models` is authoritative for Grok — its slugs (4.20 vs 4.5) do not sort numerically."""
    binp = shutil.which("grok") or f"{HOME}/.grok/bin/grok"
    if not os.path.isfile(binp):
        return None
    try:
        proc = subprocess.run([binp, "models"], capture_output=True, text=True, timeout=25)
    except Exception as exc:  # a broken CLI is the CLI's problem, not a registry fault
        warn(f"grok_exec: `grok models` unavailable ({exc.__class__.__name__}) — pin not verified")
        return None
    if proc.returncode != 0:
        warn(f"grok_exec: `grok models` exited {proc.returncode} — pin not verified")
        return None
    out = proc.stdout
    default = (re.search(r"^Default model:\s*(\S+)", out, re.M) or [None, None])[1]
    listed, seen_header = [], False
    for line in out.splitlines():
        if line.startswith("Available models:"):
            seen_header = True
            continue
        if not seen_header:
            continue
        # the list ENDS at the first blank or unindented line — without a terminator a trailing
        # hint like "  Use `grok --model <id>` to switch." became a model the page offered
        if not line.strip() or not line[:1].isspace():
            break
        m = re.match(r"\s+\*?\s*([a-z][\w.\-]*)\s*(\(default\))?\s*$", line)
        if m:
            listed.append(m.group(1))
    if not listed:
        warn("grok_exec: `grok models` listed nothing parseable — pin not verified")
        return None
    return {"listed": listed, "default": default}


def codex_offer():
    """Codex's own model catalog. No live /v1/models exists for the ChatGPT backend, so this file
    (config `model_catalog_json`, else ~/.codex/models.json) is the only enumerable source."""
    if not shutil.which("codex"):
        return None
    for cand in (codex_catalog_path(), f"{HOME}/.codex/models.json"):
        cand = os.path.expanduser(cand) if cand else None
        if not cand or not os.path.isfile(cand):
            continue
        try:
            with open(cand, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            continue
        models = data.get("models") if isinstance(data, dict) else data
        if isinstance(models, list) and models:
            return {"models": [m for m in models if m.get("visibility", "list") == "list"],
                    "source": cand, "synced": (data or {}).get("synced_at") if isinstance(data, dict) else None}
    return "no-catalog"  # Codex is here but not enumerable — a different story from "not installed"


def check_grok(pin, offer):
    if pin not in offer["listed"]:
        fail(f"grok_exec pins '{pin}' — `grok models` lists {offer['listed'] or ['(none)']}")
    elif offer["default"] and offer["default"] != pin:
        warn(f"grok_exec '{pin}' differs from the CLI default '{offer['default']}'")
    else:
        ok(f"grok_exec '{pin}' is served and is the CLI default")


def check_codex(pin, effort, offer, owner_pinned=False):
    by_slug = {m["slug"]: m for m in offer["models"]}
    entry = by_slug.get(pin)
    if not entry:
        fail(f"gpt_exec pins '{pin}' — absent from the Codex catalog ({', '.join(sorted(by_slug)[:6])})")
        return
    efforts = [e["effort"] for e in entry.get("supported_reasoning_levels") or []]
    if efforts and effort not in efforts:
        fail(f"gpt_exec effort '{effort}' unsupported by '{pin}' (supports {', '.join(efforts)})")
    fam = generation(pin)
    if not fam:
        ok(f"gpt_exec '{pin}' is served")
        return
    siblings = [m for m in offer["models"] if generation(m["slug"]) == fam]
    best = min(siblings, key=lambda m: m.get("priority", 10**6))
    # Rank is a preference, not a defect. Once the owner has pinned deliberately, saying "sol ranks
    # higher" every single run is noise that trains people to ignore the whole report.
    if best["slug"] != pin and not owner_pinned:
        warn(f"gpt_exec '{pin}' is not the top of its generation — '{best['slug']}' ranks higher "
             f"({best.get('description', '')[:60]}). /clx-model gpt_exec={best['slug']}")
    newer = sorted({g for g in (generation(m["slug"]) for m in offer["models"])
                    if g and g[0] == fam[0] and g[1:] > fam[1:]})
    if newer:  # a generation the owner has never seen is news even when the tier was chosen
        warn(f"gpt_exec: newer Codex generation available — {', '.join(f'{v[0]}-{v[1]}.{v[2]}' for v in newer)}")
    if (not efforts or effort in efforts) and not newer:
        if best["slug"] == pin:
            ok(f"gpt_exec '{pin}' is the current top model, effort '{effort}' supported")
        elif owner_pinned:
            ok(f"gpt_exec '{pin}' effort '{effort}' — owner-pinned tier "
               f"(top of this generation is '{best['slug']}')")


SELF_DELEGATING = {"ultra"}      # Codex "ultra" spawns its own subtasks (core rule 2)
AGENT_EFFORTS = ("low", "medium", "high", "xhigh", "max")


def offers():
    """What can this machine actually serve, per role — the shared answer for the CLI, the doctor
    and the setup-ui switcher, so a chip the page offers is never one the checker would reject."""
    roles = load_roles()
    codex, grok = codex_offer(), grok_offer()
    # home-relative: this string is rendered in a browser page people screenshot and paste
    source = codex.get("source") if isinstance(codex, dict) else None
    if source and source.startswith(HOME):
        source = "~" + source[len(HOME):]
    out = {"roles": [], "codex_source": source,
           "codex_synced": codex.get("synced") if isinstance(codex, dict) else None}
    for name, cfg in roles.items():
        row = {"role": name, "model": cfg.get("model") or "", "effort": cfg.get("effort") or "",
               "owner_pinned": bool(cfg.get("owner_pinned")), "options": [], "efforts": [],
               "switchable": False, "reason": ""}
        if name == "gpt_exec":
            if not isinstance(codex, dict):
                row["reason"] = "no-codex" if codex is None else "no-catalog"
            else:
                fam = [m for m in codex["models"] if m["slug"].startswith("gpt-")]
                for m in sorted(fam, key=lambda m: m.get("priority", 10**6)):
                    row["options"].append({
                        "model": m["slug"], "note": (m.get("description") or "")[:64],
                        "efforts": [e["effort"] for e in m.get("supported_reasoning_levels") or []
                                    if e["effort"] not in SELF_DELEGATING]})
                row["switchable"] = bool(row["options"])
        elif name == "grok_exec":
            if grok is None:
                row["reason"] = "no-grok"
            else:
                # the Grok CLI lists models but not reasoning tiers, so effort stays text-only
                row["options"] = [{"model": s, "note": "CLI default" if s == grok["default"] else "",
                                   "efforts": []} for s in grok["listed"]]
                row["switchable"] = len(row["options"]) > 1
        elif name == "claude_exec" and not shutil.which("claude"):
            row["reason"] = "no-claude"
        else:
            row["options"] = [{"model": t, "note": "", "efforts": list(AGENT_EFFORTS)}
                              for t in sorted(AGENT_TIERS)]
            row["switchable"] = True
        current = next((o for o in row["options"] if o["model"] == row["model"]), None)
        if current:
            row["efforts"] = list(current["efforts"])
        elif name not in ("gpt_exec", "grok_exec"):
            # a legal `claude-*` pin is not one of the four tier names, but the tiers still apply —
            # deriving efforts from the pin alone left the row with none and made the page print
            # the Grok "no tiers exposed" note on a Claude subagent
            row["efforts"] = list(AGENT_EFFORTS)
        out["roles"].append(row)
    return out


def check_agent_tier(role, pin):
    if pin in AGENT_TIERS or pin.startswith("claude-"):
        ok(f"{role} '{pin}' is a valid Agent-tool tier")
    else:
        fail(f"{role} pins '{pin}' — not an Agent tier ({'/'.join(sorted(AGENT_TIERS))}) or claude-* id")


def main(argv):
    try:
        roles = load_roles()
    except Exception as exc:
        fail(f"{REGISTRY} unreadable/invalid: {exc.__class__.__name__}")
        return 1
    if not roles:
        fail(f"{REGISTRY} defines no [roles.*]")
        return 1

    if "--json" in argv:   # machine-readable feed for setup-ui
        print(json.dumps(offers(), ensure_ascii=False))
        return 0

    codex = codex_offer()
    if "--list" in argv:
        grok = grok_offer()
        print("\nregistry:")
        for name, cfg in roles.items():
            print(f"  {name:16} {cfg.get('model'):24} effort={cfg.get('effort')}")
        if isinstance(codex, dict):
            print(f"\ncodex catalog ({codex['source']}, synced {codex['synced']}):")
            for m in sorted(codex["models"], key=lambda m: m.get("priority", 10**6)):
                print(f"  {m['slug']:32} prio={m.get('priority')!s:5} {m.get('description', '')[:52]}")
        if grok:
            print(f"\ngrok models: {', '.join(grok['listed'])} (default {grok['default']})")
        return 0

    for name, cfg in roles.items():
        pin, effort = cfg.get("model"), cfg.get("effort")
        if not pin:
            fail(f"role {name} has no model")
            continue
        if name == "grok_exec":
            offer = grok_offer()
            if offer is None:
                ok("grok_exec skipped — Grok CLI not installed")
            else:
                check_grok(pin, offer)
        elif name == "gpt_exec":
            if codex is None:
                ok("gpt_exec skipped — Codex CLI not installed")
            elif codex == "no-catalog":
                warn(f"gpt_exec '{pin}' unverified — Codex is installed but exposes no model catalog")
            else:
                check_codex(pin, effort, codex, bool(cfg.get("owner_pinned")))
        elif name == "claude_exec" and not shutil.which("claude"):
            ok("claude_exec skipped — Claude Code CLI not installed")
        else:
            check_agent_tier(name, pin)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
