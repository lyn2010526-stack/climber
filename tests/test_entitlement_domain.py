"""Tests for entitlement domain."""


from app.domains.entitlement_domain import (
    EntitlementEntity,
    EntitlementEntityFactory,
    EntitlementEntityRepository,
    EntitlementValidator,
)


class TestEntitlementEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = EntitlementEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = EntitlementEntityFactory.create('test')
        assert entity.name == 'test'


class TestEntitlementEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = EntitlementEntityRepository()
        entity = EntitlementEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = EntitlementEntityRepository()
        repo.save(EntitlementEntity(name='e1'))
        repo.save(EntitlementEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = EntitlementEntityRepository()
        entity = EntitlementEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = EntitlementEntityRepository()
        repo.save(EntitlementEntity(name='e1'))
        repo.save(EntitlementEntity(name='e2'))
        assert repo.count() == 2


class TestEntitlementValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = EntitlementEntity(name='test', status='active')
        assert EntitlementValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = EntitlementEntity(name='', status='active')
        errors = EntitlementValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = EntitlementEntity(name='test', status='invalid')
        errors = EntitlementValidator.validate(entity)
        assert len(errors) > 0
