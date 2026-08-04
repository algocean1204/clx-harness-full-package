import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLAUDE = ROOT / "common" / "claude"
CODEX = ROOT / "common" / "codex"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TwoStageApprovalPolicyTest(unittest.TestCase):
    def test_core_requires_work_then_development_approval(self) -> None:
        cores = (
            read(ROOT / "common" / "agents" / "AGENTS.md"),
            read(CODEX / "AGENTS.md"),
        )

        for core in cores:
            rule = next(line for line in core.splitlines() if line.startswith("11. "))
            self.assertIn("two-stage approval gate", rule)
            self.assertLess(rule.index("work specification"), rule.index("development specification"))
            self.assertIn("No mutation or implementation command before development-spec approval", rule)
            self.assertIn("material scope, authority, or risk", rule)
            self.assertIn("never become a second ask", rule)
            self.assertIn("is a violation, not a courtesy", rule)
            self.assertIn("Name them only `작업명세서` and `개발명세서`", rule)
            self.assertNotRegex(rule, r"(?:work|dev(?:elopment)?)-spec\s+v\w+")

    def test_intent_guide_defines_the_state_machine_and_packets(self) -> None:
        for path in (CLAUDE / "guides/work/intent.md", CODEX / "guides/work/intent.md"):
            guide = read(path)
            for token in (
                "## Two-stage approval gate",
                "WORK_SPEC_PENDING",
                "DEV_SPEC_PENDING",
                "EXECUTING",
                "Current-state evidence",
                "Existing execution flow",
                "File-by-file changes",
                "Rollback and deployment",
                "Approval: work-spec approved; development-spec pending",
                "Both specifications are chat responses, not files",
                "승인 대기 — 작업명세서",
                "승인 대기 — 개발명세서",
            ):
                self.assertIn(token, guide, f"{path}: missing {token}")

    def test_git_policy_binds_grants_to_the_approved_development_spec(self) -> None:
        for path in (CLAUDE / "guides/work/git.md", CODEX / "guides/work/git.md"):
            guide = read(path)
            self.assertIn("approved development specification", guide)
            self.assertIn("one guarded command", guide)
            self.assertIn("command-specific grants", guide)
            self.assertIn("trusted Codex transcript fallback", guide)

    def test_prompt_injection_uses_the_two_stage_gate(self) -> None:
        hook = read(CLAUDE / "hooks/intent-lock.py")

        self.assertIn("TWO-STAGE APPROVAL GATE", hook)
        self.assertIn("work specification", hook)
        self.assertIn("development specification", hook)
        self.assertNotIn("DESIGN GATE (core rule 11)", hook)

    def test_session_intent_stores_only_the_stage_state(self) -> None:
        skill = read(CLAUDE / "skills/clx-session-intent/SKILL.md")

        self.assertIn("Approval: work-spec approved; development-spec pending", skill)
        self.assertIn("Never store either specification body", skill)
        self.assertNotRegex(skill, r"(?:work|dev(?:elopment)?)-spec\s+v\w+")

    def test_codex_session_intent_skill_matches_claude(self) -> None:
        self.assertEqual(
            read(CLAUDE / "skills/clx-session-intent/SKILL.md"),
            read(CODEX / "skills/clx-session-intent/SKILL.md"),
        )

    def test_approval_wait_footers_are_sanctioned_stops(self) -> None:
        hooks = str(CLAUDE / "hooks")
        sys.path.insert(0, hooks)
        try:
            spec = importlib.util.spec_from_file_location(
                "selfcheck_stop", CLAUDE / "hooks/selfcheck-stop.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(hooks)

        self.assertFalse(module.is_handoff("승인 대기 — 작업명세서"))
        self.assertFalse(module.is_handoff("승인 대기 — 개발명세서"))
        self.assertTrue(module.is_handoff("다음 작업은 구현입니다"))

    def test_obsolete_approval_comments_are_removed(self) -> None:
        guard = read(CLAUDE / "hooks/guard-destructive.py")
        intent_lock = read(CLAUDE / "hooks/intent-lock.py")

        self.assertNotIn("may be user-run via `!`", guard)
        self.assertNotIn("only the UserPromptSubmit hook mints", guard)
        self.assertNotIn("This hook is the ONLY place a real owner prompt is visible", intent_lock)

    def test_agent_facing_text_uses_the_two_stage_gate_name(self) -> None:
        for path in (
            CLAUDE / "CLAUDE.md",
            CLAUDE / "hooks/selfcheck-stop.py",
            CLAUDE / "hooks/auto-format.sh",
        ):
            text = read(path)
            self.assertNotIn("design gate", text.lower(), str(path))
            self.assertIn("two-stage approval gate", text.lower(), str(path))

    def test_readme_explains_both_approval_stages(self) -> None:
        readme = read(ROOT / "README.md")

        self.assertIn("작업명세서 승인", readme)
        self.assertIn("개발명세서 승인", readme)
        self.assertLess(readme.index("작업명세서 승인"), readme.index("개발명세서 승인"))
        self.assertIn("명세 이름에 번호나 버전 표기를 붙이지 않습니다", readme)

    def test_core_defines_the_approved_task_completion_contract(self) -> None:
        cores = (
            read(ROOT / "common" / "agents" / "AGENTS.md"),
            read(CODEX / "AGENTS.md"),
        )

        for core in cores:
            rule = next(line for line in core.splitlines() if line.startswith("8. "))
            for token in (
                "final chat report is its exit contract",
                "work-spec N/N",
                "development-spec N/N",
                "DoD N/N",
                "apply, deploy, and backup",
                "unresolved REQUIRED",
            ):
                self.assertIn(token, rule)

    def test_intent_guide_defines_the_completion_exit_contract(self) -> None:
        for path in (CLAUDE / "guides/work/intent.md", CODEX / "guides/work/intent.md"):
            guide = read(path)
            for token in (
                "## Completion report exit contract",
                "`EXECUTING` exits only",
                "work-spec N/N",
                "development-spec N/N",
                "DoD N/N",
                "chat response, never a file",
                "Clear the Approval line only after",
            ):
                self.assertIn(token, guide, f"{path}: missing {token}")

    def test_report_skills_are_identical(self) -> None:
        self.assertEqual(
            read(CLAUDE / "skills/clx-concise-report/SKILL.md"),
            read(CODEX / "skills/clx-concise-report/SKILL.md"),
        )

    def test_report_skill_defines_the_approved_task_template(self) -> None:
        skill = read(CLAUDE / "skills/clx-concise-report/SKILL.md")

        for token in (
            "## Approved-task completion",
            "work-spec N/N",
            "development-spec N/N",
            "DoD N/N",
            "apply, deploy, and backup",
            "blocker report",
            "`미검증:`",
        ):
            self.assertIn(token, skill)

    def test_session_intent_clears_approval_after_the_completion_report(self) -> None:
        skill = read(CLAUDE / "skills/clx-session-intent/SKILL.md")
        state_contract = "For a task using the two-stage approval gate"

        self.assertEqual(skill.count(state_contract), 1)
        self.assertIn("clear it only after the completion report is sent", skill)

    def test_readme_explains_the_chat_only_completion_report(self) -> None:
        readme = read(ROOT / "README.md")

        self.assertIn("채팅 완료 보고", readme)
        self.assertIn("작업명세 N/N", readme)
        self.assertIn("개발명세 N/N", readme)
        self.assertIn("별도 완료 보고서 파일을 만들지 않습니다", readme)

    def test_public_backup_payload_excludes_owner_infrastructure(self) -> None:
        backup = read(CODEX / "hooks/backup-config.sh")

        for private_name in (
            "codex-xai-bridge",
            "codex-hermes-connector",
            "codex-hermes-desktop-proxy",
            "hermes-xai-proxy",
            "com.finauto",
            "LaunchAgents",
        ):
            self.assertNotIn(private_name, backup)


if __name__ == "__main__":
    unittest.main()
