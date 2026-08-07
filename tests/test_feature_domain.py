"""Tests for feature domain."""


from app.domains.feature_domain import (
    FeatureEntity,
    FeatureEntityFactory,
    FeatureEntityRepository,
    FeatureValidator,
)


class TestFeatureEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = FeatureEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = FeatureEntityFactory.create('test')
        assert entity.name == 'test'


class TestFeatureEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = FeatureEntityRepository()
        entity = FeatureEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = FeatureEntityRepository()
        repo.save(FeatureEntity(name='e1'))
        repo.save(FeatureEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = FeatureEntityRepository()
        entity = FeatureEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = FeatureEntityRepository()
        repo.save(FeatureEntity(name='e1'))
        repo.save(FeatureEntity(name='e2'))
        assert repo.count() == 2


class TestFeatureValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = FeatureEntity(name='test', status='active')
        assert FeatureValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = FeatureEntity(name='', status='active')
        errors = FeatureValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = FeatureEntity(name='test', status='invalid')
        errors = FeatureValidator.validate(entity)
        assert len(errors) > 0
