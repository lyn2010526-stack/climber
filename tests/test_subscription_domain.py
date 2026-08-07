"""Tests for subscription domain."""


from app.domains.subscription_domain import (
    SubscriptionEntity,
    SubscriptionEntityFactory,
    SubscriptionEntityRepository,
    SubscriptionValidator,
)


class TestSubscriptionEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = SubscriptionEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = SubscriptionEntityFactory.create('test')
        assert entity.name == 'test'


class TestSubscriptionEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = SubscriptionEntityRepository()
        entity = SubscriptionEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = SubscriptionEntityRepository()
        repo.save(SubscriptionEntity(name='e1'))
        repo.save(SubscriptionEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = SubscriptionEntityRepository()
        entity = SubscriptionEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = SubscriptionEntityRepository()
        repo.save(SubscriptionEntity(name='e1'))
        repo.save(SubscriptionEntity(name='e2'))
        assert repo.count() == 2


class TestSubscriptionValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = SubscriptionEntity(name='test', status='active')
        assert SubscriptionValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = SubscriptionEntity(name='', status='active')
        errors = SubscriptionValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = SubscriptionEntity(name='test', status='invalid')
        errors = SubscriptionValidator.validate(entity)
        assert len(errors) > 0
