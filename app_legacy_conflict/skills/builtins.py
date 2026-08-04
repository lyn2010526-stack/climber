"""Builtin skill handler functions."""

from __future__ import annotations

import asyncio
import json
import re
import urllib.parse

import httpx

from app.skills.memory_manager import persistent_memory, MemoryType


async def skill_recursive_research(topic: str, depth: int = 3, max_sources: int = 5) -> str:
    """Recursive Deep Research: search → extract → follow links → synthesize."""
    findings = []
    visited = set()

    async def search_and_extract(query: str, level: int) -> list[str]:
        if level <= 0 or len(visited) >= max_sources:
            return []

        results = []
        # DuckDuckGo search
        url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            try:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                text = resp.text
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()[:2000]
                results.append(f"[Level {level}] Search: {query}\n{text}")

                # Extract key terms for deeper search
                if level > 1:
                    words = re.findall(r"\b[A-Z][a-z]{3,}\b", text)
                    key_terms = list(set(words))[:3]
                    for term in key_terms:
                        sub_results = await search_and_extract(f"{query} {term}", level - 1)
                        results.extend(sub_results)
            except Exception as e:
                results.append(f"[Level {level}] Error: {e}")

        return results

    findings = await search_and_extract(topic, depth)

    report = f"""# Deep Research Report: {topic}
**Depth:** {depth} | **Sources:** {len(findings)}

"""
    for i, finding in enumerate(findings, 1):
        report += f"## Finding {i}\n{finding}\n\n"

    report += f"""---
**Synthesis Required:**
- Cross-reference findings for consensus
- Note contradictions or gaps
- Rate confidence per claim: HIGH / MEDIUM / LOW
- Provide actionable conclusions"""
    return report


async def skill_task_decomposition(objective: str, max_steps: int = 8) -> str:
    """Project Task Decomposition & Milestone Management."""
    return f"""# Task Decomposition: {objective}

## Strategy
Break the objective into atomic, verifiable sub-tasks with:
- Clear acceptance criteria
- Dependency mapping
- Effort estimation (S/M/L)
- Parallelization opportunities

## Output Format
For each task:
```
### Task N: [Name]
- **Goal:** What success looks like
- **Input:** Prerequisites needed
- **Output:** Deliverable produced
- **Depends on:** [Task IDs or "None"]
- **Estimate:** S / M / L
- **Parallel:** Yes / No
- **Verify:** How to confirm completion
```

## Rules
- Maximum {max_steps} tasks total
- Tasks must form a DAG (no circular deps)
- Each task independently verifiable
- Milestones at 25%, 50%, 75%, 100%

Generate the complete decomposition."""


async def skill_self_evolving(context: str, improvement_target: str = "accuracy") -> str:
    """Self-Evolving Agent: analyze performance, identify improvements, adapt."""
    return f"""# Self-Evolution Protocol

## Current Context
{context}

## Evolution Target
{improvement_target}

## Protocol
1. **Analyze:** What patterns lead to errors or inefficiency?
2. **Hypothesize:** What specific change would improve performance?
3. **Experiment:** Apply the change in a test scenario
4. **Measure:** Did the change improve outcomes?
5. **Adopt or Revert:** Keep improvements, discard regressions

## Self-Modification Rules
- Change ONE variable at a time
- Measure before and after
- Document what was tried and why
- Never remove safety constraints
- Keep a changelog of adaptations

## Output Format
```
### Analysis
What I observed about my performance

### Hypothesis
What I believe will improve things

### Experiment
What I will try differently

### Expected Outcome
What improvement I anticipate

### Verification
How to measure success
```

Begin self-analysis."""


