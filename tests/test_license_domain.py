"""Tests for license domain."""


from app.domains.license_domain import (
    LicenseEntity,
    LicenseEntityFactory,
    LicenseEntityRepository,
    LicenseValidator,
)


class TestLicenseEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = LicenseEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = LicenseEntityFactory.create('test')
        assert entity.name == 'test'


class TestLicenseEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = LicenseEntityRepository()
        entity = LicenseEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = LicenseEntityRepository()
        repo.save(LicenseEntity(name='e1'))
        repo.save(LicenseEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = LicenseEntityRepository()
        entity = LicenseEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = LicenseEntityRepository()
        repo.save(LicenseEntity(name='e1'))
        repo.save(LicenseEntity(name='e2'))
        assert repo.count() == 2


class TestLicenseValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = LicenseEntity(name='test', status='active')
        assert LicenseValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = LicenseEntity(name='', status='active')
        errors = LicenseValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = LicenseEntity(name='test', status='invalid')
        errors = LicenseValidator.validate(entity)
        assert len(errors) > 0
