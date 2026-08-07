"""Tests for promotion domain."""


from app.domains.promotion_domain import (
    PromotionEntity,
    PromotionEntityFactory,
    PromotionEntityRepository,
    PromotionValidator,
)


class TestPromotionEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = PromotionEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = PromotionEntityFactory.create('test')
        assert entity.name == 'test'


class TestPromotionEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = PromotionEntityRepository()
        entity = PromotionEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = PromotionEntityRepository()
        repo.save(PromotionEntity(name='e1'))
        repo.save(PromotionEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = PromotionEntityRepository()
        entity = PromotionEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = PromotionEntityRepository()
        repo.save(PromotionEntity(name='e1'))
        repo.save(PromotionEntity(name='e2'))
        assert repo.count() == 2


class TestPromotionValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = PromotionEntity(name='test', status='active')
        assert PromotionValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = PromotionEntity(name='', status='active')
        errors = PromotionValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = PromotionEntity(name='test', status='invalid')
        errors = PromotionValidator.validate(entity)
        assert len(errors) > 0
