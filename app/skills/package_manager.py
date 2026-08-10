"""Local skill package manager.

Handles installation, uninstallation, updating, and listing of skill packages.
Packages are stored in the skills/ directory as .skill.json files.
"""

from __future__ import annotations

import json
from datetime import UTC
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import structlog

from app.skills.skill_package import RiskLevel, SkillPackage

logger = structlog.get_logger()

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "skills"
INSTALLED_REGISTRY = SKILLS_DIR / ".installed.json"


class SkillPackageManager:
    """Manages local skill package lifecycle."""

    def __init__(self, skills_dir: Path | None = None) -> None:
        self._dir = skills_dir or SKILLS_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._registry_path = self._dir / ".installed.json"
        self._installed = self._load_registry()

    # ── registry ──────────────────────────────────────────────────────────────

    def _load_registry(self) -> dict[str, dict[str, Any]]:
        if self._registry_path.exists():
            try:
                return json.loads(self._registry_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_registry(self) -> None:
        self._registry_path.write_text(
            json.dumps(self._installed, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── list ──────────────────────────────────────────────────────────────────

    def list_installed(self) -> list[dict[str, Any]]:
        """List all installed skills with metadata."""
        result = []
        for skill_id, meta in self._installed.items():
            pkg_path = self._dir / f"{skill_id}.skill.json"
            if pkg_path.exists():
                try:
                    pkg = SkillPackage.from_file(pkg_path)
                    result.append({
                        "id": pkg.id,
                        "name": pkg.name,
                        "version": pkg.version,
                        "category": pkg.category,
                        "risk_level": pkg.risk_level.value,
                        "requires_admin": pkg.requires_admin,
                        "installed_at": meta.get("installed_at", ""),
                        "source": meta.get("source", "local"),
                    })
                except Exception as e:
                    logger.warning("skill_list_error", skill_id=skill_id, error=str(e))
        return result

    # ── install ───────────────────────────────────────────────────────────────

    def requires_admin(self, pkg: SkillPackage) -> bool:
        """Check if a skill requires admin privileges to install/enable."""
        return pkg.risk_level in (RiskLevel.HIGH, RiskLevel.RESTRICTED) or pkg.requires_admin

    def install_from_file(
        self, path: Path | str, *, overwrite: bool = False, is_admin: bool = False,
    ) -> tuple[bool, str]:
        """Install a skill from a local .skill.json file."""
        try:
            pkg = SkillPackage.from_file(path)
        except FileNotFoundError:
            return False, f"File not found: {path}"
        except Exception as e:
            return False, f"Invalid skill package: {e}"

        issues = pkg.validate_package()
        if issues:
            return False, f"Validation failed: {'; '.join(issues)}"

        if self.requires_admin(pkg) and not is_admin:
            return False, (
                f"Skill '{pkg.id}' has risk level '{pkg.risk_level.value}' and requires "
                f"admin privileges to install. Use --admin flag."
            )

        dest = self._dir / f"{pkg.id}.skill.json"
        if dest.exists() and not overwrite:
            return False, f"Skill '{pkg.id}' already installed. Use overwrite=True to replace."

        pkg.save_to_file(dest)
        from datetime import datetime
        self._installed[pkg.id] = {
            "version": pkg.version,
            "installed_at": datetime.now(UTC).isoformat(),
            "source": "local",
            "risk_level": pkg.risk_level.value,
        }
        self._save_registry()
        logger.info("skill_installed", skill_id=pkg.id, version=pkg.version)
        return True, f"Installed '{pkg.name}' v{pkg.version}"

    def install_from_url(
        self, url: str, *, overwrite: bool = False, is_admin: bool = False,
    ) -> tuple[bool, str]:
        """Download and install a skill from a URL."""
        import httpx

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, f"Unsupported URL scheme: {parsed.scheme}"

        try:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.text
        except Exception as e:
            return False, f"Download failed: {e}"

        try:
            pkg = SkillPackage.from_json(data)
        except Exception as e:
            return False, f"Invalid skill package from URL: {e}"

        issues = pkg.validate_package()
        if issues:
            return False, f"Validation failed: {'; '.join(issues)}"

        if self.requires_admin(pkg) and not is_admin:
            return False, (
                f"Skill '{pkg.id}' has risk level '{pkg.risk_level.value}' and requires "
                f"admin privileges to install. Use --admin flag."
            )

        dest = self._dir / f"{pkg.id}.skill.json"
        if dest.exists() and not overwrite:
            return False, f"Skill '{pkg.id}' already installed. Use overwrite=True to replace."

        pkg.save_to_file(dest)
        from datetime import datetime
        self._installed[pkg.id] = {
            "version": pkg.version,
            "installed_at": datetime.now(UTC).isoformat(),
            "source": url,
            "risk_level": pkg.risk_level.value,
        }
        self._save_registry()
        logger.info("skill_installed_from_url", skill_id=pkg.id, url=url)
        return True, f"Installed '{pkg.name}' v{pkg.version} from URL"

    # ── uninstall ─────────────────────────────────────────────────────────────

    def uninstall(self, skill_id: str) -> tuple[bool, str]:
        """Remove an installed skill."""
        dest = self._dir / f"{skill_id}.skill.json"
        if not dest.exists():
            return False, f"Skill '{skill_id}' is not installed"

        dest.unlink()
        self._installed.pop(skill_id, None)
        self._save_registry()
        logger.info("skill_uninstalled", skill_id=skill_id)
        return True, f"Uninstalled '{skill_id}'"

    # ── update ────────────────────────────────────────────────────────────────

    def update(self, skill_id: str, *, path: str | None = None, url: str | None = None) -> tuple[bool, str]:
        """Update an installed skill from file or url."""
        if skill_id not in self._installed:
            return False, f"Skill '{skill_id}' is not installed"

        if path:
            ok, msg = self.install_from_file(path, overwrite=True)
        elif url:
            ok, msg = self.install_from_url(url, overwrite=True)
        else:
            return False, "Must provide either path or url"

        if ok:
            logger.info("skill_updated", skill_id=skill_id)
        return ok, msg

    # ── get ───────────────────────────────────────────────────────────────────

    def get(self, skill_id: str) -> SkillPackage | None:
        """Get a specific installed skill package."""
        dest = self._dir / f"{skill_id}.skill.json"
        if dest.exists():
            try:
                return SkillPackage.from_file(dest)
            except Exception:
                return None
        return None

    def get_all(self) -> list[SkillPackage]:
        """Get all installed skill packages."""
        result = []
        for skill_id in self._installed:
            pkg = self.get(skill_id)
            if pkg:
                result.append(pkg)
        return result


_manager: SkillPackageManager | None = None


def get_skill_manager() -> SkillPackageManager:
    global _manager
    if _manager is None:
        _manager = SkillPackageManager()
    return _manager
