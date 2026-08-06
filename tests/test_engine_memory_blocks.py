"""Tests for memory blocks system."""


from app.core.engine.memory_blocks import (
    BlockType,
    EntityExtractor,
    MemoryBlock,
    MemoryBlockStore,
    MemoryConsolidator,
    PassageRecord,
)


class TestMemoryBlock:
    def test_creation(self) -> None:
        block = MemoryBlock(label="user_name", value="Alice")
        assert block.label == "user_name"
        assert block.value == "Alice"
        assert block.read_only is False

    def test_update(self) -> None:
        block = MemoryBlock(label="pref", value="old")
        assert block.update("new") is True
        assert block.value == "new"

    def test_update_read_only(self) -> None:
        block = MemoryBlock(label="core", value="fixed", read_only=True)
        assert block.update("new") is False
        assert block.value == "fixed"

    def test_update_limit(self) -> None:
        block = MemoryBlock(label="short", value="", limit=10)
        block.update("x" * 20)
        assert len(block.value) == 10

    def test_to_dict(self) -> None:
        block = MemoryBlock(label="test", value="val", block_type=BlockType.USER)
        d = block.to_dict()
        assert d["label"] == "test"
        assert d["block_type"] == "user"
        assert d["read_only"] is False


class TestMemoryBlockStore:
    def test_add_and_get(self) -> None:
        store = MemoryBlockStore()
        block = MemoryBlock(label="name", value="Alice")
        store.add_block(block)
        retrieved = store.get_block("name")
        assert retrieved is not None
        assert retrieved.value == "Alice"

    def test_update_block(self) -> None:
        store = MemoryBlockStore()
        store.add_block(MemoryBlock(label="pref", value="old"))
        assert store.update_block("pref", "new") is True
        assert store.get_block("pref").value == "new"

    def test_remove_block(self) -> None:
        store = MemoryBlockStore()
        store.add_block(MemoryBlock(label="temp", value="data"))
        assert store.remove_block("temp") is True
        assert store.get_block("temp") is None

    def test_remove_read_only(self) -> None:
        store = MemoryBlockStore()
        store.add_block(MemoryBlock(label="core", value="fixed", read_only=True))
        assert store.remove_block("core") is False

    def test_list_blocks_by_type(self) -> None:
        store = MemoryBlockStore()
        store.add_block(MemoryBlock(label="c1", value="v", block_type=BlockType.CORE))
        store.add_block(MemoryBlock(label="u1", value="v", block_type=BlockType.USER))
        store.add_block(MemoryBlock(label="u2", value="v", block_type=BlockType.USER))
        user_blocks = store.list_blocks(BlockType.USER)
        assert len(user_blocks) == 2

    def test_compile_prompt(self) -> None:
        store = MemoryBlockStore()
        store.add_block(MemoryBlock(label="user_name", value="Alice"))
        store.add_block(MemoryBlock(label="language", value="English"))
        prompt = store.compile_prompt()
        assert "user_name" in prompt
        assert "Alice" in prompt
        assert "language" in prompt

    def test_compile_prompt_empty(self) -> None:
        store = MemoryBlockStore()
        assert store.compile_prompt() == ""

    def test_compile_prompt_filtered(self) -> None:
        store = MemoryBlockStore()
        store.add_block(MemoryBlock(label="c1", value="v", block_type=BlockType.CORE))
        store.add_block(MemoryBlock(label="u1", value="v", block_type=BlockType.USER))
        prompt = store.compile_prompt(include_types=[BlockType.CORE])
        assert "c1" in prompt
        assert "u1" not in prompt

    def test_add_passage(self) -> None:
        store = MemoryBlockStore()
        pid = store.add_passage("important info", source="conversation")
        assert len(pid) == 12
        assert len(store._archive) == 1

    def test_search_archive(self) -> None:
        store = MemoryBlockStore()
        store.add_passage("Python is a great programming language")
        store.add_passage("JavaScript is used for web development")
        store.add_passage("Python has excellent libraries")
        results = store.search_archive("Python")
        assert len(results) >= 1

    def test_get_stats(self) -> None:
        store = MemoryBlockStore()
        store.add_block(MemoryBlock(label="c1", value="v", block_type=BlockType.CORE))
        store.add_block(MemoryBlock(label="u1", value="v", block_type=BlockType.USER))
        stats = store.get_stats()
        assert stats["total_blocks"] == 2
        assert "core" in stats["type_distribution"]


class TestEntityExtractor:
    def test_extract_email(self) -> None:
        text = "Contact us at hello@example.com for info"
        entities = EntityExtractor.extract(text)
        assert "email" in entities
        assert "hello@example.com" in entities["email"]

    def test_extract_url(self) -> None:
        text = "Visit https://example.com/page for details"
        entities = EntityExtractor.extract(text)
        assert "url" in entities

    def test_extract_date(self) -> None:
        text = "The event is on 2026-07-30"
        entities = EntityExtractor.extract(text)
        assert "date" in entities
        assert "2026-07-30" in entities["date"]

    def test_extract_empty(self) -> None:
        entities = EntityExtractor.extract("")
        assert len(entities) == 0

    def test_extract_to_block(self) -> None:
        text = "Email alice@example.com or visit https://example.com"
        block = EntityExtractor.extract_to_block(text)
        assert block.block_type == BlockType.ENTITY
        assert "email" in block.value.lower() or "url" in block.value.lower()


class TestMemoryConsolidator:
    def test_consolidate_prunes_empty(self) -> None:
        store = MemoryBlockStore()
        store.add_block(MemoryBlock(label="empty", value="   "))
        store.add_block(MemoryBlock(label="valid", value="data"))
        consolidator = MemoryConsolidator(store)
        report = consolidator.consolidate()
        assert report["blocks_pruned"] == 1
        assert store.get_block("empty") is None

    def test_consolidate_keeps_read_only(self) -> None:
        store = MemoryBlockStore()
        store.add_block(MemoryBlock(label="core", value="   ", read_only=True))
        consolidator = MemoryConsolidator(store)
        consolidator.consolidate()
        assert store.get_block("core") is not None

    def test_detect_stale_blocks(self) -> None:
        import time
        store = MemoryBlockStore()
        block = MemoryBlock(label="old", value="data")
        block.updated_at = time.monotonic() - 86400 * 40  # 40 days ago
        store.add_block(block)
        consolidator = MemoryConsolidator(store)
        stale = consolidator.detect_stale_blocks()
        assert "old" in stale


class TestPassageRecord:
    def test_creation(self) -> None:
        record = PassageRecord(content="test content", source="test")
        assert record.content == "test content"
        assert record.source == "test"
        assert len(record.passage_id) == 12