async def skill_frontend_engineer(
    requirement: str,
    framework: str = "react",
    styling: str = "tailwindcss",
) -> str:
    """UI/UX Frontend Implementation Engineer with commercial design sense."""
    return f"""# Frontend Engineering Task

## Requirement
{requirement}

## Tech Stack
- Framework: {framework}
- Styling: {styling}
- State: hooks / context / zustand

## Engineering Standards
1. **Component Architecture**
   - Single Responsibility per component
   - Composition over inheritance
   - Props interface clearly typed
   - No prop drilling beyond 2 levels

2. **Styling**
   - Mobile-first responsive design
   - Consistent spacing (4px base grid)
   - Accessible color contrast (WCAG AA)
   - Smooth transitions (200-300ms)

3. **State Management**
   - Local state for UI-only data
   - Server state with proper caching
   - No unnecessary re-renders

4. **Performance**
   - Code splitting for large routes
   - Lazy loading for below-fold content
   - Memoize expensive computations
   - Optimize images (WebP, lazy load)

5. **Accessibility**
   - Semantic HTML elements
   - ARIA labels where needed
   - Keyboard navigation support
   - Screen reader friendly

6. **Error Handling**
   - Error boundaries for crash isolation
   - Graceful loading states
   - Meaningful error messages
   - Retry mechanisms

## Deliverables
- Complete component implementation
- Responsive layout (mobile/tablet/desktop)
- Loading and error states
- Unit tests for critical logic
- Storybook story (if applicable)"""


async def skill_backend_engineer(
    requirement: str,
    language: str = "python",
    framework: str = "fastapi",
) -> str:
    """Backend Engineer: API design, business logic, data layer."""
    return f"""# Backend Engineering Task

## Requirement
{requirement}

## Tech Stack
- Language: {language}
- Framework: {framework}

## Engineering Standards
1. **API Design**
   - RESTful conventions (proper HTTP verbs, status codes)
   - Consistent naming (noun-based resources)
   - Versioning strategy (URL or header)
   - Comprehensive error response format

2. **Input Validation**
   - Validate at the boundary (request DTOs)
   - Reject unknown fields
   - Clear error messages (field-level)
   - Sanitize all inputs

3. **Error Handling**
   - Domain-specific exception types
   - Global exception handler middleware
   - No stack traces in production
   - Structured error responses

4. **Data Layer**
   - Repository pattern for data access
   - Migration scripts for schema changes
   - Proper indexing strategy
   - Connection pooling

5. **Security**
   - Authentication & authorization (RBAC/ABAC)
   - Rate limiting per user/IP
   - CORS configuration
   - SQL injection prevention (parameterized queries)

6. **Observability**
   - Structured logging (correlation IDs)
   - Metrics for key operations
   - Health check endpoints
   - Request tracing

7. **Performance**
   - Async I/O for all external calls
   - Caching strategy (what, where, TTL)
   - Pagination for list endpoints
   - N+1 query prevention

## Deliverables
- Complete endpoint implementation
- Request/response schemas
- Data models and migrations
- Unit and integration tests
- API documentation (OpenAPI)"""


async def skill_database_architect(
    requirement: str,
    db_type: str = "postgresql",
) -> str:
    """Database Architecture & SQL Optimization."""
    return f"""# Database Architecture Task

## Requirement
{requirement}

## Database: {db_type}

## Design Principles
1. **Normalization**
   - 3NF minimum (denormalize only for performance)
   - Clear entity relationships
   - Proper foreign key constraints
   - Cascade rules explicitly defined

2. **Indexing Strategy**
   - Index all foreign keys
   - Composite indexes for frequent queries
   - Partial indexes for filtered queries
   - Monitor and remove unused indexes

3. **Performance**
   - EXPLAIN ANALYZE all critical queries
   - Avoid SELECT * (fetch only needed columns)
   - Use JOINs over subqueries where appropriate
   - Connection pooling (PgBouncer for Postgres)

4. **Migrations**
   - Backward-compatible changes only
   - Separate schema and data migrations
   - Idempotent scripts (re-runnable)
   - Rollback plan for each migration

5. **Security**
   - Least privilege per database user
   - Encrypt sensitive columns at rest
   - Audit trail for critical tables
   - Parameterized queries only

6. **Scalability**
   - Read replicas for read-heavy workloads
   - Table partitioning for large tables
   - Archival strategy for cold data
   - Sharding plan if single-node limits reached

## Deliverables
- Complete DDL (CREATE TABLE statements)
- Index definitions
- Migration scripts
- Sample optimized queries
- Scaling recommendations"""


