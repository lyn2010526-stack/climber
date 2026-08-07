"""Tests for contact domain."""


from app.domains.contact_domain import (
    ContactEntity,
    ContactEntityFactory,
    ContactEntityRepository,
    ContactValidator,
)


class TestContactEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = ContactEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = ContactEntityFactory.create('test')
        assert entity.name == 'test'


class TestContactEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = ContactEntityRepository()
        entity = ContactEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = ContactEntityRepository()
        repo.save(ContactEntity(name='e1'))
        repo.save(ContactEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = ContactEntityRepository()
        entity = ContactEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = ContactEntityRepository()
        repo.save(ContactEntity(name='e1'))
        repo.save(ContactEntity(name='e2'))
        assert repo.count() == 2


class TestContactValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = ContactEntity(name='test', status='active')
        assert ContactValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = ContactEntity(name='', status='active')
        errors = ContactValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = ContactEntity(name='test', status='invalid')
        errors = ContactValidator.validate(entity)
        assert len(errors) > 0
