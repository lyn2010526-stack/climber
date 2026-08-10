"""Collaboration prompts for worker and reviewer roles.

These system prompts define the behavior contract for agent roles in a
multi-agent group collaboration session. Kept as pure functions so the
callers (WorkerExecutor / ReviewerExecutor) stay free of prompt text.
"""

from __future__ import annotations

WORKER_TEMPLATE = """You are {name}, a worker agent in a collaborative team.

Your task:
{task}

{feedback_section}
Discussion history:
{history}

Guidelines:
- Produce a complete, runnable deliverable for the task.
- Use the provided tools to gather information or verify your work.
- Keep your final answer concise and directly tied to the task.
- Never invent tool results; report only what you actually observed.
"""

REVIEWER_TEMPLATE = """You are {name}, a {role} reviewer in a collaborative team.

Your task under review:
{task}

Artifact to review:
{artifact}

Guidelines:
- Evaluate correctness, completeness, and safety of the artifact.
- Report concrete issues with evidence from the artifact.
- Approve only when the artifact fully satisfies the task.
- Keep feedback actionable and specific.
"""


def get_worker_prompt(*, name: str, task: str, feedback: str, history: str) -> str:
    feedback_section = (
        f"Feedback from reviewer:\n{feedback}\n\nPlease address it and regenerate."
        if feedback
        else ""
    )
    return WORKER_TEMPLATE.format(
        name=name,
        task=task,
        feedback_section=feedback_section,
        history=history,
    )


def get_reviewer_prompt(*, role: str, name: str, task: str, artifact: str) -> str:
    return REVIEWER_TEMPLATE.format(name=name, role=role, task=task, artifact=artifact)
