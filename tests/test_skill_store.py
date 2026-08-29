"""Tests for skill store (three-level loading) + skill market."""

from __future__ import annotations

from app.core.skill_store import SkillMetadata, SkillStore
from app.core.skill_store.skill_market import SkillMarket


def test_skill_create_and_three_levels(tmp_path):
    store = SkillStore(base_dir=str(tmp_path / "skills"))
    meta = SkillMetadata(name="test_skill", description="A test skill", tags=["test"], status="active")
    skill = store.create("test_skill", meta, "Step 1: do x\nStep 2: do y", references={"logo.png": b"pngdata"})
    assert skill.skill_id == "test_skill"
    assert skill.load_instruction() == "Step 1: do x\nStep 2: do y"
    assert skill.list_references() == ["logo.png"]
    assert skill.read_reference("logo.png") == b"pngdata"

    meta_payload = skill.to_metadata_payload()
    assert meta_payload["name"] == "test_skill"
    assert meta_payload["description"] == "A test skill"


def test_skill_metadata_index(tmp_path):
    store = SkillStore(base_dir=str(tmp_path / "skills2"))
    store.create("s1", SkillMetadata(name="s1", description="desc1"), "instr1")
    store.create("s2", SkillMetadata(name="s2", description="desc2"), "instr2")
    idx = store.metadata_index()
    assert len(idx) == 2
    names = [i["name"] for i in idx]
    assert "s1" in names
    assert "s2" in names


def test_skill_record_usage(tmp_path):
    store = SkillStore(base_dir=str(tmp_path / "skills3"))
    store.create("s1", SkillMetadata(name="s1", description="desc1", status="active"), "instr")
    store.record_usage("s1", success=True, duration_ms=100)
    skill = store.get("s1")
    assert skill.metadata.use_count == 1
    assert skill.metadata.success_rate == 1.0
    store.record_usage("s1", success=False, duration_ms=200)
    skill = store.get("s1")
    assert skill.metadata.use_count == 2
    assert skill.metadata.success_rate < 0.6


def test_skill_market_export_import_scan(tmp_path):
    store = SkillStore(base_dir=str(tmp_path / "skills4"))
    store.create("market_skill", SkillMetadata(name="market_skill", description="market"), "do stuff")
    market = SkillMarket(store=store, market_dir=str(tmp_path / "market"))
    exported = market.export_skill("market_skill", output_path=str(tmp_path / "market" / "test.skill"))
    assert exported.exists()

    scan = market.scan_package(str(tmp_path / "market" / "test.skill"))
    assert scan.skill_id == "market_skill"
    assert scan.safe

    imported = market.import_skill(str(tmp_path / "market" / "test.skill"), approved=True)
    assert imported.skill_id == "market_skill"
