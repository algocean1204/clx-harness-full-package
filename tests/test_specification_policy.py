import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLAUDE = ROOT / "common" / "claude"
CODEX = ROOT / "common" / "codex"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class SpecificationPolicyTest(unittest.TestCase):
    def test_core_defines_conditional_event_driven_specs(self) -> None:
        cores = (read(ROOT / "common/agents/AGENTS.md"), read(CODEX / "AGENTS.md"))
        for core in cores:
            rule = next(line for line in core.splitlines() if line.startswith("11. "))
            self.assertIn("stable W/O/A/X identifiers", rule)
            self.assertIn("Development specification is conditional", rule)
            self.assertIn("using D/V identifiers mapped to W/A", rule)
            self.assertIn("development-spec N/A", rule)
            self.assertIn("Do not regenerate either specification during execution", rule)
            self.assertIn("never become a second ask", core)
            self.assertIn("is a violation, not a courtesy", core)
            self.assertNotIn("two-stage approval gate", rule)
            self.assertNotRegex(rule, r"(?:work|dev(?:elopment)?)-spec\s+v\w+")

    def test_intent_guides_match_and_define_the_routing_matrix(self) -> None:
        guides = (
            read(CLAUDE / "guides/work/intent.md"),
            read(CODEX / "guides/work/intent.md"),
        )
        self.assertEqual(guides[0], guides[1])
        for token in (
            "## Event-driven specification gate",
            "non-trivial read-only analysis or design",
            "| non-trivial read-only analysis or design | required once | N/A | required once |",
            "D1 [W1]",
            "V1 [A1]",
            "승인 대기 — 작업명세서",
            "승인 대기 — 개발명세서",
            "retain the compact `closed` snapshot",
        ):
            self.assertIn(token, guides[0])

    def test_git_policy_keeps_command_grants_separate(self) -> None:
        for path in (CLAUDE / "guides/work/git.md", CODEX / "guides/work/git.md"):
            guide = read(path)
            self.assertIn("approved development specification", guide)
            self.assertIn("command-specific grants", guide)
            self.assertIn("trusted Codex transcript fallback", guide)

    def test_approval_wait_footers_remain_sanctioned_stops(self) -> None:
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

    def test_session_and_report_skills_match_between_surfaces(self) -> None:
        self.assertEqual(
            read(CLAUDE / "skills/clx-session-intent/SKILL.md"),
            read(CODEX / "skills/clx-session-intent/SKILL.md"),
        )
        self.assertEqual(
            read(CLAUDE / "skills/clx-concise-report/SKILL.md"),
            read(CODEX / "skills/clx-concise-report/SKILL.md"),
        )

    def test_completion_report_closes_ids_once(self) -> None:
        skill = read(CLAUDE / "skills/clx-concise-report/SKILL.md")
        for token in (
            "one final chat report",
            "development-spec N/A",
            "W1 PASS",
            "A1 PASS",
            "apply, deploy, or backup",
            "blocker report",
            "`미검증:`",
        ):
            self.assertIn(token, skill)

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

    def test_project_local_filesystem_crud_is_direct_but_bounded(self) -> None:
        cores = (read(ROOT / "common/agents/AGENTS.md"), read(CODEX / "AGENTS.md"))
        guides = (
            read(CLAUDE / "guides/work/intent.md"),
            read(CODEX / "guides/work/intent.md"),
        )
        for core in cores:
            self.assertIn("ordinary filesystem CRUD strictly below the current project root", core)
            self.assertIn("without another conversational approval", core)
        for guide in guides:
            self.assertIn("Create, read, update, move, rename, and delete", guide)
            self.assertIn("Resolve symlinks before applying the boundary", guide)
            for exclusion in ("The root itself", ".git", "secrets/auth", "remote services"):
                self.assertIn(exclusion, guide)
        readme = read(ROOT / "README.md")
        self.assertIn("프로젝트 내부 파일 CRUD", readme)
        settings = read(CLAUDE / "settings.json")
        guard = read(CLAUDE / "hooks/guard-destructive.py")
        self.assertIn('"Read(**/.env)"', settings)
        self.assertIn("git reset --hard (destroys uncommitted work)", guard)


if __name__ == "__main__":
    unittest.main()
