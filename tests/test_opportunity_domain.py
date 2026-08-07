"""Tests for opportunity domain."""


from app.domains.opportunity_domain import (
    OpportunityEntity,
    OpportunityEntityFactory,
    OpportunityEntityRepository,
    OpportunityValidator,
)


class TestOpportunityEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = OpportunityEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = OpportunityEntityFactory.create('test')
        assert entity.name == 'test'


class TestOpportunityEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = OpportunityEntityRepository()
        entity = OpportunityEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = OpportunityEntityRepository()
        repo.save(OpportunityEntity(name='e1'))
        repo.save(OpportunityEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = OpportunityEntityRepository()
        entity = OpportunityEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = OpportunityEntityRepository()
        repo.save(OpportunityEntity(name='e1'))
        repo.save(OpportunityEntity(name='e2'))
        assert repo.count() == 2


class TestOpportunityValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = OpportunityEntity(name='test', status='active')
        assert OpportunityValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = OpportunityEntity(name='', status='active')
        errors = OpportunityValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = OpportunityEntity(name='test', status='invalid')
        errors = OpportunityValidator.validate(entity)
        assert len(errors) > 0
