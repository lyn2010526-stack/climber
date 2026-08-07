"""Tests for account domain."""


from app.domains.account_domain import (
    AccountEntity,
    AccountEntityFactory,
    AccountEntityRepository,
    AccountValidator,
)


class TestAccountEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = AccountEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = AccountEntityFactory.create('test')
        assert entity.name == 'test'


class TestAccountEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = AccountEntityRepository()
        entity = AccountEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = AccountEntityRepository()
        repo.save(AccountEntity(name='e1'))
        repo.save(AccountEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = AccountEntityRepository()
        entity = AccountEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = AccountEntityRepository()
        repo.save(AccountEntity(name='e1'))
        repo.save(AccountEntity(name='e2'))
        assert repo.count() == 2


class TestAccountValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = AccountEntity(name='test', status='active')
        assert AccountValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = AccountEntity(name='', status='active')
        errors = AccountValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = AccountEntity(name='test', status='invalid')
        errors = AccountValidator.validate(entity)
        assert len(errors) > 0
