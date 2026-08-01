"""Skill package import/export.

"""

from __future__ import annotations

import json
import logging
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SkillPackage:
    skill_id: str
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    tags: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    files: dict[str, str] = field(default_factory=dict)  # path -> content
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SkillPackageManager:
    """Manage skill package import/export.

    """

    def __init__(self, storage_path: str = "./data/skill_packages"):
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)

    def create_package(self, skill_id: str, source_dir: str) -> SkillPackage:
        source = Path(source_dir)
        files: dict[str, str] = {}
        for path in source.rglob("*"):
            if path.is_file():
                rel = str(path.relative_to(source))
                files[rel] = path.read_text(encoding="utf-8")
        return SkillPackage(
            skill_id=skill_id,
            name=skill_id,
            description=f"Exported from {source_dir}",
            files=files,
        )

    def export_package(self, skill_id: str, output_path: str) -> str:
        package = self._load_from_registry(skill_id)
        if not package:
            raise ValueError(f"Skill not found: {skill_id}")
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            manifest = {
                "skill_id": package.skill_id,
                "name": package.name,
                "description": package.description,
                "version": package.version,
                "author": package.author,
                "tags": package.tags,
                "config": package.config,
                "created_at": package.created_at.isoformat(),
            }
            zf.writestr("skill.json", json.dumps(manifest, indent=2, ensure_ascii=False))
            for rel_path, content in package.files.items():
                zf.writestr(f"files/{rel_path}", content)
        with open(output_path, "wb") as f:
            f.write(buffer.getvalue())
        return output_path

    def import_package(self, package_path: str) -> SkillPackage:
        with zipfile.ZipFile(package_path, "r") as zf:
            manifest = json.loads(zf.read("skill.json").decode("utf-8"))
            files: dict[str, str] = {}
            for name in zf.namelist():
                if name.startswith("files/"):
                    rel = name[len("files/"):]
                    files[rel] = zf.read(name).decode("utf-8")
            package = SkillPackage(
                skill_id=manifest["skill_id"],
                name=manifest["name"],
                description=manifest.get("description", ""),
                version=manifest.get("version", "1.0.0"),
                author=manifest.get("author", ""),
                tags=manifest.get("tags", []),
                config=manifest.get("config", {}),
                files=files,
                created_at=datetime.fromisoformat(manifest.get("created_at", datetime.now(timezone.utc).isoformat())),
            )
        self._save_to_registry(package)
        return package

    def _load_from_registry(self, skill_id: str) -> SkillPackage | None:
        path = self._storage_path / f"{skill_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return SkillPackage(**data)

    def _save_to_registry(self, package: SkillPackage) -> None:
        path = self._storage_path / f"{package.skill_id}.json"
        data = {
            "skill_id": package.skill_id,
            "name": package.name,
            "description": package.description,
            "version": package.version,
            "author": package.author,
            "tags": package.tags,
            "config": package.config,
            "files": package.files,
            "created_at": package.created_at.isoformat(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


skill_package_manager = SkillPackageManager()
