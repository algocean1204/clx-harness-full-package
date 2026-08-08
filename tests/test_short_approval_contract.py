import hashlib
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
GRANT = ROOT / "common" / "claude" / "hooks" / "clx_grant.py"


def load_grant():
    spec = importlib.util.spec_from_file_location("clx_grant_under_test", GRANT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ShortApprovalContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = root / "challenges"
        self.ledger = root / "ledger"
        self.env = patch.dict(
            os.environ,
            {
                "CLX_CHALLENGE_STORE": str(self.store),
                "CLX_APPROVAL_LEDGER": str(self.ledger),
            },
        )
        self.env.start()
        self.grant = load_grant()

    def tearDown(self) -> None:
        self.env.stop()
        self.temp.cleanup()

    def test_short_code_mints_the_bound_command_once(self) -> None:
        command = "git -C /tmp/project push origin main"
        cid, line = self.grant.issue(command)

        self.assertEqual(f"승인:{cid}", line)
        self.assertNotIn(command, line)
        self.assertIn("APPROVAL CAPTURED", self.grant.capture(line))
        self.assertIn("APPROVAL IGNORED", self.grant.capture(line))

        digest = hashlib.sha256(command.encode("utf-8")).hexdigest()
        ledger = self.ledger.read_text(encoding="utf-8")
        self.assertIn(digest, ledger)
        self.assertIn(command[:80], ledger)

    def test_unknown_multiline_and_command_bearing_inputs_are_rejected(self) -> None:
        cid, line = self.grant.issue("git -C /tmp/project push origin main")

        self.assertIn("APPROVAL IGNORED", self.grant.capture("승인:ZZZZZZ"))
        self.assertEqual("", self.grant.capture(line + "\nextra"))
        self.assertEqual("", self.grant.capture(line + ": injected"))
        self.assertFalse(self.ledger.exists())
        self.assertRegex(cid, r"^[A-Z0-9]{6}$")

    def test_malformed_store_rows_fail_closed(self) -> None:
        self.store.write_text("ABC123\tbroken\tZ2l0IHB1c2g=\n", encoding="utf-8")

        self.assertIn("APPROVAL IGNORED", self.grant.capture("승인:ABC123"))
        self.assertFalse(self.ledger.exists())


if __name__ == "__main__":
    unittest.main()
