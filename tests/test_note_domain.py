"""Tests for note domain."""


from app.domains.note_domain import (
    NoteEntity,
    NoteEntityFactory,
    NoteEntityRepository,
    NoteValidator,
)


class TestNoteEntity:
    """Tests for entity."""

    def test_create_entity(self):
        entity = NoteEntity(name='test')
        assert entity.name == 'test'
        assert entity.status == 'active'

    def test_entity_factory(self):
        entity = NoteEntityFactory.create('test')
        assert entity.name == 'test'


class TestNoteEntityRepository:
    """Tests for repository."""

    def test_save_and_find(self):
        repo = NoteEntityRepository()
        entity = NoteEntity(name='test')
        repo.save(entity)
        result = repo.find_by_id(entity.id)
        assert result is not None
        assert result.name == 'test'

    def test_find_all(self):
        repo = NoteEntityRepository()
        repo.save(NoteEntity(name='e1'))
        repo.save(NoteEntity(name='e2'))
        results = repo.find_all()
        assert len(results) == 2

    def test_delete(self):
        repo = NoteEntityRepository()
        entity = NoteEntity(name='test')
        repo.save(entity)
        assert repo.delete(entity.id)
        result = repo.find_by_id(entity.id)
        assert result.is_deleted

    def test_count(self):
        repo = NoteEntityRepository()
        repo.save(NoteEntity(name='e1'))
        repo.save(NoteEntity(name='e2'))
        assert repo.count() == 2


class TestNoteValidator:
    """Tests for validator."""

    def test_valid_entity(self):
        entity = NoteEntity(name='test', status='active')
        assert NoteValidator.is_valid(entity)

    def test_invalid_name(self):
        entity = NoteEntity(name='', status='active')
        errors = NoteValidator.validate(entity)
        assert len(errors) > 0

    def test_invalid_status(self):
        entity = NoteEntity(name='test', status='invalid')
        errors = NoteValidator.validate(entity)
        assert len(errors) > 0
