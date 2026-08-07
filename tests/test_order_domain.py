"""Tests for order domain."""


from app.domains.order_domain import (
    OrderEntity,
    OrderEntityFactory,
    OrderEntityRepository,
    OrderValidator,
)


class TestOrderEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = OrderEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = OrderEntityFactory.create('test')
        assert entity.name == 'test'


class TestOrderEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = OrderEntityRepository()
        entity = OrderEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = OrderEntityRepository()
        repo.save(OrderEntity(name='e1'))
        repo.save(OrderEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = OrderEntityRepository()
        entity = OrderEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = OrderEntityRepository()
        repo.save(OrderEntity(name='e1'))
        repo.save(OrderEntity(name='e2'))
        assert repo.count() == 2


class TestOrderValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = OrderEntity(name='test', status='active')
        assert OrderValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = OrderEntity(name='', status='active')
        errors = OrderValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = OrderEntity(name='test', status='invalid')
        errors = OrderValidator.validate(entity)
        assert len(errors) > 0
