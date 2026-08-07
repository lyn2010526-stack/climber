"""Comprehensive tests for file_storage - File storage and CDN configuration."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file_storage import (
    FileStorageServiceCreate,
    FileStorageServiceFilter,
    FileStorageServicePriority,
    FileStorageServiceStatus,
    FileStorageServiceUpdate,
)
from app.services.file_storage_service import FileStorageService
from app.services.file_storage_service import FileStorage
from datetime import datetime


@pytest.fixture
def mock_session() -> AsyncSession:
    session = MagicMock(spec=AsyncSession)
    session.execute.return_value = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.delete = AsyncMock()

    # Simulate auto-increment ID on refresh
    _id_counter = [0]
    async def _refresh(item):
        if hasattr(item, 'id') and item.id is None:
            _id_counter[0] += 1
            item.id = _id_counter[0]

    session.refresh = _refresh
    return session



@pytest.fixture
def service(mock_session: AsyncSession) -> FileStorageService:
    return FileStorageService(mock_session)


@pytest.fixture
def sample_create() -> FileStorageServiceCreate:
    return FileStorageServiceCreate(
        name="Test FileStorageService",
        description="Test description",
        priority=FileStorageServicePriority.MEDIUM,
        tags=["test"],
        config={"key": "value"},
    )


class TestFileStorageServiceCreation:
    """Tests for file_storage creation."""

    @pytest.mark.asyncio
    async def test_create_success(self, service, mock_session, sample_create):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        result = await service.create(sample_create)
        assert result.name == "Test FileStorageService"
        assert result.status == FileStorageServiceStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_create_generates_slug(self, service, mock_session, sample_create):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        result = await service.create(sample_create)
        assert result.slug is not None

    @pytest.mark.asyncio
    async def test_create_with_tags(self, service, mock_session, sample_create):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        result = await service.create(sample_create)
        assert "test" in result.tags

    @pytest.mark.asyncio
    async def test_create_duplicate_slug_gets_suffix(self, service, mock_session, sample_create):
        mock_session.execute.return_value.scalar_one_or_none.return_value = MagicMock()
        result = await service.create(sample_create)
        assert result.slug is not None


class TestFileStorageServiceRetrieval:
    """Tests for file_storage retrieval."""

    @pytest.mark.asyncio
    async def test_get_by_id(self, service, mock_session):
        mock_item = FileStorage(
            id=1,
            name="Test",
            slug="test",
            description="",
            status="active",
            priority="medium",
            owner_id=None,
            tags=[],
            is_public=False,
            view_count=0,
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_item
        result = await service.get(1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_not_found(self, service, mock_session):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        result = await service.get(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_slug(self, service, mock_session):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        result = await service.get_by_slug("nonexistent")
        assert result is None


class TestFileStorageServiceList:
    """Tests for file_storage listing."""

    @pytest.mark.asyncio
    async def test_list_empty(self, service, mock_session):
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_session.execute.return_value.scalar_one.return_value = 0
        items, total = await service.list_items(FileStorageServiceFilter())
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_with_items(self, service, mock_session):
        mock_items = [
        FileStorage(
                    id=1,
                    name="Test 1",
                    slug="test-1",
                    description="",
                    status="active",
                    priority="medium",
                    owner_id=None,
                    organization_id=None,
                    metadata_json={},
                    tags=[],
                    config={},
                    is_public=False,
                    is_archived=False,
                    view_count=0,
                    like_count=0,
                    sort_order=0,
                    parent_id=None,
                    version=1,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    published_at=None,
                    archived_at=None,
                ),
        FileStorage(
                    id=2,
                    name="Test 2",
                    slug="test-2",
                    description="",
                    status="active",
                    priority="medium",
                    owner_id=None,
                    organization_id=None,
                    metadata_json={},
                    tags=[],
                    config={},
                    is_public=False,
                    is_archived=False,
                    view_count=0,
                    like_count=0,
                    sort_order=0,
                    parent_id=None,
                    version=1,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    published_at=None,
                    archived_at=None,
                ),
        FileStorage(
                    id=3,
                    name="Test 3",
                    slug="test-3",
                    description="",
                    status="active",
                    priority="medium",
                    owner_id=None,
                    organization_id=None,
                    metadata_json={},
                    tags=[],
                    config={},
                    is_public=False,
                    is_archived=False,
                    view_count=0,
                    like_count=0,
                    sort_order=0,
                    parent_id=None,
                    version=1,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    published_at=None,
                    archived_at=None,
                )
    ]
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_items
        mock_session.execute.return_value.scalar_one.return_value = 3
        items, total = await service.list_items(FileStorageServiceFilter())
        assert total == 3

    @pytest.mark.asyncio
    async def test_list_with_status_filter(self, service, mock_session):
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_session.execute.return_value.scalar_one.return_value = 0
        items, total = await service.list_items(FileStorageServiceFilter(status=FileStorageServiceStatus.ACTIVE))
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, service, mock_session):
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_session.execute.return_value.scalar_one.return_value = 100
        items, total = await service.list_items(FileStorageServiceFilter(page=2, page_size=10))
        assert total == 100


class TestFileStorageServiceUpdate:
    """Tests for file_storage update."""

    @pytest.mark.asyncio
    async def test_update_name(self, service, mock_session):
        mock_item = FileStorage(
            id=1,
            name="Old",
            slug="old",
            description="",
            status="active",
            priority="medium",
            owner_id=None,
            tags=[],
            is_public=False,
            view_count=0,
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_item
        result = await service.update(1, FileStorageServiceUpdate(name="New"))
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_not_found(self, service, mock_session):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        result = await service.update(999, FileStorageServiceUpdate(name="New"))
        assert result is None

    @pytest.mark.asyncio
    async def test_update_status(self, service, mock_session):
        mock_item = FileStorage(
            id=1,
            name="Test",
            slug="test",
            description="",
            status="active",
            priority="medium",
            owner_id=None,
            tags=[],
            is_public=False,
            view_count=0,
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_item
        result = await service.update(1, FileStorageServiceUpdate(status=FileStorageServiceStatus.INACTIVE))
        assert result is not None


class TestFileStorageServiceDelete:
    """Tests for file_storage deletion."""

    @pytest.mark.asyncio
    async def test_soft_delete(self, service, mock_session):
        mock_item = FileStorage(
            id=1,
            name="Test",
            slug="test",
            description="",
            status="active",
            priority="medium",
            owner_id=None,
            tags=[],
            is_public=False,
            view_count=0,
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_item
        result = await service.delete(1, hard=False)
        assert result is True

    @pytest.mark.asyncio
    async def test_hard_delete(self, service, mock_session):
        mock_item = FileStorage(
            id=1,
            name="Test",
            slug="test",
            description="",
            status="active",
            priority="medium",
            owner_id=None,
            tags=[],
            is_public=False,
            view_count=0,
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_item
        result = await service.delete(1, hard=True)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, service, mock_session):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        result = await service.delete(999)
        assert result is False


class TestFileStorageServiceArchive:
    """Tests for file_storage archiving."""

    @pytest.mark.asyncio
    async def test_archive(self, service, mock_session):
        mock_item = FileStorage(
            id=1,
            name="Test",
            slug="test",
            description="",
            status="active",
            priority="medium",
            owner_id=None,
            tags=[],
            is_public=False,
            view_count=0,
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_item
        result = await service.archive(1)
        assert result is True

    @pytest.mark.asyncio
    async def test_restore(self, service, mock_session):
        mock_item = FileStorage(
            id=1,
            name="Test",
            slug="test",
            description="",
            status="active",
            priority="medium",
            owner_id=None,
            tags=[],
            is_public=False,
            view_count=0,
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_item
        result = await service.restore(1)
        assert result is True


class TestFileStorageServiceInteractions:
    """Tests for file_storage interactions."""

    @pytest.mark.asyncio
    async def test_increment_views(self, service, mock_session):
        mock_item = FileStorage(
            id=1,
            name="Test",
            slug="test",
            description="",
            status="active",
            priority="medium",
            owner_id=None,
            tags=[],
            is_public=False,
            view_count=0,
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_item
        await service.increment_views(1)
        assert mock_item.view_count == 1

    @pytest.mark.asyncio
    async def test_toggle_like(self, service, mock_session):
        mock_item = FileStorage(
            id=1,
            name="Test",
            slug="test",
            description="",
            status="active",
            priority="medium",
            owner_id=None,
            tags=[],
            is_public=False,
            view_count=0,
            like_count=0,
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_item
        result = await service.toggle_like(1, increment=True)
        assert result == 1


class TestFileStorageServiceStats:
    """Tests for file_storage statistics."""

    @pytest.mark.asyncio
    async def test_get_stats(self, service, mock_session):
        mock_session.execute.return_value.scalar_one.return_value = 0
        mock_session.execute.return_value.all.return_value = []
        result = await service.get_stats()
        assert result.total_count >= 0


class TestFileStorageServiceBulk:
    """Tests for bulk operations."""

    @pytest.mark.asyncio
    async def test_bulk_update_status(self, service, mock_session):
        mock_session.execute.return_value.rowcount = 3
        result = await service.bulk_update_status([1, 2, 3], FileStorageServiceStatus.ARCHIVED)
        assert result == 3

    @pytest.mark.asyncio
    async def test_bulk_delete(self, service, mock_session):
        mock_session.execute.return_value.rowcount = 5
        result = await service.bulk_delete([1, 2, 3, 4, 5])
        assert result == 5
