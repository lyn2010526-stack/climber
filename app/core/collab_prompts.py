"""Collaboration prompts for multi-agent worker execution."""
from __future__ import annotations


def get_worker_prompt(role: str = "worker", context: str = "") -> str:
    """Get the system prompt for a worker agent."""
    return f"""You are a {role} agent. Your task is to complete the assigned work efficiently and report results.

Context: {context}

Follow these guidelines:
1. Complete the task step by step
2. Report progress clearly
3. Ask for clarification if needed
4. Output results in the requested format
"""
