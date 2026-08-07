"""Integration tests for features extracted from 20 open-source AI projects.

Tests each new module to verify correct functionality.
"""

from __future__ import annotations


class TestSOPEngine:
    """Tests for MetaGPT-inspired SOP Engine."""

    def test_register_template(self):
        from app.core.sop_engine import Phase, SOPEngine, SOPTemplate
        engine = SOPEngine()
        template = SOPTemplate(
            name="test_sop",
            description="Test SOP",
            phases=[Phase(name="step1", role="Tester", description="Test step")],
        )
        engine.register_template(template)
        assert engine.get_template("test_sop") is not None

    def test_default_templates(self):
        from app.core.sop_engine import SOPEngine
        engine = SOPEngine()
        templates = engine.list_templates()
        assert len(templates) >= 2
        names = [t["name"] for t in templates]
        assert "software_development" in names
        assert "data_analysis" in names

    def test_execution_order(self):
        from app.core.sop_engine import SOPEngine
        engine = SOPEngine()
        levels = engine.get_execution_order("software_development")
        assert len(levels) > 0
        assert "requirements" in levels[0]

    def test_phase_prompt_building(self):
        from app.core.sop_engine import Phase, SOPEngine
        engine = SOPEngine()
        phase = Phase(
            name="test",
            role="Developer",
            description="Write code",
            output_schema={"type": "object", "properties": {"code": {"type": "string"}}},
        )
        prompt = engine.build_phase_prompt(phase, {"input": "test data"})
        assert "Developer" in prompt
        assert "Write code" in prompt
        assert "test data" in prompt


class TestRepoMapper:
    """Tests for Aider/SWE-agent inspired Repo Mapper."""

    def test_scan_directory(self, tmp_path):
        from app.core.repo_mapper import RepoMapper
        (tmp_path / "main.py").write_text("def hello():\n    pass\n")
        (tmp_path / "test.py").write_text("import main\n\nclass Test:\n    pass\n")
        mapper = RepoMapper(str(tmp_path))
        repo_map = mapper.scan()
        assert repo_map.total_files >= 2
        assert "main.py" in repo_map.files or "test.py" in repo_map.files

    def test_find_symbol(self, tmp_path):
        from app.core.repo_mapper import RepoMapper
        (tmp_path / "app.py").write_text(
            "def process():\n    pass\n\nclass Handler:\n    def handle(self):\n        pass\n"
        )
        mapper = RepoMapper(str(tmp_path))
        repo_map = mapper.scan()
        symbols = repo_map.find_symbol("process")
        assert len(symbols) > 0

    def test_get_context_for_edit(self, tmp_path):
        from app.core.repo_mapper import RepoMapper
        (tmp_path / "main.py").write_text("import os\n\ndef main():\n    pass\n")
        mapper = RepoMapper(str(tmp_path))
        repo_map = mapper.scan()
        context = repo_map.get_context_for_edit("main.py")
        assert "main.py" in context


class TestOutputSchema:
    """Tests for PydanticAI-inspired Output Schema validation."""

    def test_validate_object(self):
        from app.core.output_schema import OutputValidator
        validator = OutputValidator()
        validator.register_schema("test", {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        })
        result = validator.validate("test", {"name": "hello"})
        assert result.valid

    def test_validate_missing_required(self):
        from app.core.output_schema import OutputValidator
        validator = OutputValidator()
        validator.register_schema("test", {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        })
        result = validator.validate("test", {})
        assert not result.valid
        assert len(result.errors) > 0

    def test_validate_array(self):
        from app.core.output_schema import OutputValidator
        validator = OutputValidator()
        validator.register_schema("items", {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string"},
        })
        result = validator.validate("items", ["a", "b"])
        assert result.valid

    def test_validate_number_range(self):
        from app.core.output_schema import OutputValidator
        validator = OutputValidator()
        validator.register_schema("score", {
            "type": "number",
            "minimum": 0,
            "maximum": 10,
        })
        assert validator.validate("score", 5).valid
        assert not validator.validate("score", 15).valid

    def test_retry_prompt(self):
        from app.core.output_schema import OutputValidator
        validator = OutputValidator()
        validator.register_schema("test", {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        })
        prompt = validator.build_retry_prompt("test", ["Missing name"], "{}")
        assert "Validation Failed" in prompt
        assert "Missing name" in prompt


