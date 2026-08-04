#!/usr/bin/env python3
import json
import hashlib
import os
import stat
import subprocess
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path


SCRIPT = Path(os.environ.get(
    "BROWSER_AUDIT_SCRIPT",
    str(Path.home() / ".claude/hooks/browser-audit.py"),
))
GUARD = Path(os.environ.get(
    "DESTRUCTIVE_GUARD_SCRIPT",
    str(Path.home() / ".claude/hooks/guard-destructive.py"),
))
CLAUDE_SETTINGS = Path(os.environ.get(
    "CLAUDE_SETTINGS_PATH", str(Path.home() / ".claude/settings.json")
))
CODEX_CONFIG = Path(os.environ.get(
    "CODEX_CONFIG_PATH", str(Path.home() / ".codex/config.toml")
))
HOOK_FILTER = Path(os.environ.get(
    "BROWSER_AUDIT_HOOK_FILTER",
    str(Path.home() / ".claude/hooks/browser-audit-hook.sh"),
))
SID_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
SID_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


class BrowserAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "browser-audit"
        self.env = os.environ.copy()
        self.env["CLX_BROWSER_AUDIT_ROOT"] = str(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def run_audit(self, *args, stdin=None, check=True):
        result = subprocess.run(
            ["python3", str(SCRIPT), *args],
            input=None if stdin is None else json.dumps(stdin),
            capture_output=True,
            text=True,
            env=self.env,
            timeout=5,
        )
        if check and result.returncode != 0:
            self.fail(f"audit command failed: {result.stderr or result.stdout}")
        return result

    def begin(self, sid=SID_A):
        result = self.run_audit(
            "begin",
            "--session", sid,
            "--purpose", "Read a Drive document without changing it",
            "--method", "isolated-browser",
            "--target", "https://drive.google.com/file/d/abc?token=secret#private",
            "--expected-change", "none",
            "--owned-resource", "/tmp/clx-browser/profile-a",
            "--rollback-step", "Close only the agent-created browser process",
            "--rollback-step", "Remove only /tmp/clx-browser/profile-a",
            "--verification", "Confirm no external content or account state changed",
        )
        return json.loads(result.stdout)

    def hook(self, phase, payload):
        result = self.run_audit(f"hook-{phase}", stdin=payload)
        return result, json.loads(result.stdout) if result.stdout.strip() else {}

    def test_begin_creates_private_detailed_reversible_record(self):
        created = self.begin()
        action = Path(created["action_dir"])
        plan = json.loads((action / "plan.json").read_text())
        rollback = (action / "ROLLBACK.md").read_text()
        index = (self.root / "README.md").read_text()
        self.assertEqual(plan["session_id"], SID_A)
        self.assertEqual(plan["state"], "planned")
        self.assertEqual(plan["expected_change"], "none")
        self.assertEqual(len(plan["rollback_steps"]), 2)
        self.assertEqual(plan["target"], "https://drive.google.com/file/d/abc")
        self.assertNotIn("secret", json.dumps(plan))
        self.assertIn("Remove only /tmp/clx-browser/profile-a", rollback)
        self.assertIn("YYYY-MM-DD/<session-id>/<action-id>", index)
        self.assertIn("10 days", index)
        self.assertEqual(stat.S_IMODE((action / "plan.json").stat().st_mode), 0o600)

    def test_browser_tool_is_denied_without_a_plan(self):
        _, output = self.hook("pre", {
            "session_id": SID_A,
            "tool_name": "mcp__browser__navigate",
            "tool_input": {"url": "https://example.com/?auth=hidden"},
        })
        decision = output["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertIn("browser-audit.py begin", decision["permissionDecisionReason"])

    def test_non_browser_tool_is_ignored_without_creating_state(self):
        result, output = self.hook("pre", {
            "session_id": SID_A,
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/example.txt"},
        })
        self.assertEqual(result.returncode, 0)
        self.assertEqual(output, {})
        self.assertFalse(self.root.exists())

    def test_browser_documentation_read_is_not_treated_as_browser_execution(self):
        result, output = self.hook("pre", {
            "session_id": SID_A,
            "tool_name": "Bash",
            "tool_input": {
                "command": "sed -n '1,80p' $HOME/.agents/skills/gstack/bin/chrome-cdp"
            },
        })
        self.assertEqual(result.returncode, 0)
        self.assertEqual(output, {})

    def test_isolated_browser_launch_still_requires_a_plan(self):
        payload = {
            "session_id": SID_A,
            "tool_name": "Bash",
            "tool_input": {
                "command": "open -na 'Google Chrome' --args --user-data-dir=/tmp/clx-browser/profile-a"
            },
        }
        _, denied = self.hook("pre", payload)
        self.assertEqual(denied["hookSpecificOutput"]["permissionDecision"], "deny")
        self.begin()
        _, allowed = self.hook("pre", payload)
        self.assertEqual(allowed, {})

    def test_planned_safe_browser_use_records_pre_and_post_without_payload(self):
        created = self.begin()
        pre, pre_output = self.hook("pre", {
            "session_id": SID_A,
            "tool_name": "mcp__browser__navigate",
            "tool_input": {"url": "https://example.com/?token=do-not-log"},
        })
        self.assertEqual(pre.returncode, 0)
        self.assertEqual(pre_output, {})
        self.hook("post", {
            "session_id": SID_A,
            "tool_name": "mcp__browser__navigate",
            "tool_input": {"url": "https://example.com/?token=do-not-log"},
            "tool_result": {"content": "xai-secret-value", "is_error": False},
        })
        events = (Path(created["action_dir"]) / "events.jsonl").read_text()
        self.assertIn('"event":"tool_pre"', events.replace(" ", ""))
        self.assertIn('"event":"tool_post"', events.replace(" ", ""))
        self.assertNotIn("do-not-log", events)
        self.assertNotIn("xai-secret-value", events)

    def test_regular_chrome_endpoint_is_always_denied_even_with_plan(self):
        self.begin()
        _, output = self.hook("pre", {
            "session_id": SID_A,
            "tool_name": "mcp__claude-in-chrome__tabs_context_mcp",
            "tool_input": {},
        })
        decision = output["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertIn("regular Chrome", decision["permissionDecisionReason"])

    def test_sessions_cannot_share_active_authorization(self):
        self.begin(SID_A)
        _, output = self.hook("pre", {
            "session_id": SID_B,
            "tool_name": "mcp__browser__navigate",
            "tool_input": {"url": "https://example.com"},
        })
        self.assertEqual(
            output["hookSpecificOutput"]["permissionDecision"], "deny"
        )

    def test_same_session_cannot_overwrite_an_open_plan(self):
        first = self.begin()
        second = self.run_audit(
            "begin",
            "--session", SID_A,
            "--purpose", "second",
            "--method", "isolated-browser",
            "--target", "https://example.com",
            "--expected-change", "none",
            "--rollback-step", "close owned browser",
            "--verification", "verify no change",
            check=False,
        )
        self.assertEqual(second.returncode, 2)
        self.assertTrue(Path(first["action_dir"]).exists())

    def test_finish_writes_result_and_closes_only_that_session(self):
        created = self.begin()
        self.run_audit(
            "finish", "--session", SID_A,
            "--status", "success",
            "--actual-change", "none",
            "--rollback-status", "not-needed",
            "--verification", "No external content changed",
        )
        action = Path(created["action_dir"])
        result = json.loads((action / "result.json").read_text())
        self.assertEqual(result["rollback_status"], "not-needed")
        self.assertFalse((self.root / ".active" / f"{SID_A}.json").exists())

    def test_prune_removes_only_owned_date_dirs_older_than_ten_days(self):
        old = self.root / (date.today() - timedelta(days=11)).isoformat()
        keep = self.root / (date.today() - timedelta(days=10)).isoformat()
        outside = Path(self.tmp.name) / "outside"
        old.mkdir(parents=True)
        keep.mkdir(parents=True)
        outside.mkdir()
        link = self.root / (date.today() - timedelta(days=12)).isoformat()
        link.symlink_to(outside, target_is_directory=True)
        self.run_audit("prune", "--days", "10")
        self.assertFalse(old.exists())
        self.assertTrue(keep.exists())
        self.assertTrue(link.is_symlink())
        self.assertTrue(outside.exists())

    def test_audit_root_symlink_is_rejected(self):
        outside = Path(self.tmp.name) / "outside-root"
        outside.mkdir()
        self.root.symlink_to(outside, target_is_directory=True)
        result = self.run_audit("prune", "--days", "10", check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("must not be a symlink", result.stderr)

    def test_wrapper_validation_is_static_and_hash_pinned(self):
        sentinel = Path(self.tmp.name) / "must-not-exist"
        wrapper = Path(self.tmp.name) / "safe-wrapper"
        wrapper.write_text(f"#!/bin/sh\ntouch '{sentinel}'\nexit 125\n")
        wrapper.chmod(0o755)
        digest = hashlib.sha256(wrapper.read_bytes()).hexdigest()
        expected = Path(self.tmp.name) / "safe-wrapper.sha256"
        expected.write_text(f"{digest}  safe-wrapper\n")
        result = self.run_audit(
            "validate-wrapper",
            "--path", str(wrapper),
            "--expected-sha-file", str(expected),
        )
        self.assertEqual(result.returncode, 0)
        self.assertFalse(sentinel.exists())

    def test_wrapper_validation_rejects_risky_source_without_executing_it(self):
        sentinel = Path(self.tmp.name) / "must-not-exist"
        wrapper = Path(self.tmp.name) / "risky-wrapper"
        wrapper.write_text(
            f"#!/bin/sh\ntouch '{sentinel}'\npkill -f 'Google Chrome'\nln -s real-profile copy\nexit 125\n"
        )
        wrapper.chmod(0o755)
        digest = hashlib.sha256(wrapper.read_bytes()).hexdigest()
        expected = Path(self.tmp.name) / "risky-wrapper.sha256"
        expected.write_text(f"{digest}  risky-wrapper\n")
        result = self.run_audit(
            "validate-wrapper",
            "--path", str(wrapper),
            "--expected-sha-file", str(expected),
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("forbidden capability", result.stderr)
        self.assertFalse(sentinel.exists())

    def test_wrapper_validation_rejects_hash_or_permission_drift(self):
        wrapper = Path(self.tmp.name) / "safe-wrapper"
        wrapper.write_text("#!/bin/sh\nexit 125\n")
        wrapper.chmod(0o644)
        expected = Path(self.tmp.name) / "safe-wrapper.sha256"
        expected.write_text(f"{'0' * 64}  safe-wrapper\n")
        result = self.run_audit(
            "validate-wrapper",
            "--path", str(wrapper),
            "--expected-sha-file", str(expected),
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertRegex(result.stderr, "hash mismatch|not executable")

    def test_reading_a_browser_wrapper_is_not_mistaken_for_executing_it(self):
        payload = {
            "tool_name": "Bash",
            "tool_input": {
                "command": "sed -n '1,80p' $HOME/.agents/skills/gstack/bin/chrome-cdp"
            },
        }
        result = subprocess.run(
            ["python3", str(GUARD)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_launching_regular_chrome_is_blocked(self):
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "open -a 'Google Chrome'"},
        }
        result = subprocess.run(
            ["python3", str(GUARD)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertIn("permissionDecision", result.stdout)

    def test_security_cli_is_manual_only(self):
        commands = (
            "security lock-keychain ~/Library/Keychains/login.keychain-db",
            "security unlock-keychain ~/Library/Keychains/login.keychain-db",
            "security set-keychain-settings ~/Library/Keychains/login.keychain-db",
            "security find-generic-password -s 'Chrome Safe Storage' -w",
        )
        for command in commands:
            with self.subTest(command=command):
                payload = {"tool_name": "Bash", "tool_input": {"command": command}}
                result = subprocess.run(
                    ["python3", str(GUARD)],
                    input=json.dumps(payload),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                output = json.loads(result.stdout)
                decision = output["hookSpecificOutput"]
                self.assertEqual(decision["permissionDecision"], "deny")
                self.assertIn("Keychain/auth state is manual-only", decision["permissionDecisionReason"])

    def test_agent_configs_do_not_expose_regular_chrome_backends(self):
        settings = json.loads(CLAUDE_SETTINGS.read_text())
        allow = settings.get("permissions", {}).get("allow", [])
        self.assertFalse(any("claude-in-chrome" in item for item in allow))
        codex = CODEX_CONFIG.read_text()
        self.assertNotIn('BROWSER_USE_AVAILABLE_BACKENDS = "chrome,iab"', codex)
        self.assertNotIn("NODE_REPL_INSTRUCTIONS_USE_CASE_CHROME", codex)
        self.assertGreaterEqual(codex.count('BROWSER_USE_AVAILABLE_BACKENDS = "iab"'), 2)

    def test_shell_prefilter_skips_non_browser_bash_without_starting_python(self):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "pwd"}})
        env = self.env.copy()
        env["BROWSER_AUDIT_PYTHON"] = "/nonexistent/browser-audit.py"
        result = subprocess.run(
            [str(HOOK_FILTER), "pre"],
            input=payload,
            capture_output=True,
            text=True,
            env=env,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_shell_prefilter_forwards_browser_candidates_to_audit_gate(self):
        payload = json.dumps({
            "session_id": SID_A,
            "tool_name": "mcp__browser__navigate",
            "tool_input": {"url": "https://example.com"},
        })
        env = self.env.copy()
        env["BROWSER_AUDIT_PYTHON"] = str(SCRIPT)
        result = subprocess.run(
            [str(HOOK_FILTER), "pre"],
            input=payload,
            capture_output=True,
            text=True,
            env=env,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("permissionDecision", result.stdout)


if __name__ == "__main__":
    unittest.main()
