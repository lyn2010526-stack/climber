"""Tests for payment domain."""


from app.domains.payment_domain import (
    PaymentEntity,
    PaymentEntityFactory,
    PaymentEntityRepository,
    PaymentValidator,
)


class TestPaymentEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = PaymentEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = PaymentEntityFactory.create('test')
        assert entity.name == 'test'


class TestPaymentEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = PaymentEntityRepository()
        entity = PaymentEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = PaymentEntityRepository()
        repo.save(PaymentEntity(name='e1'))
        repo.save(PaymentEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = PaymentEntityRepository()
        entity = PaymentEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = PaymentEntityRepository()
        repo.save(PaymentEntity(name='e1'))
        repo.save(PaymentEntity(name='e2'))
        assert repo.count() == 2


class TestPaymentValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = PaymentEntity(name='test', status='active')
        assert PaymentValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = PaymentEntity(name='', status='active')
        errors = PaymentValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = PaymentEntity(name='test', status='invalid')
        errors = PaymentValidator.validate(entity)
        assert len(errors) > 0