async def skill_devops_engineer(
    requirement: str,
    platform: str = "docker",
) -> str:
    """Docker & K8s Deploy Engineer."""
    return f"""# DevOps Engineering Task

## Requirement
{requirement}

## Platform: {platform}

## Standards
1. **Containerization**
   - Multi-stage builds for minimal image size
   - Non-root user in containers
   - .dockerignore for build context
   - Health checks in Dockerfile
   - Pin base image versions (no `latest`)

2. **Docker Compose**
   - Service dependencies clearly defined
   - Volume persistence for data
   - Environment variable management
   - Network isolation between services
   - Restart policies configured

3. **Kubernetes (if applicable)**
   - Resource requests and limits
   - Liveness and readiness probes
   - Horizontal Pod Autoscaling
   - ConfigMaps and Secrets management
   - Ingress with TLS termination

4. **CI/CD**
   - Lint → Test → Build → Deploy pipeline
   - Automated testing before deploy
   - Rollback on failure
   - Environment promotion (dev → staging → prod)

5. **Observability**
   - Centralized logging (ELK/Loki)
   - Metrics (Prometheus + Grafana)
   - Alerting rules for SLI/SLO
   - Distributed tracing

6. **Security**
   - Image vulnerability scanning
   - Secret management (Vault/Sealed Secrets)
   - Network policies
   - Pod Security Standards

## Deliverables
- Dockerfile (production-grade)
- docker-compose.yml (full stack)
- CI/CD pipeline configuration
- Deployment runbook
- Monitoring setup"""


async def skill_git_master(
    action: str,
    branch: str = "",
    message: str = "",
) -> str:
    """Git Workflow Manager: branch strategy, PR analysis, conflict resolution."""
    import asyncio

    commands = {
        "status": "git status",
        "log": "git log --oneline --graph -20",
        "branches": "git branch -a --sort=-committerdate",
        "prune": "git fetch --prune",
        "stash": "git stash push -m 'agent-stash'",
    }

    if action in commands:
        cmd = commands[action]
    elif action == "commit":
        cmd = f"git diff --cached --stat && git commit -m '{message or 'chore: update'}'"
    elif action == "branch":
        cmd = f"git checkout -b {branch}"
    elif action == "merge":
        cmd = f"git merge --no-ff {branch} -m 'merge: {branch}'"
    elif action == "rebase":
        cmd = f"git rebase {branch or 'main'}"
    elif action == "conflict-resolve":
        cmd = "git diff --name-only --diff-filter=U"
    else:
        return f"Unknown action: {action}. Available: {list(commands.keys()) + ['commit', 'branch', 'merge', 'rebase', 'conflict-resolve']}"

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        output = stdout.decode()[:5000]
        if stderr:
            output += f"\n[stderr]: {stderr.decode()[:1000]}"
        return output or "Git command completed (no output)"
    except asyncio.TimeoutError:
        return "Git command timed out (30s)"
    except Exception as e:
        return f"Git error: {e}"


