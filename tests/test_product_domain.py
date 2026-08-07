"""Tests for product domain."""


from app.domains.product_domain import (
    ProductEntity,
    ProductEntityFactory,
    ProductEntityRepository,
    ProductValidator,
)


class TestProductEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = ProductEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = ProductEntityFactory.create('test')
        assert entity.name == 'test'


class TestProductEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = ProductEntityRepository()
        entity = ProductEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = ProductEntityRepository()
        repo.save(ProductEntity(name='e1'))
        repo.save(ProductEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = ProductEntityRepository()
        entity = ProductEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = ProductEntityRepository()
        repo.save(ProductEntity(name='e1'))
        repo.save(ProductEntity(name='e2'))
        assert repo.count() == 2


class TestProductValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = ProductEntity(name='test', status='active')
        assert ProductValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = ProductEntity(name='', status='active')
        errors = ProductValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = ProductEntity(name='test', status='invalid')
        errors = ProductValidator.validate(entity)
        assert len(errors) > 0
