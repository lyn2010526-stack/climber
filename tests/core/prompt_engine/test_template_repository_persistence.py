"""Tests for prompt template repository persistence."""

import json
import threading

from app.core.prompt_engine.template_repository import PromptTemplateRepository


def test_create_persists_and_new_instance_reads_back(tmp_path):
    path = tmp_path / "templates.json"
    repo = PromptTemplateRepository(path)
    tpl = repo.create("persisted", "hello {{name}}", tags=["test"])
    assert repo.get(tpl.id) is not None

    fresh = PromptTemplateRepository(path)
    loaded = fresh.get(tpl.id)
    assert loaded is not None
    assert loaded.name == "persisted"
    assert loaded.content == "hello {{name}}"
    assert loaded.tags == ["test"]
    assert loaded.is_builtin is False


def test_delete_persists_removal(tmp_path):
    path = tmp_path / "templates.json"
    repo = PromptTemplateRepository(path)
    tpl = repo.create("doomed", "content")
    assert repo.delete(tpl.id) is True

    fresh = PromptTemplateRepository(path)
    assert fresh.get(tpl.id) is None


def test_update_persists(tmp_path):
    path = tmp_path / "templates.json"
    repo = PromptTemplateRepository(path)
    tpl = repo.create("editable", "v1")
    repo.update(tpl.id, content="v2")

    fresh = PromptTemplateRepository(path)
    assert fresh.get(tpl.id).content == "v2"


def test_import_persists(tmp_path):
    path = tmp_path / "templates.json"
    repo = PromptTemplateRepository(path)
    tpl = repo.import_template(json.dumps({"name": "imported", "content": "body"}))
    assert tpl is not None

    fresh = PromptTemplateRepository(path)
    loaded = fresh.get(tpl.id)
    assert loaded is not None
    assert loaded.name == "imported"


def test_builtins_are_not_persisted(tmp_path):
    path = tmp_path / "templates.json"
    repo = PromptTemplateRepository(path)
    tpl = repo.create("custom", "x")

    fresh = PromptTemplateRepository(path)
    assert any(t.is_builtin for t in fresh.list_builtins())
    assert [t.id for t in fresh.list_custom()] == [tpl.id]


def test_missing_file_yields_empty_custom_repo(tmp_path):
    repo = PromptTemplateRepository(tmp_path / "missing.json")
    assert repo.list_custom() == []


def test_corrupt_file_degrades_to_empty(tmp_path):
    path = tmp_path / "templates.json"
    path.write_text("{ not json !!!")
    repo = PromptTemplateRepository(path)
    assert repo.list_custom() == []


def test_unwritable_path_degrades_to_in_memory(tmp_path):
    repo = PromptTemplateRepository(tmp_path / "no_dir" / "templates.json")
    tpl = repo.create("mem", "content")
    assert repo.get(tpl.id) is not None


def test_no_path_runs_without_crash(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    repo = PromptTemplateRepository()
    tpl = repo.create("mem", "content")
    assert repo.get(tpl.id) is not None
    repo.delete(tpl.id)
    assert repo.get(tpl.id) is None
    assert (tmp_path / ".climber" / "templates.json").exists()


def test_concurrent_creates_are_safe(tmp_path):
    path = tmp_path / "templates.json"
    repo = PromptTemplateRepository(path)
    ids = []
    barrier = threading.Barrier(5)

    def worker():
        barrier.wait()
        ids.append(repo.create("t", "c").id)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(ids) == 5
    assert len(repo.list_custom()) == 5
    assert len(PromptTemplateRepository(path).list_custom()) == 5
