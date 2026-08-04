import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GrokInstallTest(unittest.TestCase):
    def install(self, home: Path) -> None:
        python_dir = str(Path(shutil.which("python3") or "/usr/bin/python3").parent)
        env = {**os.environ, "HOME": str(home), "PATH": os.pathsep.join((python_dir, "/usr/bin", "/bin"))}
        subprocess.run(
            ["bash", str(ROOT / "install.sh"), "--apply"],
            check=True,
            env=env,
            capture_output=True,
            text=True,
        )

    def test_fresh_install_sets_grok_sandbox_off(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.install(home)

            config = (home / ".grok" / "config.toml").read_text(encoding="utf-8")
            self.assertIn('[sandbox]\nprofile = "off"', config)

    def test_fresh_install_carries_codex_session_intent_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.install(home)

            installed = home / ".codex" / "skills" / "clx-session-intent" / "SKILL.md"
            source = ROOT / "common" / "codex" / "skills" / "clx-session-intent" / "SKILL.md"
            self.assertEqual(source.read_bytes(), installed.read_bytes())

    def test_existing_grok_config_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            grok = home / ".grok"
            grok.mkdir()
            original = '[models]\ndefault = "custom"\n\n[sandbox]\nprofile = "strict"\n'
            (grok / "config.toml").write_text(original, encoding="utf-8")

            self.install(home)

            config = (grok / "config.toml").read_text(encoding="utf-8")
            self.assertIn('default = "custom"', config)
            self.assertIn('profile = "off"', config)
            self.assertNotIn('profile = "strict"', config)
            backups = list(grok.glob("config.toml.pre-clx-*"))
            self.assertEqual(1, len(backups))
            self.assertEqual(original, backups[0].read_text(encoding="utf-8"))

    def test_windows_installer_carries_the_same_grok_contract(self) -> None:
        installer = (ROOT / "windows-harness" / "install.ps1").read_text(encoding="utf-8")

        self.assertIn("@{ Src = 'grok';   Dst = (Join-Path $profileDir '.grok')", installer)
        self.assertIn("function Merge-GrokConfig", installer)
        self.assertIn("Merge-GrokConfig $liveGrokConfig $prevGrokConfig", installer)


if __name__ == "__main__":
    unittest.main()