class TestRolePlay:
    """Tests for CAMEL-inspired Role Play protocol."""

    def test_create_session(self):
        from app.core.role_play import RoleDefinition, RolePlayConfig, RolePlayOrchestrator
        orch = RolePlayOrchestrator()
        config = RolePlayConfig(
            task="Build a web app",
            roles=[
                RoleDefinition(name="Developer", description="Writes code", goals=["Build features"]),
                RoleDefinition(name="Reviewer", description="Reviews code", goals=["Ensure quality"]),
            ],
        )
        session = orch.create_session("test_1", config)
        assert session is not None
        assert len(session.config.roles) == 2

    def test_specify_task(self):
        from app.core.role_play import RoleDefinition, RolePlayConfig, RolePlaySession
        config = RolePlayConfig(
            task="Build something",
            roles=[
                RoleDefinition(name="Dev", description="Developer", goals=["Code"]),
            ],
        )
        session = RolePlaySession(config)
        specified = session.specify_task()
        assert "Build something" in specified

    def test_dialogue_flow(self):
        from app.core.role_play import RoleDefinition, RolePlayConfig, RolePlaySession
        config = RolePlayConfig(
            task="Discuss architecture",
            roles=[
                RoleDefinition(name="Architect", description="Designs systems", goals=["Scalability"]),
                RoleDefinition(name="Engineer", description="Implements systems", goals=["Reliability"]),
            ],
            max_turns=4,
        )
        session = RolePlaySession(config)
        session.add_message("Architect", "Let's use microservices.")
        session.add_message("Engineer", "Agreed, but we need to consider deployment.")
        assert len(session.messages) == 2
        assert session.current_turn == 2

    def test_consensus_detection(self):
        from app.core.role_play import RoleDefinition, RolePlayConfig, RolePlaySession
        config = RolePlayConfig(
            task="Decide approach",
            roles=[
                RoleDefinition(name="A", description="Person A", goals=["Goal A"]),
                RoleDefinition(name="B", description="Person B", goals=["Goal B"]),
            ],
            consensus_threshold=2,
        )
        session = RolePlaySession(config)
        session.add_message("A", "I agree with this approach.")
        session.add_message("B", "I also agree, let's proceed.")
        assert session.check_consensus()


class TestPlanActController:
    """Tests for Cline-inspired Plan-Act controller."""

    def test_mode_switch(self):
        from app.core.plan_act_controller import ExecutionMode, PlanActController
        ctrl = PlanActController()
        assert ctrl.mode == ExecutionMode.PLAN
        ctrl.switch_mode(ExecutionMode.ACT)
        assert ctrl.mode == ExecutionMode.ACT

    def test_create_plan(self):
        from app.core.plan_act_controller import PlanActController
        ctrl = PlanActController()
        plan = ctrl.create_plan("Build authentication")
        assert plan.goal == "Build authentication"

    def test_add_steps(self):
        from app.core.plan_act_controller import PlanActController
        ctrl = PlanActController()
        plan = ctrl.create_plan("Test")
        plan.add_step("Write tests", "file_edit", "test.py")
        plan.add_step("Run tests", "command", "pytest")
        assert len(plan.steps) == 2

    def test_approval_policy(self):
        from app.core.plan_act_controller import ApprovalPolicy, PlanActController
        ctrl = PlanActController(approval_policy=ApprovalPolicy.AUTO_SAFE)
        assert ctrl.should_approve_action("search")
        assert not ctrl.should_approve_action("command", "rm -rf /")

    def test_risk_assessment(self):
        from app.core.plan_act_controller import PlanActController
        ctrl = PlanActController()
        assert ctrl.get_risk_level("search") == "low"
        assert ctrl.get_risk_level("command", "rm file") == "high"
        assert ctrl.get_risk_level("write_file") == "medium"

    def test_progress_tracking(self):
        from app.core.plan_act_controller import PlanActController
        ctrl = PlanActController()
        plan = ctrl.create_plan("Test")
        plan.add_step("Step 1", "search")
        plan.add_step("Step 2", "file_edit")
        ctrl.approve_plan()
        ctrl.record_step_result("step_1", "done", True)
        progress = ctrl.get_progress()
        assert progress["completed"] == 1
        assert progress["pending"] == 1


