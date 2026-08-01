"""External prompt template registry.

Loads prompt templates from files with variable substitution.
Supports AGENT_SPEC.md for project-specific instructions.

Directory structure:
    prompts/
      system.md         # Base system prompt
      agent_spec.md     # Project-specific instructions (git-ignorable)
      roles/
        planner.md      # Planner role prompt
        coder.md        # Coder role prompt
        reviewer.md     # Reviewer role prompt
      templates/
        code_review.md  # Code review template
        refactoring.md  # Refactoring template
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from string import Template

logger = logging.getLogger(__name__)


class PromptRegistry:
    """Loads and manages prompt templates from files."""

    def __init__(self, prompts_dir: str = "prompts"):
        self._dir = Path(prompts_dir)
        self._cache: dict[str, str] = {}
        self._load_defaults()

    def _load_defaults(self):
        """Create default prompt directory and templates if they don't exist."""
        self._dir.mkdir(parents=True, exist_ok=True)

        roles_dir = self._dir / "roles"
        roles_dir.mkdir(exist_ok=True)

        templates_dir = self._dir / "templates"
        templates_dir.mkdir(exist_ok=True)

        system_file = self._dir / "system.md"
        if not system_file.exists():
            system_file.write_text(DEFAULT_SYSTEM_PROMPT)

        for name, content in DEFAULT_ROLE_PROMPTS.items():
            role_file = roles_dir / f"{name}.md"
            if not role_file.exists():
                role_file.write_text(content)

        for name, content in DEFAULT_TEMPLATES.items():
            tmpl_file = templates_dir / f"{name}.md"
            if not tmpl_file.exists():
                tmpl_file.write_text(content)

    def get(self, name: str, **variables) -> str:
        """Get a prompt template with variable substitution."""
        content = self._load(name)
        if variables:
            try:
                return Template(content).safe_substitute(variables)
            except Exception:
                return content
        return content

    def get_role(self, role_name: str, **variables) -> str:
        """Get a role-specific prompt."""
        return self.get(f"roles/{role_name}", **variables)

    def get_template(self, template_name: str, **variables) -> str:
        """Get a prompt template."""
        return self.get(f"templates/{template_name}", **variables)

    def load_agent_spec(self, path: str = "AGENT_SPEC.md") -> str:
        """Load project-specific agent instructions."""
        spec_file = Path(path)
        if spec_file.exists():
            content = spec_file.read_text(encoding="utf-8")
            logger.info("Loaded AGENT_SPEC.md (%d chars)", len(content))
            return content
        return ""

    def _load(self, name: str) -> str:
        """Load a prompt file with caching."""
        if name in self._cache:
            return self._cache[name]

        for search_path in [
            self._dir / f"{name}.md",
            self._dir / name,
            Path(f"{name}.md"),
        ]:
            if search_path.exists():
                content = search_path.read_text(encoding="utf-8")
                self._cache[name] = content
                return content

        logger.warning("Prompt template not found: %s", name)
        return ""

    def reload(self):
        """Clear cache and reload all templates."""
        self._cache.clear()

    def list_available(self) -> dict[str, list[str]]:
        """List all available prompt templates."""
        result: dict[str, list[str]] = {"roles": [], "templates": []}

        roles_dir = self._dir / "roles"
        if roles_dir.exists():
            result["roles"] = sorted(f.stem for f in roles_dir.glob("*.md"))

        templates_dir = self._dir / "templates"
        if templates_dir.exists():
            result["templates"] = sorted(f.stem for f in templates_dir.glob("*.md"))

        return result


DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant running locally. You help users with software development tasks.

## Core Principles
- Always verify actions before executing
- Prefer read-only operations unless asked to modify
- Report errors clearly and suggest fixes
- Write clean, well-structured code with type hints
- Follow the project's existing code style and conventions

## Project Context
- Working directory: $working_directory
- Project language: $language
- Framework: $framework

## Instructions
Follow the user's requests carefully. If something is unclear, ask for clarification.
"""

DEFAULT_ROLE_PROMPTS = {
    "planner": """You are a software planning assistant.

## Role
Break down complex tasks into actionable steps.

## Output Format
Return a numbered list of steps with:
1. Step description
2. Files that need to be modified
3. Expected outcome

## Guidelines
- Keep steps small and focused
- Consider dependencies between steps
- Identify potential risks
""",
    "coder": """You are a software development assistant.

## Role
Write clean, well-tested code.

## Guidelines
- Use type hints
- Follow existing code patterns
- Add docstrings for public functions
- Write tests for new functionality
- Keep functions focused (single responsibility)

## Code Style
- Follow PEP 8 (Python) or project conventions
- Use meaningful variable names
- Handle errors explicitly
""",
    "reviewer": """You are a code review assistant.

## Role
Review code for correctness, performance, and maintainability.

## Review Checklist
1. Logic correctness
2. Error handling
3. Performance considerations
4. Security implications
5. Code style consistency
6. Test coverage

## Output Format
- List issues with severity (critical/major/minor)
- Suggest specific fixes
- Acknowledge good practices
""",
}

DEFAULT_TEMPLATES = {
    "code_review": """Review the following code for:

1. **Correctness**: Does it work as intended?
2. **Performance**: Any bottlenecks or inefficiencies?
3. **Security**: Any vulnerabilities?
4. **Style**: Does it follow project conventions?

## Code to Review
$code

## Context
$context

Provide feedback with specific line references and suggested fixes.
""",
    "refactoring": """Refactor the following code to improve:

$code

## Goals
$goals

## Constraints
$constraints

Provide the refactored code with explanations of changes made.
""",
}
