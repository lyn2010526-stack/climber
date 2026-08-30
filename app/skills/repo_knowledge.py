"""Repo-level knowledge packs (OpenHands microagents style).

Skills with triggers are injected deterministically: a keyword in the user
message or a file path matching a glob pulls the skill's system_prompt into
context, without relying on the model to remember the skill exists.

Repo convention: ``<workspace>/.climber/skills/*.md`` files with optional
YAML frontmatter::

    ---
    name: Repo Rules
    description: Project conventions
    triggers: [deploy, 发布]
    paths: ["src/**"]
    ---
    Markdown body becomes the skill's system_prompt.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from app.skills.registry import SkillCategory, SkillInfo

if TYPE_CHECKING:
    from app.skills.registry import SkillRegistry

logger = structlog.get_logger()

# Path-like tokens: contain a slash or a known file extension.
_PATH_TOKEN = re.compile(r"[\w./-]*(?:/[\w./-]+)+|[\w.-]+\.(?:py|ts|tsx|js|jsx|go|rs|java|md|json|ya?ml|toml|sql|css|html)\b")


def extract_file_paths(text: str) -> list[str]:
    """Extract plausible file paths mentioned in free text."""
    seen: list[str] = []
    for match in _PATH_TOKEN.finditer(text):
        token = match.group(0).strip("./")
        if token and token not in seen:
            seen.append(token)
    return seen


def extract_paths_from_values(value: object) -> list[str]:
    """Extract file paths recursively from normalized tool arguments."""
    paths: list[str] = []
    if isinstance(value, str):
        paths.extend(extract_file_paths(value))
    elif isinstance(value, dict):
        for item in value.values():
            paths.extend(extract_paths_from_values(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            paths.extend(extract_paths_from_values(item))
    return list(dict.fromkeys(paths))


def parse_skill_markdown(raw: str, skill_id: str) -> SkillInfo:
    """Parse a markdown knowledge pack with optional YAML frontmatter."""
    meta: dict = {}
    body = raw
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            import yaml

            try:
                meta = yaml.safe_load(raw[3:end]) or {}
            except yaml.YAMLError:
                logger.warning("skill_frontmatter_invalid", skill_id=skill_id)
                meta = {}
            body = raw[end + 4:].lstrip("\n")

    return SkillInfo(
        id=skill_id,
        name=str(meta.get("name") or skill_id),
        description=str(meta.get("description") or ""),
        category=SkillCategory.KNOWLEDGE,
        system_prompt=body.strip(),
        triggers=[str(t) for t in meta.get("triggers") or []],
        path_triggers=[str(p) for p in meta.get("paths") or []],
        tags=["repo"],
    )


def load_repo_skills(registry: SkillRegistry, root: str | Path) -> int:
    """Load ``.climber/skills/*.md`` knowledge packs into the registry."""
    skills_dir = Path(root) / ".climber" / "skills"
    if not skills_dir.is_dir():
        return 0
    count = 0
    for path in sorted(skills_dir.glob("*.md")):
        try:
            skill = parse_skill_markdown(path.read_text(encoding="utf-8"), skill_id=path.stem)
        except OSError as e:
            logger.warning("skill_pack_load_failed", path=str(path), error=str(e))
            continue
        registry.register(skill)
        count += 1
    if count:
        logger.info("repo_skills_loaded", count=count, dir=str(skills_dir))
    return count
