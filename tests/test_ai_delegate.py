import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from typing import Dict, Optional


ROOT = Path(__file__).resolve().parents[1]
DELEGATE = ROOT / "common" / "local-bin" / "clx-ai-delegate"


class AiDelegateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.bin = self.root / "bin"
        self.repo = self.root / "repo"
        self.home.mkdir()
        self.bin.mkdir()
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        agents = self.home / ".agents"
        agents.mkdir()
        (agents / "models.toml").write_text(
            textwrap.dedent(
                """
                [roles.gpt_exec]  # Codex target
                model = "codex-test"
                effort = "high"

                [roles.claude_exec]  # Claude target
                model = "claude-test"
                effort = "max"
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        self.log = self.root / "call.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def fake_cli(self, name: str, body: str) -> None:
        path = self.bin / name
        path.write_text("#!/usr/bin/env python3\n" + textwrap.dedent(body), encoding="utf-8")
        path.chmod(0o755)

    def env(self) -> Dict[str, str]:
        return {
            **os.environ,
            "HOME": str(self.home),
            "PATH": os.pathsep.join((str(self.bin), str(Path(sys.executable).parent), "/usr/bin", "/bin")),
            "CLX_TEST_LOG": str(self.log),
        }

    def run_delegate(self, provider: str, *, env: Optional[Dict[str, str]] = None):
        return subprocess.run(
            [sys.executable, str(DELEGATE), provider, str(self.repo), "-p", "Implement the bounded task."],
            env=env or self.env(),
            capture_output=True,
            text=True,
        )

    def test_codex_uses_workspace_write_ephemeral_registry_role(self) -> None:
        self.fake_cli(
            "codex",
            """
            import json, os, sys
            from pathlib import Path
            args = sys.argv[1:]
            Path(os.environ["CLX_TEST_LOG"]).write_text(json.dumps({"args": args, "cwd": os.getcwd(), "active": os.environ.get("CLX_EXTERNAL_EXECUTOR")}))
            Path(args[args.index("-o") + 1]).write_text("CODEX_OK")
            """,
        )

        result = self.run_delegate("codex")

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("CODEX_OK", result.stdout.strip())
        call = json.loads(self.log.read_text())
        self.assertEqual(str(self.repo.resolve()), call["cwd"])
        self.assertEqual("codex", call["active"])
        for value in ("exec", "--ephemeral", "--sandbox", "workspace-write", "-C", str(self.repo.resolve()), "-m", "codex-test"):
            self.assertIn(value, call["args"])
        self.assertIn('model_reasoning_effort="high"', call["args"])
        self.assertIn('approval_policy="never"', call["args"])

    def test_claude_uses_nonpersistent_sandboxed_registry_role(self) -> None:
        self.fake_cli(
            "claude",
            """
            import json, os, sys
            from pathlib import Path
            args = sys.argv[1:]
            settings = json.loads(Path(args[args.index("--settings") + 1]).read_text())
            Path(os.environ["CLX_TEST_LOG"]).write_text(json.dumps({"args": args, "cwd": os.getcwd(), "active": os.environ.get("CLX_EXTERNAL_EXECUTOR"), "settings": settings}))
            print(json.dumps({"result": "CLAUDE_OK", "is_error": False}))
            """,
        )

        result = self.run_delegate("claude")

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("CLAUDE_OK", result.stdout.strip())
        call = json.loads(self.log.read_text())
        self.assertEqual(str(self.repo.resolve()), call["cwd"])
        self.assertEqual("claude", call["active"])
        for value in ("-p", "--no-session-persistence", "--no-chrome", "--strict-mcp-config", "--permission-mode", "acceptEdits", "--model", "claude-test", "--effort", "max"):
            self.assertIn(value, call["args"])
        settings_path = Path(call["args"][call["args"].index("--settings") + 1])
        self.assertFalse(settings_path.exists())
        if os.name == "nt":
            self.assertNotIn("sandbox", call["settings"])
            self.assertNotIn("Bash", call["args"][call["args"].index("--tools") + 1])
        else:
            self.assertEqual(
                {"enabled": True, "autoAllowBashIfSandboxed": True, "excludedCommands": [], "allowUnsandboxedCommands": False},
                call["settings"]["sandbox"],
            )

    def test_nested_external_executor_is_rejected_before_launch(self) -> None:
        self.fake_cli("codex", "raise SystemExit('must not launch')\n")
        env = self.env()
        env["CLX_EXTERNAL_EXECUTOR"] = "claude"

        result = self.run_delegate("codex", env=env)

        self.assertEqual(126, result.returncode)
        self.assertIn("recursive external delegation", result.stderr)
        self.assertFalse(self.log.exists())

    def test_non_git_directory_is_rejected(self) -> None:
        plain = self.root / "plain"
        plain.mkdir()
        result = subprocess.run(
            [sys.executable, str(DELEGATE), "codex", str(plain), "-p", "x"],
            env=self.env(),
            capture_output=True,
            text=True,
        )

        self.assertEqual(126, result.returncode)
        self.assertIn("Git repository", result.stderr)

    def test_same_repository_rejects_a_second_executor(self) -> None:
        started = self.root / "started"
        self.fake_cli(
            "codex",
            """
            import os, sys, time
            from pathlib import Path
            args = sys.argv[1:]
            started = Path(os.environ["CLX_TEST_STARTED"])
            if not started.exists():
                started.write_text("first")
                time.sleep(2)
            Path(args[args.index("-o") + 1]).write_text("DONE")
            """,
        )
        env = self.env()
        env["CLX_TEST_STARTED"] = str(started)
        first = subprocess.Popen(
            [sys.executable, str(DELEGATE), "codex", str(self.repo), "-p", "first"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            for _ in range(100):
                if started.exists():
                    break
                time.sleep(0.02)
            self.assertTrue(started.exists())
            second = subprocess.run(
                [sys.executable, str(DELEGATE), "codex", str(self.repo), "-p", "second"],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(126, second.returncode)
            self.assertIn("another external executor", second.stderr)
        finally:
            first.communicate(timeout=5)

    def test_installers_ship_the_delegate(self) -> None:
        install_home = self.root / "install-home"
        install_home.mkdir()
        python_dir = str(Path(shutil.which("python3") or sys.executable).parent)
        env = {**os.environ, "HOME": str(install_home), "PATH": os.pathsep.join((python_dir, "/usr/bin", "/bin"))}
        subprocess.run(["bash", str(ROOT / "install.sh"), "--apply"], check=True, env=env, capture_output=True, text=True)

        installed = install_home / ".local" / "bin" / "clx-ai-delegate"
        self.assertTrue(installed.is_file())
        self.assertTrue(os.access(installed, os.X_OK))
        windows = (ROOT / "windows-harness" / "install.ps1").read_text(encoding="utf-8")
        self.assertIn("Src = 'local-bin'", windows)
        self.assertIn("'.local\\bin'", windows)

    def test_cross_executor_routes_are_shipped_without_bypass_flags(self) -> None:
        core = (ROOT / "common" / "agents" / "AGENTS.md").read_text(encoding="utf-8")
        models = (ROOT / "common" / "agents" / "models.toml").read_text(encoding="utf-8")
        guide = (ROOT / "common" / "claude" / "guides" / "work" / "models.md").read_text(encoding="utf-8")
        gpt = (ROOT / "common" / "claude" / "commands" / "gpt.md").read_text(encoding="utf-8")
        claude_path = ROOT / "common" / "codex" / "prompts" / "claude.md"
        self.assertTrue(claude_path.is_file())
        claude = claude_path.read_text(encoding="utf-8")
        delegate = DELEGATE.read_text(encoding="utf-8")

        self.assertIn("explicit user request to assign an installed external executor", core)
        self.assertIn("[roles.claude_exec]", models)
        self.assertIn("`/claude`", guide)
        self.assertIn("clx-ai-delegate codex", gpt)
        self.assertIn("clx-ai-delegate claude", claude)
        self.assertNotIn("dangerously-bypass", delegate)
        self.assertNotIn("dangerously-skip-permissions", delegate)
        ui = (ROOT / "setup-ui" / "index.html").read_text(encoding="utf-8")
        self.assertIn('claude_exec: "claude"', ui)
        self.assertIn('"no-claude": "reasonNoClaude"', ui)
        detector = (ROOT / "common" / "claude" / "hooks" / "model-registry-check.py").read_text(encoding="utf-8")
        self.assertIn('name == "claude_exec" and not shutil.which("claude")', detector)


if __name__ == "__main__":
    unittest.main()