async def skill_code_reviewer(code: str, language: str = "python") -> str:
    """Multi-Agent Code Review: 5-dimensional parallel review."""
    return f"""# Code Review (5-Dimensional Analysis)

## Language: {language}

## Code
```{language}
{code}
```

## Review Dimensions

### 1. Correctness & Logic
- Does the code solve the stated problem?
- Edge cases: null, empty, single element, overflow
- Off-by-one errors in loops
- Race conditions in concurrent code
- Correct algorithm choice for the problem

### 2. Security
- Injection vulnerabilities (SQL, XSS, command, path traversal)
- Authentication/authorization gaps
- Sensitive data exposure (logs, errors, URLs)
- Input validation completeness
- Dependency vulnerabilities (outdated packages)
- Secrets in code

### 3. Performance
- Time complexity analysis (Big-O)
- Unnecessary loops or redundant computation
- Memory leaks (unclosed resources, growing collections)
- N+1 query patterns
- Missing caching opportunities
- Blocking operations in async context

### 4. Maintainability
- Single Responsibility Principle
- Appropriate abstraction level
- Clear naming (no `data`, `temp`, `foo`)
- No magic numbers/strings
- Proper error handling (specific exceptions)
- Testability (can this be easily tested?)

### 5. Style & Documentation
- Consistent formatting and naming
- Type hints on public APIs
- Docstrings for non-obvious logic
- Comments explain WHY, not WHAT
- Import organization
- No dead code or commented-out blocks

## Output Format
For each issue:
```
[SEVERITY: HIGH | MEDIUM | LOW] [DIMENSION: correctness/security/performance/maintainability/style]
Issue: Description of the problem
Fix: Concrete code suggestion
```

Begin 5-dimensional review."""


async def skill_security_auditor(code: str, context: str = "") -> str:
    """Security Audit: OWASP Top 10, CWE, threat modeling."""
    return f"""# Security Audit Report

## Target Code
```{code}
```

## Context
{context or "General security review"}

## Audit Framework

### OWASP Top 10 (2021)
1. **A01: Broken Access Control** — Can users access others' data?
2. **A02: Cryptographic Failures** — Sensitive data encrypted at rest and in transit?
3. **A03: Injection** — All inputs parameterized/sanitized?
4. **A04: Insecure Design** — Missing threat modeling, insecure patterns?
5. **A05: Security Misconfiguration** — Default creds, unnecessary features, verbose errors?
6. **A06: Vulnerable Components** — Outdated dependencies with known CVEs?
7. **A07: Auth Failures** — Weak password policy, session fixation, missing MFA?
8. **A08: Data Integrity** — No integrity checks on software updates, CI/CD?
9. **A09: Logging Failures** — Security events logged? Log injection possible?
10. **A10: SSRF** — Server-side requests to user-supplied URLs?

### Additional Checks
- Secrets in code (API keys, passwords, tokens)
- Insecure random number generation
- Path traversal in file operations
- XML external entity (XXE) injection
- Server-side request forgery (SSRF)
- Insecure deserialization
- Missing rate limiting
- Missing CORS configuration

## Output Format
For each finding:
```
[SEVERITY: CRITICAL | HIGH | MEDIUM | LOW | INFO]
OWASP Category: A0X: Name
Description: What the vulnerability is
Impact: What an attacker could achieve
Remediation: How to fix it
Code: Example fix
```

Begin security audit."""


async def skill_tdd_engineer(task: str, language: str = "python") -> str:
    """TDD Test Driven Development: Red → Green → Refactor."""
    return f"""# TDD Session

## Task
{task}

## Language: {language}

## TDD Cycle (Red → Green → Refactor)

### Step 1: RED — Write a failing test
- Write the SMALLEST possible test that captures one requirement
- Run the test and watch it FAIL (this validates the test)
- If it doesn't fail, the test is wrong or the feature already exists

### Step 2: GREEN — Make it pass with minimal code
- Write the SIMPLEST code that makes the test pass
- Don't add features beyond what the test requires
- Ugly code is fine — we'll refactor next

### Step 3: REFACTER — Clean up
- Improve naming, remove duplication, extract methods
- Run tests after EVERY change to ensure they still pass
- Repeat until code is clean

### Step 4: Repeat
- Add the next test, watch it fail, make it pass, refactor
- Each cycle should be 2-10 minutes

## Test Naming Convention
`test_<unit>_<scenario>_<expected_behavior>`
Example: `test_calculator_divide_by_zero_raises_value_error`

## Test Structure (Arrange-Act-Assert)
```python
def test_name():
    # Arrange: Set up test data and dependencies
    # Act: Execute the code under test
    # Assert: Verify the outcome matches expectations
```

## Engineering Rules
- One assertion per test (ideally)
- Tests must be independent (no shared mutable state)
- Don't test implementation details, test behavior
- Mock external dependencies (APIs, databases, time)
- Coverage target: >80% for critical paths

## Deliverables
- Complete test suite
- Implementation that passes all tests
- Coverage report
- Refactoring notes"""


