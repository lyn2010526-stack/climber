"""Skill market — export/import skills as single .skill files (zip).

Skills are exported as a zip-packaged skill directory. Importing scans for
safety: declared sensitive permission requests require explicit user approval
before the skill is installed.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.skill_store.skill_store import METADATA_JSON, SKILL_MD, Skill, SkillMetadata

SENSITIVE_PERMISSIONS = ("network", "screenshot", "file_write", "device_control", "shell")


@dataclass
class ImportScanResult:
    skill_id: str
    safe: bool
    sensitive_permissions: list[str] = field(default_factory=list)
    requires_confirmation: bool = False


class SkillMarket:
    """Pack, unpack, and safely import .skill files."""

    def __init__(self, store: Any, market_dir: str | Path = "data/skill_market") -> None:
        self._store = store
        self._market_dir = Path(market_dir)
        self._market_dir.mkdir(parents=True, exist_ok=True)

    def export_skill(self, skill_id: str, output_path: str | None = None) -> Path:
        """Package a skill directory into a single .skill zip file."""
        skill = self._store.get(skill_id)
        if skill is None:
            raise FileNotFoundError(f"skill not found: {skill_id}")
        if output_path is None:
            output_path = str(self._market_dir / f"{skill_id}.skill")
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(METADATA_JSON, json.dumps(skill.metadata.to_dict(), ensure_ascii=False))
            zf.writestr(SKILL_MD, skill.load_instruction())
            for ref in skill.list_references():
                zf.writestr(f"{skill.path.name}/{ref}", skill.read_reference(ref))
        return out

    def scan_package(self, package_path: str | Path) -> ImportScanResult:
        """Scan an imported .skill file for safety before installation."""
        with zipfile.ZipFile(package_path, "r") as zf:
            manifest_raw = zf.read(METADATA_JSON).decode("utf-8")
        meta = SkillMetadata.from_dict(json.loads(manifest_raw))
        sensitive = [p for p in SENSITIVE_PERMISSIONS if p in json.dumps(meta.to_dict()).lower()]
        declared = list(sensitive)
        return ImportScanResult(
            skill_id=meta.name,
            safe=not declared,
            sensitive_permissions=declared,
            requires_confirmation=bool(declared),
        )

    def import_skill(
        self,
        package_path: str | Path,
        approved: bool = False,
    ) -> ImportScanResult | Skill:
        """Import a .skill file.

        When the package requests sensitive permissions and ``approved`` is
        False, the scan result is returned instead of installing.
        """
        scan = self.scan_package(package_path)
        if scan.requires_confirmation and not approved:
            return scan
        with zipfile.ZipFile(package_path, "r") as zf:
            manifest_raw = zf.read(METADATA_JSON).decode("utf-8")
            meta = SkillMetadata.from_dict(json.loads(manifest_raw))
            instruction = zf.read(SKILL_MD).decode("utf-8")
            references: dict[str, bytes] = {}
            prefix = f"{meta.name}/"
            for name in zf.namelist():
                if name.startswith(prefix) and name not in (METADATA_JSON, SKILL_MD):
                    references[name[len(prefix):]] = zf.read(name)
        return self._store.create(meta.name, meta, instruction, references or None)


_default_market: SkillMarket | None = None


def get_skill_market(store: Any = None) -> SkillMarket:
    global _default_market
    if _default_market is None or store is not None:
        from app.core.skill_store.skill_store import get_skill_store

        _default_market = SkillMarket(store or get_skill_store())
    return _default_market
