"""Tests for inventory domain."""


from app.domains.inventory_domain import (
    InventoryEntity,
    InventoryEntityFactory,
    InventoryEntityRepository,
    InventoryValidator,
)


class TestInventoryEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = InventoryEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = InventoryEntityFactory.create('test')
        assert entity.name == 'test'


class TestInventoryEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = InventoryEntityRepository()
        entity = InventoryEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = InventoryEntityRepository()
        repo.save(InventoryEntity(name='e1'))
        repo.save(InventoryEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = InventoryEntityRepository()
        entity = InventoryEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = InventoryEntityRepository()
        repo.save(InventoryEntity(name='e1'))
        repo.save(InventoryEntity(name='e2'))
        assert repo.count() == 2


class TestInventoryValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = InventoryEntity(name='test', status='active')
        assert InventoryValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = InventoryEntity(name='', status='active')
        errors = InventoryValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = InventoryEntity(name='test', status='invalid')
        errors = InventoryValidator.validate(entity)
        assert len(errors) > 0