class TestFAQEngine:
    """Tests for FastGPT-inspired FAQ Engine."""

    def test_add_and_search(self):
        from app.core.faq_engine import FAQEngine, FAQEntry
        engine = FAQEngine()
        engine.add_entry(FAQEntry(
            question="How to install?",
            answer="Run pip install package",
            category="setup",
        ))
        results = engine.search("installation instructions")
        assert len(results) > 0

    def test_exact_match(self):
        from app.core.faq_engine import FAQEngine, FAQEntry
        engine = FAQEngine()
        engine.add_entry(FAQEntry(
            question="What is Python?",
            answer="A programming language",
        ))
        result = engine.answer("What is Python?")
        assert result["found"]
        assert result["confidence"] >= 0.8

    def test_no_match(self):
        from app.core.faq_engine import FAQEngine, FAQEntry
        engine = FAQEngine()
        engine.add_entry(FAQEntry(
            question="How to deploy?",
            answer="Use Docker",
        ))
        result = engine.answer("completely unrelated topic xyz")
        assert not result["found"]

    def test_categories(self):
        from app.core.faq_engine import FAQEngine, FAQEntry
        engine = FAQEngine()
        engine.add_entry(FAQEntry(question="Q1", answer="A1", category="setup"))
        engine.add_entry(FAQEntry(question="Q2", answer="A2", category="usage"))
        engine.add_entry(FAQEntry(question="Q3", answer="A3", category="setup"))
        cats = engine.list_categories()
        assert "setup" in cats
        assert "usage" in cats

    def test_remove_entry(self):
        from app.core.faq_engine import FAQEngine, FAQEntry
        engine = FAQEngine()
        engine.add_entry(FAQEntry(question="Test?", answer="Yes"))
        assert engine.size == 1
        engine.remove_entry("Test?")
        assert engine.size == 0


class TestMessageSearch:
    """Tests for LibreChat-inspired Message Search."""

    def test_index_and_search(self):
        from app.core.message_search import MessageSearchEngine, SearchQuery
        engine = MessageSearchEngine()
        engine.index_message("msg1", "session1", "user", "How to use Python?")
        engine.index_message("msg2", "session1", "assistant", "Python is a language.")
        results = engine.search(SearchQuery(text="Python"))
        assert len(results) > 0

    def test_session_filter(self):
        from app.core.message_search import MessageSearchEngine, SearchQuery
        engine = MessageSearchEngine()
        engine.index_message("msg1", "session1", "user", "Hello world")
        engine.index_message("msg2", "session2", "user", "Hello there")
        results = engine.search(SearchQuery(text="Hello", session_id="session1"))
        assert len(results) == 1
        assert results[0].session_id == "session1"

    def test_role_filter(self):
        from app.core.message_search import MessageSearchEngine, SearchQuery
        engine = MessageSearchEngine()
        engine.index_message("msg1", "s1", "user", "Help me code")
        engine.index_message("msg2", "s1", "assistant", "Sure, what do you need?")
        results = engine.search(SearchQuery(text="code", role="user"))
        assert all(r.role == "user" for r in results)

    def test_search_sessions(self):
        from app.core.message_search import MessageSearchEngine
        engine = MessageSearchEngine()
        engine.index_message("msg1", "session1", "user", "Docker setup")
        engine.index_message("msg2", "session2", "user", "Kubernetes config")
        sessions = engine.search_sessions("Docker")
        assert "session1" in sessions


