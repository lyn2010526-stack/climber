"""Tests for tax domain."""


from app.domains.tax_domain import (
    TaxEntity,
    TaxEntityFactory,
    TaxEntityRepository,
    TaxValidator,
)


class TestTaxEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = TaxEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = TaxEntityFactory.create('test')
        assert entity.name == 'test'


class TestTaxEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = TaxEntityRepository()
        entity = TaxEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = TaxEntityRepository()
        repo.save(TaxEntity(name='e1'))
        repo.save(TaxEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = TaxEntityRepository()
        entity = TaxEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = TaxEntityRepository()
        repo.save(TaxEntity(name='e1'))
        repo.save(TaxEntity(name='e2'))
        assert repo.count() == 2


class TestTaxValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = TaxEntity(name='test', status='active')
        assert TaxValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = TaxEntity(name='', status='active')
        errors = TaxValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = TaxEntity(name='test', status='invalid')
        errors = TaxValidator.validate(entity)
        assert len(errors) > 0
