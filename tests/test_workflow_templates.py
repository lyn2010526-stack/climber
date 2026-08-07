"""Tests for WorkflowTemplates."""

from __future__ import annotations

from app.workflow.templates import WorkflowTemplates


class TestSimpleQA:
    """Tests for simple_qa template."""

    def test_creates_workflow(self):
        wf = WorkflowTemplates.simple_qa("openai", "gpt-4", "key123")
        assert wf.name == "Simple QA"
        assert len(wf.nodes) == 3
        assert len(wf.edges) == 2

    def test_start_node(self):
        wf = WorkflowTemplates.simple_qa("openai", "gpt-4", "key123")
        start = wf.get_node("start")
        assert start is not None
        assert start.type.value == "start"

    def test_llm_node_config(self):
        wf = WorkflowTemplates.simple_qa("openai", "gpt-4", "key123", "Custom prompt")
        llm = wf.get_node("llm")
        assert llm is not None
        assert llm.config["provider"] == "openai"
        assert llm.config["model_id"] == "gpt-4"
        assert llm.config["api_key"] == "key123"
        assert llm.config["system_prompt"] == "Custom prompt"

    def test_default_system_prompt(self):
        wf = WorkflowTemplates.simple_qa("openai", "gpt-4", "key123")
        llm = wf.get_node("llm")
        assert llm.config["system_prompt"] == "You are a helpful assistant."

    def test_end_node_inputs(self):
        wf = WorkflowTemplates.simple_qa("openai", "gpt-4", "key123")
        end = wf.get_node("end")
        assert end is not None
        assert end.inputs == {"result": "llm.response"}


class TestToolUse:
    """Tests for tool_use template."""

    def test_creates_workflow(self):
        wf = WorkflowTemplates.tool_use("calculator", "openai", "gpt-4", "key123")
        assert wf.name == "Tool Use"
        assert len(wf.nodes) == 6
        assert len(wf.edges) == 6

    def test_has_tool_node(self):
        wf = WorkflowTemplates.tool_use("calculator", "openai", "gpt-4", "key123")
        tool = wf.get_node("tool")
        assert tool is not None
        assert tool.config["tool_name"] == "calculator"

    def test_has_condition_node(self):
        wf = WorkflowTemplates.tool_use("calculator", "openai", "gpt-4", "key123")
        check = wf.get_node("check")
        assert check is not None
        assert check.config["operator"] == "contains"

    def test_conditional_edges(self):
        wf = WorkflowTemplates.tool_use("calculator", "openai", "gpt-4", "key123")
        edges = wf.edges
        true_edges = [e for e in edges if e.condition == "true"]
        false_edges = [e for e in edges if e.condition == "false"]
        assert len(true_edges) == 1
        assert len(false_edges) == 1


class TestChainOfThought:
    """Tests for chain_of_thought template."""

    def test_creates_workflow(self):
        wf = WorkflowTemplates.chain_of_thought("openai", "gpt-4", "key123", steps=3)
        assert wf.name == "Chain of Thought"

    def test_default_steps(self):
        wf = WorkflowTemplates.chain_of_thought("openai", "gpt-4", "key123")
        llm_nodes = [n for n in wf.nodes if n.type.value == "llm"]
        assert len(llm_nodes) == 3

    def test_custom_steps(self):
        wf = WorkflowTemplates.chain_of_thought("openai", "gpt-4", "key123", steps=5)
        llm_nodes = [n for n in wf.nodes if n.type.value == "llm"]
        assert len(llm_nodes) == 5

    def test_step_connections(self):
        wf = WorkflowTemplates.chain_of_thought("openai", "gpt-4", "key123", steps=2)
        step_0 = wf.get_node("step_0")
        step_1 = wf.get_node("step_1")
        assert step_0 is not None
        assert step_1 is not None


class TestMapReduce:
    """Tests for map_reduce template."""

    def test_creates_workflow(self):
        wf = WorkflowTemplates.map_reduce("openai", "gpt-4", "key123")
        assert wf.name == "Map Reduce"
        assert len(wf.nodes) == 4

    def test_has_iterator_node(self):
        wf = WorkflowTemplates.map_reduce("openai", "gpt-4", "key123")
        map_node = wf.get_node("map")
        assert map_node is not None
        assert map_node.type.value == "iterator"

    def test_iterator_config(self):
        wf = WorkflowTemplates.map_reduce("openai", "gpt-4", "key123")
        map_node = wf.get_node("map")
        assert map_node.config["item_var"] == "item"
        assert map_node.config["max_iterations"] == 50


class TestConditionalBranch:
    """Tests for conditional_branch template."""

    def test_creates_workflow(self):
        wf = WorkflowTemplates.conditional_branch(
            "openai", "gpt-4", "key123",
            "status", "ok",
            "Handle true", "Handle false",
        )
        assert wf.name == "Conditional Branch"
        assert len(wf.nodes) == 5

    def test_has_both_branches(self):
        wf = WorkflowTemplates.conditional_branch(
            "openai", "gpt-4", "key123",
            "status", "ok",
            "Handle true", "Handle false",
        )
        assert wf.get_node("true_branch") is not None
        assert wf.get_node("false_branch") is not None

    def test_branch_prompts(self):
        wf = WorkflowTemplates.conditional_branch(
            "openai", "gpt-4", "key123",
            "status", "ok",
            "True prompt", "False prompt",
        )
        true_node = wf.get_node("true_branch")
        false_node = wf.get_node("false_branch")
        assert true_node.config["prompt"] == "True prompt"
        assert false_node.config["prompt"] == "False prompt"


class TestListTemplates:
    """Tests for list_templates."""

    def test_returns_list(self):
        templates = WorkflowTemplates.list_templates()
        assert len(templates) == 5

    def test_template_ids(self):
        templates = WorkflowTemplates.list_templates()
        ids = [t["id"] for t in templates]
        assert "simple_qa" in ids
        assert "tool_use" in ids
        assert "chain_of_thought" in ids
        assert "map_reduce" in ids
        assert "conditional_branch" in ids

    def test_template_has_name_and_description(self):
        templates = WorkflowTemplates.list_templates()
        for t in templates:
            assert "name" in t
            assert "description" in t