async def skill_systematic_debugger(error_description: str, context: str = "") -> str:
    """Systematic Debugging: layered diagnosis approach."""
    return f"""# Systematic Debugging Session

## Error Description
{error_description}

## Context
{context or "No additional context"}

## Debugging Methodology (Layered Approach)

### Layer 1: Information Gathering
1. What EXACTLY is the error? (copy the full traceback)
2. When does it happen? (specific input, timing, frequency)
3. What changed recently? (code, config, dependencies, environment)
4. Can it be reproduced consistently?

### Layer 2: Reproduction
1. Create a MINIMAL test case that triggers the error
2. Document the exact steps to reproduce
3. Determine: intermittent vs consistent?

### Layer 3: Isolation (Binary Search)
1. Comment out half the code — does error persist?
2. Keep narrowing to the smallest code that reproduces
3. Check: is it in our code or a dependency?

### Layer 4: Root Cause Analysis (5 Whys)
Ask "why?" at least 5 times:
- Why did this error occur? → Answer 1
- Why did Answer 1 happen? → Answer 2
- Why did Answer 2 happen? → Answer 3
- Why did Answer 3 happen? → Answer 4
- Why did Answer 4 happen? → ROOT CAUSE

### Layer 5: Fix & Verify
1. Apply the targeted fix
2. Verify the error is gone
3. Verify no regressions (run related tests)
4. Add a test to prevent recurrence

## Common Error Categories
- **SyntaxError**: Missing colon, bracket, quote
- **TypeError**: Wrong type operation (None + str)
- **IndexError/KeyError**: Accessing non-existent element
- **AttributeError**: Method/attribute doesn't exist on object
- **ImportError**: Module not found or circular import
- **ValueError**: Right type but wrong value
- **LogicError**: Runs but produces wrong results (hardest)

## Output Format
```
### Root Cause
[What actually caused the error]

### Fix
[Specific code change to apply]

### Prevention
[How to prevent this class of error in the future]

### Test
[Test that would catch this regression]
```

Begin systematic debugging."""


async def skill_data_analyst(data: str, question: str = "") -> str:
    """Data Analysis & Visualization Engine."""
    lines = data.strip().split("\n")
    analysis = {
        "total_lines": len(lines),
        "total_chars": len(data),
        "non_empty": len([l for l in lines if l.strip()]),
    }

    # Detect format
    try:
        json.loads(data)
        analysis["format"] = "json"
    except json.JSONDecodeError:
        if "," in data and len(lines) > 1:
            cols = lines[0].count(",") + 1
            analysis["format"] = "csv"
            analysis["columns"] = cols
        else:
            analysis["format"] = "text"

    return f"""# Data Analysis Report

## Dataset Overview
- Format: {analysis["format"]}
- Rows: {analysis["total_lines"]}
- Non-empty: {analysis["non_empty"]}
- Characters: {analysis["total_chars"]}

## Analysis Question
{question or "Explore and summarize the data"}

## Framework
1. **Data Quality Check**
   - Missing values per column
   - Outlier detection
   - Type consistency
   - Duplicate rows

2. **Exploratory Analysis**
   - Distribution of key variables
   - Correlation between variables
   - Time-series trends (if applicable)
   - Category breakdowns

3. **Insight Extraction**
   - Top patterns discovered
   - Anomalies or surprises
   - Actionable recommendations

4. **Visualization Recommendations**
   - What chart types fit this data?
   - What relationships to highlight?

## Data Preview
```
{data[:2000]}
```

Begin analysis."""


