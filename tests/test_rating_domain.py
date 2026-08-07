"""Tests for rating domain."""


from app.domains.rating_domain import (
    RatingEntity,
    RatingEntityFactory,
    RatingEntityRepository,
    RatingValidator,
)


class TestRatingEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = RatingEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = RatingEntityFactory.create('test')
        assert entity.name == 'test'


class TestRatingEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = RatingEntityRepository()
        entity = RatingEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = RatingEntityRepository()
        repo.save(RatingEntity(name='e1'))
        repo.save(RatingEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = RatingEntityRepository()
        entity = RatingEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = RatingEntityRepository()
        repo.save(RatingEntity(name='e1'))
        repo.save(RatingEntity(name='e2'))
        assert repo.count() == 2


class TestRatingValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = RatingEntity(name='test', status='active')
        assert RatingValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = RatingEntity(name='', status='active')
        errors = RatingValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = RatingEntity(name='test', status='invalid')
        errors = RatingValidator.validate(entity)
        assert len(errors) > 0
