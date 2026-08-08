import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class RoutingAndSpecContractTest(unittest.TestCase):
    def test_shared_root_is_the_only_authored_policy_root(self) -> None:
        shared = read("common/agents/AGENTS.md")
        codex = read("common/codex/AGENTS.md")
        claude = read("common/claude/CLAUDE.md")

        self.assertIn("only authored shared policy root", shared)
        self.assertIn("native import or a generated, drift-checked snapshot", shared)
        self.assertIn("@~/.agents/AGENTS.md", claude)
        self.assertIn("generated, sync-checked shared core", codex)

    def test_specifications_are_event_driven_and_traceable(self) -> None:
        cores = (read("common/agents/AGENTS.md"), read("common/codex/AGENTS.md"))
        guides = (
            read("common/claude/guides/work/intent.md"),
            read("common/codex/guides/work/intent.md"),
        )

        for core in cores:
            self.assertIn("stable W/O/A/X identifiers", core)
            self.assertIn("Development specification is conditional", core)
            self.assertIn("development-spec N/A", core)
        for guide in guides:
            self.assertIn("## Event-driven specification gate", guide)
            self.assertIn("W1", guide)
            self.assertIn("D1 [W1]", guide)
            self.assertIn("V1 [A1]", guide)
            self.assertIn(
                "| non-trivial read-only analysis or design | required once | N/A | required once |",
                guide,
            )
            self.assertIn("Do not regenerate either specification during execution", guide)
        self.assertEqual(guides[0], guides[1])

    def test_session_core_keeps_one_compact_closed_snapshot(self) -> None:
        skills = (
            read("common/claude/skills/clx-session-intent/SKILL.md"),
            read("common/codex/skills/clx-session-intent/SKILL.md"),
        )
        for skill in skills:
            self.assertIn("# Session Core", skill)
            self.assertIn("State: <pending|executing|blocked|closed>", skill)
            self.assertIn("Token: <measured input/output/total|unavailable>", skill)
            self.assertIn("## 작업명세서 [ACTIVE|CLOSED]", skill)
            self.assertIn("## 개발명세서 [N/A|PENDING|APPROVED|CLOSED]", skill)
            self.assertIn("## 보고명세서 [PENDING|FINAL]", skill)
            self.assertIn("retain the compact `closed` snapshot until the next task", skill)
            self.assertNotIn("Never store either specification body", skill)
        self.assertEqual(skills[0], skills[1])

    def test_design_routes_one_specialist_only_when_substantial(self) -> None:
        cores = (read("common/agents/AGENTS.md"), read("common/codex/AGENTS.md"))
        guides = (
            read("common/claude/guides/work/subagents.md"),
            read("common/codex/guides/work/subagents.md"),
        )
        workflows = (
            read("common/claude/rules/design/design-workflow.md"),
            read("common/codex/rules/design/design-workflow.md"),
        )
        for text in (*cores, *guides, *workflows):
            self.assertIn("one scoped design specialist", text)
            self.assertNotIn("1–7 scoped", text)
            self.assertNotIn("Every design task uses", text)
        self.assertEqual(workflows[0], workflows[1])

    def test_grok_has_an_explicit_shared_root_adapter(self) -> None:
        config = read("common/grok/config.toml")
        agent = read("common/grok/agents/clx-delegate.md")
        runtime = read("common/claude/hooks/clx-grok-runtime.py")

        self.assertIn('[agent]\ndefinition = "__CLX_HOME__/.grok/agents/clx-delegate.md"', config)
        self.assertIn("Read `~/.agents/AGENTS.md` before acting", agent)
        self.assertIn("sole shared policy root", agent)
        self.assertIn("SHARED_ROOT", runtime)
        self.assertIn('runtime_agents_root / "AGENTS.md"', runtime)
        self.assertIn("shared_root_digest", runtime)

    def test_final_report_handles_skipped_development_spec(self) -> None:
        skills = (
            read("common/claude/skills/clx-concise-report/SKILL.md"),
            read("common/codex/skills/clx-concise-report/SKILL.md"),
        )
        for skill in skills:
            self.assertIn("development-spec N/A", skill)
            self.assertIn("W1 PASS", skill)
            self.assertIn("A1 PASS", skill)
        self.assertEqual(skills[0], skills[1])


if __name__ == "__main__":
    unittest.main()
