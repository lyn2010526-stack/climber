"""Tests for attachment domain."""


from app.domains.attachment_domain import (
    AttachmentEntity,
    AttachmentEntityFactory,
    AttachmentEntityRepository,
    AttachmentValidator,
)


class TestAttachmentEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = AttachmentEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = AttachmentEntityFactory.create('test')
        assert entity.name == 'test'


class TestAttachmentEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = AttachmentEntityRepository()
        entity = AttachmentEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = AttachmentEntityRepository()
        repo.save(AttachmentEntity(name='e1'))
        repo.save(AttachmentEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = AttachmentEntityRepository()
        entity = AttachmentEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = AttachmentEntityRepository()
        repo.save(AttachmentEntity(name='e1'))
        repo.save(AttachmentEntity(name='e2'))
        assert repo.count() == 2


class TestAttachmentValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = AttachmentEntity(name='test', status='active')
        assert AttachmentValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = AttachmentEntity(name='', status='active')
        errors = AttachmentValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = AttachmentEntity(name='test', status='invalid')
        errors = AttachmentValidator.validate(entity)
        assert len(errors) > 0
