"""Tests for discount domain."""


from app.domains.discount_domain import (
    DiscountEntity,
    DiscountEntityFactory,
    DiscountEntityRepository,
    DiscountValidator,
)


class TestDiscountEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = DiscountEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = DiscountEntityFactory.create('test')
        assert entity.name == 'test'


class TestDiscountEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = DiscountEntityRepository()
        entity = DiscountEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = DiscountEntityRepository()
        repo.save(DiscountEntity(name='e1'))
        repo.save(DiscountEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = DiscountEntityRepository()
        entity = DiscountEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = DiscountEntityRepository()
        repo.save(DiscountEntity(name='e1'))
        repo.save(DiscountEntity(name='e2'))
        assert repo.count() == 2


class TestDiscountValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = DiscountEntity(name='test', status='active')
        assert DiscountValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = DiscountEntity(name='', status='active')
        errors = DiscountValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = DiscountEntity(name='test', status='invalid')
        errors = DiscountValidator.validate(entity)
        assert len(errors) > 0
