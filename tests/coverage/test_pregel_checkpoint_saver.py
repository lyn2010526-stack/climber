"""Coverage tests for app.core.engine.pregel.checkpoint."""

from __future__ import annotations

from app.core.engine.pregel.checkpoint import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointConfig,
    InMemoryCheckpointSaver,
    SqliteCheckpointSaver,
    _generate_checkpoint_id,
)


class _FakeSaver:
    async def put(self, config: CheckpointConfig, checkpoint: Checkpoint) -> CheckpointConfig:
        return config

    async def get(self, config: CheckpointConfig) -> Checkpoint | None:
        return None

    async def list(
        self,
        config: CheckpointConfig,
        *,
        limit: int = 10,
        before: str | None = None,
    ) -> list[Checkpoint]:
        return []


def test_generate_checkpoint_id_shape_and_sortable() -> None:
    first = _generate_checkpoint_id()
    second = _generate_checkpoint_id()
    assert first.startswith("cp-")
    parts = first.split("-")
    assert len(parts) == 3
    assert len(parts[1]) == 24
    assert len(parts[2]) == 14
    assert second >= first


def test_checkpoint_to_dict_roundtrip() -> None:
    cp = Checkpoint(values={"a": 1}, next_nodes=["n"], step=2, metadata={"m": "x"})
    d = cp.to_dict()
    assert d["id"] == cp.id
    assert d["values"] == {"a": 1}
    assert d["next_nodes"] == ["n"]
    assert d["step"] == 2
    assert d["metadata"] == {"m": "x"}
    assert d["created_at"] == cp.created_at.isoformat()


def test_checkpoint_config_defaults() -> None:
    cfg = CheckpointConfig()
    assert cfg.thread_id == "default"
    assert cfg.checkpoint_id is None
    cfg2 = CheckpointConfig("t", "cp1")
    assert cfg2.thread_id == "t"
    assert cfg2.checkpoint_id == "cp1"


def test_base_checkpoint_saver_is_runtime_protocol() -> None:
    assert isinstance(_FakeSaver(), BaseCheckpointSaver)
    assert not isinstance(object(), BaseCheckpointSaver)


async def test_inmemory_put_get_by_id_and_latest() -> None:
    saver = InMemoryCheckpointSaver()
    cfg = CheckpointConfig(thread_id="t1")
    cp1 = Checkpoint(values={"n": 1}, step=1)
    cp2 = Checkpoint(values={"n": 2}, step=2)
    out1 = await saver.put(cfg, cp1)
    await saver.put(cfg, cp2)
    assert out1.checkpoint_id == cp1.id

    by_id = await saver.get(CheckpointConfig(thread_id="t1", checkpoint_id=cp1.id))
    assert by_id is cp1
    latest = await saver.get(cfg)
    assert latest is cp2
    assert await saver.get(CheckpointConfig(thread_id="missing")) is None


async def test_inmemory_list_limit_before_and_delete() -> None:
    saver = InMemoryCheckpointSaver()
    cfg = CheckpointConfig(thread_id="t")
    cps = []
    for i in range(5):
        cp = Checkpoint(values={"i": i}, step=i)
        cps.append(cp)
        await saver.put(cfg, cp)

    listed = await saver.list(cfg, limit=3)
    assert [c.step for c in listed] == [4, 3, 2]

    # before cursor: exclude the cursor itself and anything newer
    older = await saver.list(cfg, limit=10, before=cps[3].id)
    assert [c.step for c in older] == [2, 1, 0]

    # unknown cursor is a no-op filter
    all_cps = await saver.list(cfg, limit=10, before="unknown")
    assert len(all_cps) == 5

    deleted = await saver.delete_thread("t")
    assert deleted == 5
    assert await saver.get(cfg) is None
    assert await saver.delete_thread("nope") == 0


async def test_sqlite_checkpoint_saver_roundtrip(tmp_path) -> None:
    db = str(tmp_path / "cp.db")
    saver = SqliteCheckpointSaver(db_path=db)
    cfg = CheckpointConfig(thread_id="thread-a")
    cp = Checkpoint(
        values={"x": 1, "nested": {"y": 2}}, next_nodes=["a"], step=1, metadata={"k": "v"}
    )
    await saver.put(cfg, cp)

    by_id = await saver.get(CheckpointConfig(thread_id="thread-a", checkpoint_id=cp.id))
    assert by_id is not None
    assert by_id.values == {"x": 1, "nested": {"y": 2}}
    assert by_id.next_nodes == ["a"]
    assert by_id.metadata == {"k": "v"}

    latest = await saver.get(cfg)
    assert latest is not None and latest.id == cp.id
    assert await saver.get(CheckpointConfig(thread_id="none")) is None


async def test_sqlite_list_before_and_delete(tmp_path) -> None:
    saver = SqliteCheckpointSaver(db_path=str(tmp_path / "cp.db"))
    cfg = CheckpointConfig(thread_id="t")
    cps = []
    for i in range(4):
        cp = Checkpoint(values={"i": i}, step=i)
        cps.append(cp)
        await saver.put(cfg, cp)

    listed = await saver.list(cfg, limit=2)
    assert [c.step for c in listed] == [3, 2]

    older = await saver.list(cfg, limit=10, before=cps[3].id)
    assert [c.step for c in older] == [2, 1, 0]

    deleted = await saver.delete_thread("t")
    assert deleted == 4
    assert await saver.list(cfg) == []


async def test_sqlite_put_json_falls_back_to_str(tmp_path) -> None:
    saver = SqliteCheckpointSaver(db_path=str(tmp_path / "cp.db"))
    cfg = CheckpointConfig(thread_id="t")

    class _Unserializable:
        def __str__(self) -> str:  # pragma: no cover - trivial
            return "obj"

    cp = Checkpoint(values={"o": _Unserializable()}, metadata={"o": _Unserializable()})
    await saver.put(cfg, cp)
    loaded = await saver.get(CheckpointConfig(thread_id="t", checkpoint_id=cp.id))
    assert loaded is not None
    assert loaded.values["o"] == "obj"
    assert loaded.metadata["o"] == "obj"
