"""Tests for skill trigger matching and repo-level knowledge packs."""

from __future__ import annotations

from app.skills.registry import SkillCategory, SkillInfo, SkillRegistry
from app.skills.repo_knowledge import load_repo_skills, parse_skill_markdown


class TestTriggerMatching:
    def _registry(self) -> SkillRegistry:
        reg = SkillRegistry()
        reg.register(SkillInfo(
            id="deploy", name="Deploy", description="deploy helper",
            category=SkillCategory.ENGINEERING,
            system_prompt="Deploy carefully.",
            triggers=["deploy", "发布"],
        ))
        reg.register(SkillInfo(
            id="py-style", name="Python Style", description="py conventions",
            category=SkillCategory.ENGINEERING,
            system_prompt="Follow PEP8.",
            path_triggers=["**/*.py"],
        ))
        reg.register(SkillInfo(
            id="plain", name="Plain", description="no triggers",
            category=SkillCategory.CORE,
        ))
        return reg

    def test_keyword_trigger_matches_case_insensitive(self):
        reg = self._registry()
        matched = reg.match_triggers("Please DEPLOY the service now")
        assert [s.id for s in matched] == ["deploy"]

    def test_keyword_trigger_chinese(self):
        reg = self._registry()
        matched = reg.match_triggers("帮我发布一下")
        assert [s.id for s in matched] == ["deploy"]

    def test_no_match_returns_empty(self):
        reg = self._registry()
        assert reg.match_triggers("just chatting") == []

    def test_path_trigger_glob(self):
        reg = self._registry()
        matched = reg.match_triggers("check this file", file_paths=["src/main.py"])
        assert [s.id for s in matched] == ["py-style"]

    def test_path_trigger_no_match(self):
        reg = self._registry()
        assert reg.match_triggers("check this file", file_paths=["README.md"]) == []

    def test_disabled_skill_not_matched(self):
        reg = self._registry()
        reg.disable("deploy")
        assert reg.match_triggers("deploy now") == []

    def test_extract_file_paths_from_text(self):
        from app.skills.repo_knowledge import extract_file_paths
        paths = extract_file_paths("看看 src/app/main.py 和 docs/guide.md 有没有问题")
        assert "src/app/main.py" in paths
        assert "docs/guide.md" in paths

    def test_extract_file_paths_from_nested_tool_arguments(self):
        from app.skills.repo_knowledge import extract_paths_from_values

        paths = extract_paths_from_values({
            "path": "src/main.py",
            "options": {"references": ["docs/guide.md", "plain text"]},
        })
        assert paths == ["src/main.py", "docs/guide.md"]


class TestRepoKnowledgePack:
    def test_parse_skill_markdown(self):
        raw = """---
name: Repo Rules
description: Project conventions
triggers:
  - convention
paths:
  - "src/**"
---
Always run tests before commit.
Use Chinese in docs.
"""
        skill = parse_skill_markdown(raw, skill_id="repo-rules")
        assert skill.name == "Repo Rules"
        assert skill.triggers == ["convention"]
        assert skill.path_triggers == ["src/**"]
        assert "Always run tests" in skill.system_prompt
        assert skill.category == SkillCategory.KNOWLEDGE

    def test_parse_without_frontmatter(self):
        skill = parse_skill_markdown("Just a body.", skill_id="bare")
        assert skill.system_prompt == "Just a body."
        assert skill.triggers == []

    def test_load_repo_skills(self, tmp_path):
        skills_dir = tmp_path / ".climber" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "rules.md").write_text(
            "---\nname: Rules\ntriggers:\n  - rule\n---\nBody here.\n",
            encoding="utf-8",
        )
        reg = SkillRegistry()
        count = load_repo_skills(reg, tmp_path)
        assert count == 1
        assert reg.get("rules") is not None
        assert reg.match_triggers("tell me the rule")[0].id == "rules"

    def test_load_repo_skills_missing_dir(self, tmp_path):
        reg = SkillRegistry()
        assert load_repo_skills(reg, tmp_path) == 0
