"""Tests for plan domain."""


from app.domains.plan_domain import (
    PlanEntity,
    PlanEntityFactory,
    PlanEntityRepository,
    PlanValidator,
)


class TestPlanEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = PlanEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = PlanEntityFactory.create('test')
        assert entity.name == 'test'


class TestPlanEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = PlanEntityRepository()
        entity = PlanEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = PlanEntityRepository()
        repo.save(PlanEntity(name='e1'))
        repo.save(PlanEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = PlanEntityRepository()
        entity = PlanEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = PlanEntityRepository()
        repo.save(PlanEntity(name='e1'))
        repo.save(PlanEntity(name='e2'))
        assert repo.count() == 2


class TestPlanValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = PlanEntity(name='test', status='active')
        assert PlanValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = PlanEntity(name='', status='active')
        errors = PlanValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = PlanEntity(name='test', status='invalid')
        errors = PlanValidator.validate(entity)
        assert len(errors) > 0
