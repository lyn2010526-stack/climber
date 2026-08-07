"""Tests for meter domain."""


from app.domains.meter_domain import (
    MeterEntity,
    MeterEntityFactory,
    MeterEntityRepository,
    MeterValidator,
)


class TestMeterEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = MeterEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = MeterEntityFactory.create('test')
        assert entity.name == 'test'


class TestMeterEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = MeterEntityRepository()
        entity = MeterEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = MeterEntityRepository()
        repo.save(MeterEntity(name='e1'))
        repo.save(MeterEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = MeterEntityRepository()
        entity = MeterEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = MeterEntityRepository()
        repo.save(MeterEntity(name='e1'))
        repo.save(MeterEntity(name='e2'))
        assert repo.count() == 2


class TestMeterValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = MeterEntity(name='test', status='active')
        assert MeterValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = MeterEntity(name='', status='active')
        errors = MeterValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = MeterEntity(name='test', status='invalid')
        errors = MeterValidator.validate(entity)
        assert len(errors) > 0
