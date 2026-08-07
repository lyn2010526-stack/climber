"""Tests for usage domain."""


from app.domains.usage_domain import (
    UsageEntity,
    UsageEntityFactory,
    UsageEntityRepository,
    UsageValidator,
)


class TestUsageEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = UsageEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = UsageEntityFactory.create('test')
        assert entity.name == 'test'


class TestUsageEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = UsageEntityRepository()
        entity = UsageEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = UsageEntityRepository()
        repo.save(UsageEntity(name='e1'))
        repo.save(UsageEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = UsageEntityRepository()
        entity = UsageEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = UsageEntityRepository()
        repo.save(UsageEntity(name='e1'))
        repo.save(UsageEntity(name='e2'))
        assert repo.count() == 2


class TestUsageValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = UsageEntity(name='test', status='active')
        assert UsageValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = UsageEntity(name='', status='active')
        errors = UsageValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = UsageEntity(name='test', status='invalid')
        errors = UsageValidator.validate(entity)
        assert len(errors) > 0