async def skill_tech_researcher(topic: str) -> str:
    """Intelligent Tech Research & Information Aggregator."""
    return f"""# Technology Research: {topic}

## Research Objectives
1. Current state of the technology/approach
2. Strengths and weaknesses
3. Comparison with alternatives
4. Best practices and patterns
5. Common pitfalls to avoid
6. Recommended learning resources

## Research Method
1. Search authoritative sources (official docs, reputable blogs)
2. Cross-reference multiple perspectives
3. Note publication dates (prioritize recent)
4. Distinguish facts from opinions
5. Provide concrete examples

## Output Structure
```
## Executive Summary
[2-3 sentence overview]

## What is {topic}?
[Clear explanation]

## When to Use
[Appropriate use cases]

## When NOT to Use
[Inappropriate scenarios]

## Key Concepts
[Essential understanding]

## Best Practices
[Do's and Don'ts]

## Common Pitfalls
[Mistakes to avoid]

## Code Example
[Practical demonstration]

## Further Resources
[Links for deeper learning]
```

## Quality Standards
- Cite sources with URLs
- Include version numbers where relevant
- Note the date of information
- Distinguish stable features from experimental
- Warn about deprecated approaches

Begin research."""


async def skill_doc_generator(
    content: str,
    doc_type: str = "technical",
) -> str:
    """Automated Document Generation & Standardization."""
    templates = {
        "technical": "# Technical Design Document\n\n## Overview\n## Architecture\n## API Design\n## Data Model\n## Security\n## Testing Strategy\n## Deployment\n## Monitoring",
        "api": "# API Documentation\n\n## Endpoints\n## Authentication\n## Request/Response\n## Error Codes\n## Rate Limiting\n## Examples",
        "readme": "# Project Name\n\n## Description\n## Installation\n## Usage\n## Configuration\n## Contributing\n## License",
        "runbook": "# Operations Runbook\n\n## Service Overview\n## Architecture Diagram\n## Common Procedures\n## Troubleshooting\n## Escalation Path\n## Contacts",
        "postmortem": "# Incident Postmortem\n\n## Summary\n## Impact\n## Timeline\n## Root Cause\n## What Went Well\n## What Went Wrong\n## Action Items\n## Lessons Learned",
    }

    template = templates.get(doc_type, templates["technical"])

    return f"""# Document Generation Request

## Type: {doc_type}

## Template
{template}

## Source Content
{content[:5000]}

## Standards
- Use clear, concise language
- Include examples where helpful
- Add diagrams description (ASCII if applicable)
- Table of contents for long documents
- Consistent heading hierarchy
- Code blocks with language tags

Generate the complete document."""


async def skill_rag_organizer(documents: str, topic: str = "") -> str:
    """RAG Knowledge Base Organizer."""
    return f"""# RAG Knowledge Base Organization

## Topic
{topic or "General knowledge"}

## Documents
{documents[:5000]}

## Organization Strategy
1. **Chunking**
   - Split into logical sections (500-1000 tokens each)
   - Preserve context (overlap chunks by 100 tokens)
   - Maintain document structure (headers as chunk boundaries)

2. **Metadata Tagging**
   - Source document name
   - Section/topic tags
   - Creation/update date
   - Confidence level
   - Category classification

3. **Deduplication**
   - Identify overlapping content
   - Merge similar chunks
   - Remove exact duplicates

4. **Quality Filter**
   - Remove boilerplate (headers, footers, nav)
   - Filter low-value content (tables of contents, indexes)
   - Fix encoding issues
   - Normalize whitespace

5. **Indexing**
   - Generate embeddings for each chunk
   - Build search index
   - Tag with keywords for hybrid search

## Output
- Cleaned and chunked documents
- Metadata for each chunk
- Index mapping
- Quality report

Begin organization."""


