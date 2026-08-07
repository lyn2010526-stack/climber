"""Tests for customer domain."""


from app.domains.customer_domain import (
    CustomerEntity,
    CustomerEntityFactory,
    CustomerEntityRepository,
    CustomerValidator,
)


class TestCustomerEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = CustomerEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = CustomerEntityFactory.create('test')
        assert entity.name == 'test'


class TestCustomerEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = CustomerEntityRepository()
        entity = CustomerEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = CustomerEntityRepository()
        repo.save(CustomerEntity(name='e1'))
        repo.save(CustomerEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = CustomerEntityRepository()
        entity = CustomerEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = CustomerEntityRepository()
        repo.save(CustomerEntity(name='e1'))
        repo.save(CustomerEntity(name='e2'))
        assert repo.count() == 2


class TestCustomerValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = CustomerEntity(name='test', status='active')
        assert CustomerValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = CustomerEntity(name='', status='active')
        errors = CustomerValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = CustomerEntity(name='test', status='invalid')
        errors = CustomerValidator.validate(entity)
        assert len(errors) > 0
