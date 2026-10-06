"""Coverage tests for app.core.engine.pregel.command."""

from __future__ import annotations

from app.core.engine.pregel.command import Command, is_command, parse_node_output


def test_command_repr_all_variants() -> None:
    assert repr(Command()) == "Command()"
    empty_update = Command(update={})
    assert repr(empty_update) == "Command()"
    cmd = Command(update={"a": 1}, goto="next", resume="v")
    text = repr(cmd)
    assert "update=['a']" in text
    assert "goto=next" in text
    assert "resume=<value>" in text


def test_command_parent_factory() -> None:
    cmd = Command.PARENT(update={"x": 1})
    assert cmd.goto == "__parent__"
    assert cmd.update == {"x": 1}
    assert Command.PARENT().update is None


def test_command_flags() -> None:
    assert Command().is_interrupt is False
    assert Command(metadata={"interrupt": True}).is_interrupt is True
    assert Command(goto="__end__").is_end is True
    assert Command(goto="other").is_end is False
    assert Command().metadata == {}


def test_is_command_helper() -> None:
    assert is_command(Command()) is True
    assert is_command({"a": 1}) is False


def test_parse_node_output_command() -> None:
    cmd = Command(update={"a": 1}, goto="b", resume=5)
    assert parse_node_output(cmd) == ({"a": 1}, "b", 5)


def test_parse_node_output_dict_str_tuple() -> None:
    assert parse_node_output({"a": 1}) == ({"a": 1}, None, None)
    assert parse_node_output("next") == (None, "next", None)
    assert parse_node_output(({"a": 1}, "next")) == ({"a": 1}, "next", None)
    assert parse_node_output(({"a": 1}, ["a", "b"])) == ({"a": 1}, ["a", "b"], None)


def test_parse_node_output_invalid() -> None:
    assert parse_node_output(None) == (None, None, None)
    assert parse_node_output(42) == (None, None, None)
    # tuple with wrong contents
    assert parse_node_output(([1, 2], "next")) == (None, None, None)
    # tuple of wrong arity
    assert parse_node_output(({"a": 1}, "b", "c")) == (None, None, None)
