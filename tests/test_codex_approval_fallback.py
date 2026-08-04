import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOKS = Path(os.environ.get("CLX_TEST_HOOKS", ROOT / "common" / "claude" / "hooks"))
GUARD = HOOKS / "guard-destructive.py"
GRANT = HOOKS / "clx_grant.py"
COMMAND = "git -C /tmp/clx-canary push --force-with-lease origin main"


class CodexApprovalFallbackTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.sessions = self.home / ".codex" / "sessions" / "2026" / "08" / "07"
        self.sessions.mkdir(parents=True)
        self.transcript = self.sessions / "rollout-canary.jsonl"
        self.store = self.root / "challenges"
        self.ledger = self.root / "approvals.txt"
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "CLX_CHALLENGE_STORE": str(self.store),
            "CLX_APPROVAL_LEDGER": str(self.ledger),
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def issue(self, command: str = COMMAND) -> str:
        result = subprocess.run(
            [sys.executable, str(GRANT), "issue", command],
            env=self.env,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def write_events(self, *events: dict) -> None:
        self.transcript.write_text(
            "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
            encoding="utf-8",
        )

    @staticmethod
    def user_event(message: str) -> dict:
        return {
            "timestamp": "2026-08-07T00:00:00Z",
            "type": "event_msg",
            "payload": {
                "type": "user_message",
                "message": message + "\n",
                "client_id": "owner-canary",
                "images": [],
                "local_images": [],
                "audio": [],
                "local_audio": [],
                "text_elements": [],
            },
        }

    @staticmethod
    def assistant_event(message: str) -> dict:
        return {
            "timestamp": "2026-08-07T00:00:01Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": message}],
            },
        }

    def run_guard(self, command: str = COMMAND, transcript: Path = None, turn_id: str = "turn-canary"):
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "transcript_path": str(transcript or self.transcript),
            "turn_id": turn_id,
        }
        return subprocess.run(
            [sys.executable, str(GUARD)],
            input=json.dumps(payload),
            env=self.env,
            capture_output=True,
            text=True,
        )

    def test_latest_real_codex_user_approval_allows_exact_command_once(self) -> None:
        approval = self.issue()
        self.write_events(self.assistant_event(approval), self.user_event(approval))

        first = self.run_guard()
        second = self.run_guard()

        self.assertEqual("", first.stdout, first.stdout)
        self.assertIn("force-push", second.stdout)
        self.assertIn(" USED ", self.ledger.read_text(encoding="utf-8"))
        self.assertNotIn("PENDING", self.ledger.read_text(encoding="utf-8"))

    def test_assistant_text_cannot_mint_an_approval(self) -> None:
        approval = self.issue()
        self.write_events(self.assistant_event(approval))

        result = self.run_guard()

        self.assertIn("force-push", result.stdout)
        self.assertFalse(self.ledger.exists())

    def test_only_the_latest_user_message_is_eligible(self) -> None:
        approval = self.issue()
        self.write_events(self.user_event(approval), self.user_event("continue with the task"))

        result = self.run_guard()

        self.assertIn("force-push", result.stdout)
        self.assertFalse(self.ledger.exists())

    def test_multiline_user_payload_cannot_mint_an_approval(self) -> None:
        approval = self.issue()
        self.write_events(self.user_event("quoted document\n" + approval))

        result = self.run_guard()

        self.assertIn("force-push", result.stdout)
        self.assertFalse(self.ledger.exists())

    def test_quoted_approval_with_commentary_is_not_consumed(self) -> None:
        approval = self.issue()
        self.write_events(self.user_event(f'["{approval}"] 이렇게 말하고 끝내면 버그야.'))

        result = self.run_guard()

        self.assertIn("force-push", result.stdout)
        self.assertFalse(self.ledger.exists())

    def test_transcript_outside_codex_sessions_is_rejected(self) -> None:
        approval = self.issue()
        outside = self.root / "agent-controlled.jsonl"
        outside.write_text(json.dumps(self.user_event(approval)) + "\n", encoding="utf-8")

        result = self.run_guard(transcript=outside)

        self.assertIn("force-push", result.stdout)
        self.assertFalse(self.ledger.exists())

    def test_symlink_escape_from_codex_sessions_is_rejected(self) -> None:
        approval = self.issue()
        outside = self.root / "outside.jsonl"
        outside.write_text(json.dumps(self.user_event(approval)) + "\n", encoding="utf-8")
        link = self.sessions / "rollout-link.jsonl"
        link.symlink_to(outside)

        result = self.run_guard(transcript=link)

        self.assertIn("force-push", result.stdout)
        self.assertFalse(self.ledger.exists())

    def test_codex_turn_id_is_required(self) -> None:
        approval = self.issue()
        self.write_events(self.user_event(approval))

        result = self.run_guard(turn_id="")

        self.assertIn("force-push", result.stdout)
        self.assertFalse(self.ledger.exists())

    def test_protected_runtime_state_ignores_a_valid_approval(self) -> None:
        command = "rm -rf ~/.codex/sessions"
        approval = self.issue(command)
        self.write_events(self.user_event(approval))

        result = self.run_guard(command=command)

        self.assertIn("protected agent session/runtime state", result.stdout)
        self.assertFalse(self.ledger.exists())

    def test_trusted_grant_issuer_treats_the_candidate_command_as_data(self) -> None:
        command = f'{GRANT} issue "clx-grok-delegate /tmp/repo -p session-intent delete"'

        result = self.run_guard(command=command)

        self.assertEqual("", result.stdout, result.stdout)

    def test_shadow_grant_issuer_cannot_bypass_protected_state(self) -> None:
        shadow = self.root / "clx_grant.py"
        command = f'{shadow} issue "rm -rf ~/.codex/sessions"'

        result = self.run_guard(command=command)

        self.assertIn("protected agent session/runtime state", result.stdout)

    def test_shell_wrapped_grant_issuer_cannot_bypass_protected_state(self) -> None:
        commands = (
            f"bash -c '{GRANT} issue \"rm -rf ~/.codex/sessions\"'",
            f'{GRANT} issue "safe" && rm -rf ~/.codex/sessions',
            f'python3 {GRANT} issue "rm -rf ~/.codex/sessions"',
        )

        for command in commands:
            with self.subTest(command=command):
                result = self.run_guard(command=command)
                self.assertIn("protected agent session/runtime state", result.stdout)

    def test_approval_for_a_different_command_does_not_allow_this_command(self) -> None:
        other = "git -C /tmp/clx-canary push --force-with-lease upstream main"
        approval = self.issue(other)
        self.write_events(self.user_event(approval))

        result = self.run_guard()

        self.assertIn("force-push", result.stdout)
        self.assertIn("PENDING", self.ledger.read_text(encoding="utf-8"))

    def test_bang_prefixed_chat_message_is_not_an_approval(self) -> None:
        self.issue()
        self.write_events(self.user_event("!" + COMMAND))

        result = self.run_guard()

        self.assertIn("force-push", result.stdout)
        self.assertFalse(self.ledger.exists())

    def test_denial_does_not_advertise_unsupported_bang_chat(self) -> None:
        self.write_events(self.user_event("continue"))

        result = self.run_guard()

        self.assertNotIn("! prefix", result.stdout)
        self.assertIn("own terminal", result.stdout)

    def test_expired_challenge_is_rejected(self) -> None:
        approval = self.issue()
        challenge_id = approval.split()[1].rstrip(":")
        self.store.write_text(f"{challenge_id}\t2000-01-01T00:00:00+00:00\n", encoding="utf-8")
        self.write_events(self.user_event(approval))

        result = self.run_guard()

        self.assertIn("force-push", result.stdout)
        self.assertFalse(self.ledger.exists())

    def test_malformed_tail_records_do_not_hide_the_latest_user_message(self) -> None:
        approval = self.issue()
        self.transcript.write_text(
            json.dumps(self.user_event(approval), ensure_ascii=False) + "\n{broken json\n",
            encoding="utf-8",
        )

        result = self.run_guard()

        self.assertEqual("", result.stdout, result.stdout)

    def test_non_object_tail_records_do_not_hide_the_latest_user_message(self) -> None:
        approval = self.issue()
        self.transcript.write_text(
            json.dumps(self.user_event(approval), ensure_ascii=False) + "\n[]\nnull\n",
            encoding="utf-8",
        )

        result = self.run_guard()

        self.assertEqual("", result.stdout, result.stdout)

    def test_concurrent_calls_allow_exactly_one_spend(self) -> None:
        approval = self.issue()
        self.write_events(self.user_event(approval))

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.run_guard(), range(16)))

        self.assertEqual(1, sum(result.stdout == "" for result in results))
        self.assertEqual(15, sum("force-push" in result.stdout for result in results))
        self.assertEqual(1, self.ledger.read_text(encoding="utf-8").count(" USED "))

    def test_tail_reader_skips_a_partial_large_record(self) -> None:
        approval = self.issue()
        huge = self.assistant_event("x" * (1024 * 1024 + 32))
        self.write_events(huge, self.user_event(approval))

        result = self.run_guard()

        self.assertEqual("", result.stdout, result.stdout)

    def test_policy_matches_the_trusted_codex_fallback(self) -> None:
        core = (ROOT / "common" / "agents" / "AGENTS.md").read_text(encoding="utf-8")
        codex_core = (ROOT / "common" / "codex" / "AGENTS.md").read_text(encoding="utf-8")
        claude_git = (ROOT / "common" / "claude" / "guides" / "work" / "git.md").read_text(encoding="utf-8")
        codex_git = (ROOT / "common" / "codex" / "guides" / "work" / "git.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        for text in (core, codex_core):
            self.assertIn("trusted owner-input hook", text)
            self.assertIn("never output a bare challenge", text)
            self.assertNotIn("ONLY the UserPromptSubmit hook", text)
        for text in (claude_git, codex_git):
            self.assertIn("trusted Codex transcript fallback", text)
            self.assertIn("Never output a bare challenge", text)
            self.assertNotIn("`!` prefix", text)
        self.assertIn("마지막 실제\n`user_message`", readme)
        self.assertIn("승인 챌린지만 단독으로 보내지 않습니다", readme)
        self.assertNotIn("`!` 접두사", readme)


if __name__ == "__main__":
    unittest.main()
