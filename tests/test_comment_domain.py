"""Tests for comment domain."""

import pytest

from app.domains.comment_domain import (
    CommentCreateDTO,
    CommentRepository,
)


class TestCommentRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = CommentRepository()
        dto = CommentCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = CommentRepository()
        dto = CommentCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = CommentRepository()
        await repo.create(CommentCreateDTO(name='A'))
        await repo.create(CommentCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
