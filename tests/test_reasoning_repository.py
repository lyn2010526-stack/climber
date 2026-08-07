"""Tests for reasoning repository."""

from __future__ import annotations

import pytest

from app.storage.repository_reasoning import ReasoningFeedbackRepository, ReasoningTraceRepository


class TestReasoningTraceRepository:
    """Tests for ReasoningTraceRepository."""

    @pytest.mark.asyncio
    async def test_create_trace(self, db_session):
        repo = ReasoningTraceRepository(db_session)
        data = {
            "trace_id": "trace-001",
            "user_id": "user-001",
            "task": "Solve a math problem",
            "mode": "cot",
        }
        trace = await repo.create(data)
        assert trace.trace_id == "trace-001"
        assert trace.user_id == "user-001"
        assert trace.task == "Solve a math problem"

    @pytest.mark.asyncio
    async def test_get_by_trace_id(self, db_session):
        repo = ReasoningTraceRepository(db_session)
        data = {
            "trace_id": "trace-002",
            "user_id": "user-001",
            "task": "Analyze data",
            "mode": "react",
        }
        await repo.create(data)
        trace = await repo.get_by_trace_id("trace-002")
        assert trace is not None
        assert trace.trace_id == "trace-002"

    @pytest.mark.asyncio
    async def test_get_by_trace_id_nonexistent(self, db_session):
        repo = ReasoningTraceRepository(db_session)
        trace = await repo.get_by_trace_id("nonexistent")
        assert trace is None

    @pytest.mark.asyncio
    async def test_list_by_user(self, db_session):
        repo = ReasoningTraceRepository(db_session)
        for i in range(3):
            await repo.create({
                "trace_id": f"trace-user-{i}",
                "user_id": "user-list",
                "task": f"Task {i}",
                "mode": "cot",
            })
        traces = await repo.list_by_user("user-list")
        assert len(traces) == 3

    @pytest.mark.asyncio
    async def test_list_by_user_empty(self, db_session):
        repo = ReasoningTraceRepository(db_session)
        traces = await repo.list_by_user("user-empty")
        assert len(traces) == 0

    @pytest.mark.asyncio
    async def test_delete_trace(self, db_session):
        repo = ReasoningTraceRepository(db_session)
        data = {
            "trace_id": "trace-del",
            "user_id": "user-001",
            "task": "Delete me",
            "mode": "cot",
        }
        await repo.create(data)
        deleted = await repo.delete("trace-del")
        assert deleted is True
        trace = await repo.get_by_trace_id("trace-del")
        assert trace is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, db_session):
        repo = ReasoningTraceRepository(db_session)
        deleted = await repo.delete("nonexistent")
        assert deleted is False


class TestReasoningFeedbackRepository:
    """Tests for ReasoningFeedbackRepository."""

    @pytest.mark.asyncio
    async def test_create_feedback(self, db_session):
        # Create trace first (FK constraint)
        trace_repo = ReasoningTraceRepository(db_session)
        await trace_repo.create({
            "trace_id": "trace-001",
            "user_id": "user-001",
            "task": "Test task",
            "mode": "cot",
        })
        repo = ReasoningFeedbackRepository(db_session)
        data = {
            "trace_id": "trace-001",
            "user_id": "user-001",
            "rating": 5,
            "thumbs": "up",
            "comment": "Great reasoning!",
        }
        feedback = await repo.create(data)
        assert feedback.trace_id == "trace-001"
        assert feedback.rating == 5
        assert feedback.thumbs == "up"

    @pytest.mark.asyncio
    async def test_list_by_trace_id(self, db_session):
        trace_repo = ReasoningTraceRepository(db_session)
        await trace_repo.create({
            "trace_id": "trace-feedback",
            "user_id": "user-001",
            "task": "Test task",
            "mode": "cot",
        })
        repo = ReasoningFeedbackRepository(db_session)
        for i in range(2):
            await repo.create({
                "trace_id": "trace-feedback",
                "user_id": "user-001",
                "rating": 4 + i,
                "thumbs": "up",
                "comment": f"Feedback {i}",
            })
        feedbacks = await repo.list_by_trace_id("trace-feedback")
        assert len(feedbacks) == 2

    @pytest.mark.asyncio
    async def test_list_by_trace_id_empty(self, db_session):
        repo = ReasoningFeedbackRepository(db_session)
        feedbacks = await repo.list_by_trace_id("nonexistent")
        assert len(feedbacks) == 0

    @pytest.mark.asyncio
    async def test_list_by_user(self, db_session):
        trace_repo = ReasoningTraceRepository(db_session)
        for i in range(3):
            await trace_repo.create({
                "trace_id": f"trace-uf-{i}",
                "user_id": "user-feedback",
                "task": f"Task {i}",
                "mode": "cot",
            })
        repo = ReasoningFeedbackRepository(db_session)
        for i in range(3):
            await repo.create({
                "trace_id": f"trace-uf-{i}",
                "user_id": "user-feedback",
                "rating": 3,
                "thumbs": "down",
                "comment": f"Comment {i}",
            })
        feedbacks = await repo.list_by_user("user-feedback")
        assert len(feedbacks) == 3

    @pytest.mark.asyncio
    async def test_list_by_user_empty(self, db_session):
        repo = ReasoningFeedbackRepository(db_session)
        feedbacks = await repo.list_by_user("user-empty-feedback")
        assert len(feedbacks) == 0
