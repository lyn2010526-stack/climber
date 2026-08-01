import pytest
from app.core.agent_protocol import (
    AgentMessage, MessageType, Priority, Confidence,
    FileChange, TestConclusion, MessageBus
)

def test_message_creation():
    msg = AgentMessage(
        type=MessageType.CODE_CHANGE,
        sender="coder",
        content="Added new feature",
        session_id="s1",
    )
    assert msg.type == MessageType.CODE_CHANGE
    assert msg.sender == "coder"
    assert len(msg.message_id) == 12

def test_message_to_dict():
    msg = AgentMessage(
        type=MessageType.TEST_RESULT,
        sender="tester",
        content="All tests passed",
        session_id="s1",
    )
    d = msg.to_dict()
    assert d["type"] == "test_result"
    assert d["sender"] == "tester"

def test_message_from_dict():
    data = {
        "type": "code_review",
        "sender": "reviewer",
        "content": "Looks good",
        "session_id": "s1",
    }
    msg = AgentMessage.from_dict(data)
    assert msg.type == MessageType.CODE_REVIEW

def test_message_bus_publish_and_subscribe():
    bus = MessageBus()
    received = []
    bus.subscribe(MessageType.PROGRESS, lambda m: received.append(m))

    msg = AgentMessage(type=MessageType.PROGRESS, sender="agent", content="working")
    bus.publish(msg)

    assert len(received) == 1
    assert received[0].type == MessageType.PROGRESS

def test_message_bus_history():
    bus = MessageBus()
    for i in range(5):
        bus.publish(AgentMessage(type=MessageType.PROGRESS, sender="a", content=f"msg {i}", session_id="s1"))

    history = bus.get_history(session_id="s1")
    assert len(history) == 5

def test_file_change_in_message():
    msg = AgentMessage(
        type=MessageType.CODE_CHANGE,
        sender="coder",
        content="Modified auth.py",
        file_changes=[
            FileChange(file_path="auth.py", change_type="modify", description="Added OAuth")
        ],
    )
    d = msg.to_dict()
    assert len(d["file_changes"]) == 1
