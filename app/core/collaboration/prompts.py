"""Prompt building functions for group collaboration roles."""

from __future__ import annotations

from typing import Any


def build_initial_prompt(task_description: str, context: str) -> str:
    """Build the initial prompt for a task without previous output.

    Args:
        task_description: The task description.
        context: Additional context from dependencies/memory.

    Returns:
        A formatted prompt string.
    """
    parts = [f"Task: {task_description}"]
    if context:
        parts.append(f"\nContext:\n{context}")
    return "\n".join(parts)


def build_sequential_prompt(
    task_description: str,
    context: str,
    previous_output: str,
    issues: list[dict[str, Any]],
) -> str:
    """Build a prompt for sequential retry with issues to fix.

    Args:
        task_description: The task description.
        context: Context from previous tasks and memory.
        previous_output: The output from the previous attempt.
        issues: List of issues to address.

    Returns:
        A formatted prompt string.
    """
    parts = [f"Task: {task_description}"]
    if context:
        parts.append(f"\nContext from previous tasks and memory:\n{context}")
    parts.append(f"\nPrevious output:\n{previous_output}")
    if issues:
        issue_descriptions = [i.get("description", str(i)) for i in issues]
        parts.append(f"\nIssues to fix:\n{chr(10).join('- ' + desc for desc in issue_descriptions)}")
    return "\n".join(parts)


def build_group_chat_context(task_description: str, conversation: list[dict[str, Any]]) -> str:
    """Build context message for group chat from conversation history.

    Args:
        task_description: The task description.
        conversation: List of conversation messages.

    Returns:
        A formatted context string.
    """
    parts = [f"Task: {task_description}\n"]
    for msg in conversation:
        parts.append(
            f"[{msg.get('agent_name', 'Unknown')} ({msg.get('role', 'participant')})]: {msg.get('content', '')}"
        )
    return "\n".join(parts)


def build_manager_planning_prompt(task_description: str, workers: list[Any]) -> str:
    """Build prompt for manager to plan subtasks.

    Args:
        task_description: The overall task description.
        workers: List of available worker members.

    Returns:
        A formatted planning prompt string.
    """
    worker_names = [f"- {w.agent_id} ({w.role})" for w in workers]
    return f"""Break down the following task into subtasks for the available workers.

Task: {task_description}

Available workers:
{chr(10).join(worker_names)}

Provide a plan with:
1. Subtask assignments to specific workers
2. Expected output for each subtask
3. Dependencies between subtasks"""


def build_manager_validation_prompt(
    task_description: str,
    plan: str,
    subtask_outputs: dict[str, str],
) -> str:
    """Build prompt for manager to validate subtask outputs.

    Args:
        task_description: The original task description.
        plan: The manager's plan.
        subtask_outputs: Dictionary mapping worker IDs to their outputs.

    Returns:
        A formatted validation prompt string.
    """
    outputs_text = "\n\n".join(
        f"Worker {wid} output:\n{output}" for wid, output in subtask_outputs.items()
    )
    return f"""Validate whether the subtask outputs collectively satisfy the original task.

Original task: {task_description}

Manager plan: {plan}

Subtask outputs:
{outputs_text}

Respond with:
1. "通过" if the combined outputs satisfy the task requirements, or "不通过" if not.
2. If not passing, list specific issues or missing requirements."""


def build_worker_prompt(task_description: str) -> str:
    """Build system prompt for a worker agent.

    Args:
        task_description: The task the worker should perform.

    Returns:
        A formatted worker system prompt.
    """
    return f"""You are an executor agent. Complete tasks thoroughly and precisely, delivering high-quality output.

Task: {task_description}

Produce a complete, high-quality output. Be thorough and precise."""


def build_manager_prompt(task_description: str) -> str:
    """Build system prompt for a manager agent.

    Args:
        task_description: The task the manager should coordinate.

    Returns:
        A formatted manager system prompt.
    """
    return f"""You are a manager agent responsible for coordinating workers to complete tasks.

Task: {task_description}

Your responsibilities:
1. Break down the task into clear subtasks
2. Assign subtasks to appropriate workers
3. Validate worker outputs
4. Synthesize final results

Be decisive and thorough."""


def build_reviewer_prompt(task_description: str) -> str:
    """Build system prompt for a reviewer agent.

    Args:
        task_description: The task the reviewer should evaluate against.

    Returns:
        A formatted reviewer system prompt.
    """
    return f"""You are a reviewer agent.
Review the following output against the task requirements.

Task: {task_description}
Output: [WORKER_OUTPUT]

Respond with:
1. "通过" if the output meets all requirements, or "不通过" if not.
2. If not passing, list specific issues found."""


def build_review_prompt(task_description: str, worker_output: str) -> str:
    """Build prompt for reviewing a specific worker output.

    Args:
        task_description: The task description.
        worker_output: The worker's output to review.

    Returns:
        A formatted review prompt string.
    """
    return f"""Review the following output against the task requirements.

Task: {task_description}
Output: {worker_output}

Respond with:
1. "通过" if the output meets all requirements, or "不通过" if not.
2. If not passing, list specific issues found."""


def build_group_chat_prompt(role: str) -> str:
    """Build system prompt for a group chat participant based on role.

    Args:
        role: The participant's role (worker/reviewer/manager/participant).

    Returns:
        A formatted group chat system prompt.
    """
    role_descriptions = {
        "worker": "You are a collaborative team member. Contribute constructively to achieve the group's goal.",
        "reviewer": "You are a critical reviewer. Evaluate proposals and suggest improvements.",
        "manager": "You are a coordinator. Keep discussion focused and drive toward consensus.",
        "participant": "You are a team participant. Share ideas and build on others' contributions.",
    }
    desc = role_descriptions.get(role, role_descriptions["participant"])
    return f"""{desc}

You are participating in a group discussion. Be concise, constructive, and focused on the goal."""


def summarize_group_chat(task_description: str, conversation: list[dict[str, Any]]) -> str:
    """Summarize group chat into final output.

    Args:
        task_description: The task description.
        conversation: List of all conversation messages.

    Returns:
        A formatted summary string.
    """
    lines = [f"Group discussion for: {task_description}\n"]
    for msg in conversation:
        lines.append(f"[{msg.get('agent_name', 'Unknown')}]: {msg.get('content', '')[:500]}")
    return "\n\n".join(lines)