class TestPatchGenerator:
    """Tests for SWE-agent/Aider inspired Patch Generator."""

    def test_create_patch(self):
        from app.core.patch_generator import PatchGenerator
        gen = PatchGenerator()
        original = "line1\nline2\nline3\n"
        modified = "line1\nmodified\nline3\n"
        patch = gen.create_patch("test.txt", original, modified)
        assert patch.additions == 1
        assert patch.deletions == 1
        assert "modified" in patch.diff

    def test_apply_patch(self):
        from app.core.patch_generator import PatchGenerator
        gen = PatchGenerator()
        original = "line1\nline2\nline3\n"
        modified = "line1\nmodified\nline3\n"
        patch = gen.create_patch("test.txt", original, modified)
        result = gen.apply_patch(original, patch.diff)
        assert result == modified

    def test_patch_set(self):
        from app.core.patch_generator import PatchGenerator
        gen = PatchGenerator()
        patch_set = gen.create_patch_set([
            {"file_path": "a.py", "original": "x=1\n", "modified": "x=2\n"},
            {"file_path": "b.py", "original": "y=1\n", "modified": "y=3\n"},
        ])
        assert len(patch_set.patches) == 2
        assert "a.py" in patch_set.affected_files

    def test_validate_patch(self):
        from app.core.patch_generator import PatchGenerator
        gen = PatchGenerator()
        original = "line1\nline2\nline3\n"
        modified = "line1\nmodified\nline3\n"
        patch = gen.create_patch("test.txt", original, modified)
        result = gen.validate_patch(original, patch.diff)
        assert result["valid"]
        assert result["changed"]


class TestModelArena:
    """Tests for Open WebUI-inspired Model Arena."""

    def test_create_comparison(self):
        from app.core.model_arena import ModelArena
        arena = ModelArena()
        result = arena.create_comparison("Hello?", [
            {"model_id": "gpt-4", "provider": "openai"},
            {"model_id": "claude", "provider": "anthropic"},
        ])
        assert len(result.responses) == 2

    def test_record_response(self):
        from app.core.model_arena import ModelArena
        arena = ModelArena()
        result = arena.create_comparison("Hi", [
            {"model_id": "gpt-4", "provider": "openai"},
        ])
        arena.record_response(result, "gpt-4", "Hello!", tokens_used=10, duration_ms=100)
        assert result.responses[0].content == "Hello!"

    def test_determine_winner(self):
        from app.core.model_arena import ModelArena
        arena = ModelArena()
        result = arena.create_comparison("Hi", [
            {"model_id": "model_a", "provider": "openai"},
            {"model_id": "model_b", "provider": "anthropic"},
        ])
        arena.score_response(result, "model_a", 8.0)
        arena.score_response(result, "model_b", 6.0)
        winner = arena.determine_winner(result, criteria="quality")
        assert winner == "model_a"

    def test_elo_ratings(self):
        from app.core.model_arena import ModelArena
        arena = ModelArena()
        arena.update_elo("model_a", "model_b")
        ratings = arena.get_elo_ratings()
        assert ratings["model_a"] > ratings["model_b"]

    def test_comparison_report(self):
        from app.core.model_arena import ModelArena
        arena = ModelArena()
        result = arena.create_comparison("Test prompt", [
            {"model_id": "gpt-4", "provider": "openai"},
        ])
        arena.record_response(result, "gpt-4", "Response", tokens_used=5)
        report = arena.generate_comparison_report(result)
        assert "Model Arena Comparison" in report
        assert "gpt-4" in report
