"""Tests for skill package management."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.skills.package_manager import SkillPackageManager
from app.skills.skill_package import FailureStrategy, RiskLevel, SkillPackage


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    return tmp_path / "skills"


@pytest.fixture
def manager(skills_dir: Path) -> SkillPackageManager:
    return SkillPackageManager(skills_dir=skills_dir)


@pytest.fixture
def sample_package() -> SkillPackage:
    return SkillPackage(
        id="test-skill",
        name="Test Skill",
        description="A test skill package",
        version="1.0.0",
        author="test-author",
        category="engineering",
        system_prompt="You are a test skill.",
        tags=["test"],
        tools=["read_file"],
        risk_level=RiskLevel.LOW,
        max_iterations=5,
        timeout_seconds=60,
        failure_strategy=FailureStrategy.ASK_USER,
    )


class TestSkillPackage:
    def test_serialization_roundtrip(self, sample_package: SkillPackage) -> None:
        json_str = sample_package.to_json()
        restored = SkillPackage.from_json(json_str)
        assert restored.id == sample_package.id
        assert restored.name == sample_package.name
        assert restored.risk_level == RiskLevel.LOW
        assert restored.max_iterations == 5

    def test_from_dict(self, sample_package: SkillPackage) -> None:
        data = sample_package.to_dict()
        restored = SkillPackage.from_dict(data)
        assert restored.id == sample_package.id

    def test_validate_empty_id(self) -> None:
        pkg = SkillPackage(id="", name="x", description="d", system_prompt="y")
        issues = pkg.validate_package()
        assert any("id" in i for i in issues)

    def test_validate_missing_prompt(self) -> None:
        pkg = SkillPackage(id="x", name="y", description="d", system_prompt="  ")
        issues = pkg.validate_package()
        assert any("system_prompt" in i for i in issues)

    def test_validate_restricted_requires_admin(self) -> None:
        pkg = SkillPackage(
            id="x", name="y", description="d", system_prompt="z",
            risk_level=RiskLevel.RESTRICTED,
        )
        pkg.validate_package()
        assert pkg.requires_admin is True

    def test_save_and_load(self, sample_package: SkillPackage, tmp_path: Path) -> None:
        path = tmp_path / "test.skill.json"
        sample_package.save_to_file(path)
        assert path.exists()
        loaded = SkillPackage.from_file(path)
        assert loaded.id == sample_package.id

    def test_from_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            SkillPackage.from_file(tmp_path / "nonexistent.json")


class TestSkillPackageManager:
    def test_install_from_file(
        self, manager: SkillPackageManager, sample_package: SkillPackage, tmp_path: Path
    ) -> None:
        pkg_path = tmp_path / "test.skill.json"
        sample_package.save_to_file(pkg_path)
        ok, msg = manager.install_from_file(pkg_path)
        assert ok is True
        assert "Installed" in msg

    def test_install_duplicate_no_overwrite(
        self, manager: SkillPackageManager, sample_package: SkillPackage, tmp_path: Path
    ) -> None:
        pkg_path = tmp_path / "test.skill.json"
        sample_package.save_to_file(pkg_path)
        manager.install_from_file(pkg_path)
        ok, msg = manager.install_from_file(pkg_path)
        assert ok is False
        assert "already installed" in msg

    def test_install_overwrite(
        self, manager: SkillPackageManager, sample_package: SkillPackage, tmp_path: Path
    ) -> None:
        pkg_path = tmp_path / "test.skill.json"
        sample_package.save_to_file(pkg_path)
        manager.install_from_file(pkg_path)
        ok, _msg = manager.install_from_file(pkg_path, overwrite=True)
        assert ok is True

    def test_list_installed(
        self, manager: SkillPackageManager, sample_package: SkillPackage, tmp_path: Path
    ) -> None:
        pkg_path = tmp_path / "test.skill.json"
        sample_package.save_to_file(pkg_path)
        manager.install_from_file(pkg_path)
        installed = manager.list_installed()
        assert len(installed) == 1
        assert installed[0]["id"] == "test-skill"

    def test_uninstall(
        self, manager: SkillPackageManager, sample_package: SkillPackage, tmp_path: Path
    ) -> None:
        pkg_path = tmp_path / "test.skill.json"
        sample_package.save_to_file(pkg_path)
        manager.install_from_file(pkg_path)
        ok, _msg = manager.uninstall("test-skill")
        assert ok is True
        assert manager.list_installed() == []

    def test_uninstall_not_found(self, manager: SkillPackageManager) -> None:
        ok, _msg = manager.uninstall("nonexistent")
        assert ok is False

    def test_get(
        self, manager: SkillPackageManager, sample_package: SkillPackage, tmp_path: Path
    ) -> None:
        pkg_path = tmp_path / "test.skill.json"
        sample_package.save_to_file(pkg_path)
        manager.install_from_file(pkg_path)
        pkg = manager.get("test-skill")
        assert pkg is not None
        assert pkg.id == "test-skill"

    def test_get_missing(self, manager: SkillPackageManager) -> None:
        assert manager.get("nonexistent") is None

    def test_registry_persistence(
        self, skills_dir: Path, sample_package: SkillPackage, tmp_path: Path
    ) -> None:
        pkg_path = tmp_path / "test.skill.json"
        sample_package.save_to_file(pkg_path)
        m1 = SkillPackageManager(skills_dir=skills_dir)
        m1.install_from_file(pkg_path)
        m2 = SkillPackageManager(skills_dir=skills_dir)
        assert len(m2.list_installed()) == 1
