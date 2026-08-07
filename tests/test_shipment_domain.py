"""Tests for shipment domain."""


from app.domains.shipment_domain import (
    ShipmentEntity,
    ShipmentEntityFactory,
    ShipmentEntityRepository,
    ShipmentValidator,
)


class TestShipmentEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = ShipmentEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = ShipmentEntityFactory.create('test')
        assert entity.name == 'test'


class TestShipmentEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = ShipmentEntityRepository()
        entity = ShipmentEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = ShipmentEntityRepository()
        repo.save(ShipmentEntity(name='e1'))
        repo.save(ShipmentEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = ShipmentEntityRepository()
        entity = ShipmentEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = ShipmentEntityRepository()
        repo.save(ShipmentEntity(name='e1'))
        repo.save(ShipmentEntity(name='e2'))
        assert repo.count() == 2


class TestShipmentValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = ShipmentEntity(name='test', status='active')
        assert ShipmentValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = ShipmentEntity(name='', status='active')
        errors = ShipmentValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = ShipmentEntity(name='test', status='invalid')
        errors = ShipmentValidator.validate(entity)
        assert len(errors) > 0
