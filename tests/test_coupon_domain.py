"""Tests for coupon domain."""


from app.domains.coupon_domain import (
    CouponEntity,
    CouponEntityFactory,
    CouponEntityRepository,
    CouponValidator,
)


class TestCouponEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = CouponEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = CouponEntityFactory.create('test')
        assert entity.name == 'test'


class TestCouponEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = CouponEntityRepository()
        entity = CouponEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = CouponEntityRepository()
        repo.save(CouponEntity(name='e1'))
        repo.save(CouponEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = CouponEntityRepository()
        entity = CouponEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = CouponEntityRepository()
        repo.save(CouponEntity(name='e1'))
        repo.save(CouponEntity(name='e2'))
        assert repo.count() == 2


class TestCouponValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = CouponEntity(name='test', status='active')
        assert CouponValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = CouponEntity(name='', status='active')
        errors = CouponValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = CouponEntity(name='test', status='invalid')
        errors = CouponValidator.validate(entity)
        assert len(errors) > 0
