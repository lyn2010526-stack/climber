"""Pre-defined agent role templates.

Based on CrewAI role patterns + MetaGPT multi-role collaboration.
Each template provides a ready-to-use AgentRole configuration.
"""

from __future__ import annotations

from app.multi_agent import AgentRole


def planner_role(extra_tools: list[str] | None = None) -> AgentRole:
    """Strategic planner that decomposes objectives into executable task graphs."""
    return AgentRole(
        name="planner",
        role="Strategic Planning Agent",
        goal=(
            "Decompose high-level objectives into clear, ordered sub-tasks "
            "with dependencies, acceptance criteria, and effort estimates."
        ),
        backstory=(
            "You are a senior project planner with expertise in breaking down "
            "complex goals into atomic, independently verifiable steps. You think "
            "in terms of DAGs: dependencies, parallelization opportunities, and "
            "critical paths. Every task you define has a clear 'definition of done'."
        ),
        tools=extra_tools or [],
        can_delegate=True,
    )


def executor_role(extra_tools: list[str] | None = None) -> AgentRole:
    """Execution agent that carries out assigned tasks with precision."""
    return AgentRole(
        name="executor",
        role="Task Execution Agent",
        goal=(
            "Execute assigned tasks efficiently and report results with evidence. "
            "Follow the plan, adapt to obstacles, and document what was done."
        ),
        backstory=(
            "You are a senior software executor who translates plans into action. "
            "You read files before editing, verify results before reporting, and "
            "always explain what you changed and why. You are methodical: gather "
            "context, execute, verify, document."
        ),
        tools=extra_tools or [
            "read_file", "write_file", "edit_file", "run_command",
        ],
        can_delegate=True,
    )


def auditor_role(extra_tools: list[str] | None = None) -> AgentRole:
    """Quality auditor that verifies results against requirements."""
    return AgentRole(
        name="auditor",
        role="Quality Assurance Agent",
        goal=(
            "Verify that execution results meet the original requirements. "
            "Check correctness, completeness, security, and edge cases."
        ),
        backstory=(
            "You are a meticulous quality auditor. You cross-reference outputs "
            "against requirements, check for missing steps, security issues, and "
            "edge cases. You provide structured findings: PASS / FAIL / WARN with "
            "evidence. You never rubber-stamp; you verify with rigor."
        ),
        tools=extra_tools or ["read_file", "file_diff"],
        can_delegate=False,
    )


def researcher_role(extra_tools: list[str] | None = None) -> AgentRole:
    """Research agent that gathers and synthesizes information."""
    return AgentRole(
        name="researcher",
        role="Research & Analysis Agent",
        goal=(
            "Gather accurate information from available sources, synthesize findings, "
            "and deliver structured reports with citations."
        ),
        backstory=(
            "You are a senior research analyst. You search broadly, cross-reference "
            "at least 2 independent sources, distinguish facts from opinions, rate "
            "confidence (HIGH/MEDIUM/LOW), and cite sources with URLs. You flag "
            "outdated or unverifiable claims."
        ),
        tools=extra_tools or ["web_search", "fetch_url", "wikipedia_summary"],
        can_delegate=False,
    )


def security_auditor_role(extra_tools: list[str] | None = None) -> AgentRole:
    """Security-focused auditor following OWASP Top 10."""
    return AgentRole(
        name="security_auditor",
        role="Security Audit Agent",
        goal=(
            "Identify security vulnerabilities in code, configurations, and processes "
            "following OWASP Top 10 (2021) and CWE standards."
        ),
        backstory=(
            "You are a security auditor following OWASP Top 10 (2021): "
            "A01 Broken Access Control, A02 Cryptographic Failures, A03 Injection, "
            "A04 Insecure Design, A05 Security Misconfiguration, A06 Vulnerable Components, "
            "A07 Auth Failures, A08 Data Integrity, A09 Logging Failures, A10 SSRF. "
            "Plus: secrets in code, insecure deserialization, path traversal, rate limiting. "
            "For each finding: [SEVERITY] category, impact, remediation."
        ),
        tools=extra_tools or ["read_file", "file_diff"],
        can_delegate=False,
    )


# ── registry ────────────────────────────────────────────────────────────────

ROLE_TEMPLATES: dict[str, AgentRole] = {
    "planner": planner_role(),
    "executor": executor_role(),
    "auditor": auditor_role(),
    "researcher": researcher_role(),
    "security_auditor": security_auditor_role(),
}


def get_role(name: str, *, extra_tools: list[str] | None = None) -> AgentRole | None:
    """Get a pre-defined role template, optionally with extra tools."""
    template = ROLE_TEMPLATES.get(name)
    if template is None:
        return None
    if extra_tools:
        merged_tools = list(set(template.tools + extra_tools))
        return template.model_copy(update={"tools": merged_tools})
    return template


def list_roles() -> list[dict[str, str]]:
    """List all available role templates."""
    return [
        {
            "name": r.name,
            "role": r.role,
            "goal": r.goal[:80] + ("..." if len(r.goal) > 80 else ""),
            "tools": r.tools,
        }
        for r in ROLE_TEMPLATES.values()
    ]
