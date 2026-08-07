"""Tests for billing domain."""


from app.domains.billing_domain import (
    BillingEntity,
    BillingEntityFactory,
    BillingEntityRepository,
    BillingValidator,
)


class TestBillingEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = BillingEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = BillingEntityFactory.create('test')
        assert entity.name == 'test'


class TestBillingEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = BillingEntityRepository()
        entity = BillingEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = BillingEntityRepository()
        repo.save(BillingEntity(name='e1'))
        repo.save(BillingEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = BillingEntityRepository()
        entity = BillingEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = BillingEntityRepository()
        repo.save(BillingEntity(name='e1'))
        repo.save(BillingEntity(name='e2'))
        assert repo.count() == 2


class TestBillingValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = BillingEntity(name='test', status='active')
        assert BillingValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = BillingEntity(name='', status='active')
        errors = BillingValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = BillingEntity(name='test', status='invalid')
        errors = BillingValidator.validate(entity)
        assert len(errors) > 0