async def skill_incident_analyzer(symptoms: str, context: str = "") -> str:
    """Incident Troubleshooting Root Cause Analyzer."""
    return f"""# Incident Analysis

## Symptoms
{symptoms}

## Context
{context or "No additional context"}

## Analysis Framework

### 1. Impact Assessment
- **Severity:** SEV1 (total outage) / SEV2 (partial) / SEV3 (minor) / SEV4 (cosmetic)
- **Scope:** How many users/systems affected?
- **Duration:** When did it start? Is it ongoing?

### 2. Timeline Reconstruction
- When was the last known good state?
- What changed between then and now?
- Any deployments, config changes, traffic spikes?

### 3. Hypothesis Generation
Generate 3-5 hypotheses ordered by likelihood:
1. [Most likely cause]
2. [Second most likely]
3. [Less likely but possible]

### 4. Evidence Gathering
For each hypothesis:
- What logs/metrics would confirm or deny?
- What's the quickest test to validate?

### 5. Root Cause Identification
Apply 5 Whys:
- Why is X happening? → Because of Y
- Why is Y happening? → Because of Z
- Continue until root cause found

### 6. Resolution & Prevention
- Immediate fix (stop the bleeding)
- Long-term fix (prevent recurrence)
- Monitoring to catch it earlier next time
- Runbook update

## Output Format
```
### Root Cause
[What ultimately caused this]

### Resolution Steps
1. [Immediate action]
2. [Follow-up fix]

### Prevention
[How to prevent recurrence]

### Action Items
- [ ] [Task] - Owner: [team] - Due: [date]
```

Begin analysis."""


async def skill_memory_action(action: str = "recall", query: str = "", content: str = "", memory_type: str = "fact") -> str:
    """Persistent Memory Manager: store, recall, and manage long-term agent memory."""
    if action == "recall":
        entries = persistent_memory.recall(query=query, limit=10)
        if not entries:
            return "No memories found matching the query."
        results = []
        for e in entries:
            results.append(f"- [{e.type.value}] {e.content} (importance: {e.importance}, accessed: {e.access_count}x)")
        return "# Memory Recall Results\n\n" + "\n".join(results)
    elif action == "store":
        mt = MemoryType.FACT
        try:
            mt = MemoryType(memory_type)
        except ValueError:
            pass
        entry = persistent_memory.store(content, memory_type=mt, source="agent")
        return f"Memory stored: {entry.id}"
    elif action == "stats":
        stats = persistent_memory.get_stats()
        return f"# Memory Statistics\n\n- Total: {stats['total_memories']}\n- By type: {stats['by_type']}\n- Storage: {stats['storage_path']}"
    else:
        return f"Unknown action: {action}. Use: recall, store, stats"


async def skill_dependency_auditor(project_path: str = ".") -> str:
    """Third-Party Dependency Management Auditor."""
    return f"""# Dependency Audit

## Project Path
{project_path}

## Audit Checklist

### 1. Inventory
- All dependencies listed with versions
- Direct vs transitive dependencies
- Dev vs production dependencies
- License compatibility check

### 2. Security
- Known CVEs for current versions
- Available security patches
- Vulnerability severity ratings
- Exploitability assessment

### 3. Freshness
- Last update date for each package
- How far behind latest version?
- Is the project still maintained?
- Community health indicators

### 4. Size & Impact
- Total dependency count
- Bundle size impact
- Duplicate functionality across packages
- Unused dependencies

### 5. License Compliance
- All licenses identified
- Compatibility with project license
- Copyleft requirements
- Attribution requirements

### 6. Recommendations
- Packages to upgrade
- Packages to replace
- Packages to remove
- Alternative suggestions

## Output
```
| Package | Current | Latest | Status | Action |
|---------|---------|--------|--------|--------|
| ...     | ...     | ...    | ...    | ...    |
```

Begin audit."""
