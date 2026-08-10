"""System prompt management with base + dynamic constraint assembly."""

from __future__ import annotations


class PromptManager:
    """Manages base system prompt and dynamic constraint fragments."""

    def __init__(self) -> None:
        self.base_prompt = self._load_base_prompt()
        self.autonomous_prompt = self._load_autonomous_prompt()
        self.mcp_constraint_prompt = self._load_mcp_constraint_prompt()

    def _load_base_prompt(self) -> str:
        """Load the permanent base system prompt."""
        return (
            "You are Climber, a helpful AI assistant.\n"
            "You can engage in natural conversations and help users with various tasks.\n"
            "Always be concise, accurate, and helpful."
        )

    def _load_autonomous_prompt(self) -> str:
        """Load the autonomous agent mode prompt fragment."""
        return (
            "\n\n[ Autonomous Agent Mode ]\n"
            "You are now operating in autonomous agent mode.\n"
            "- Break down complex tasks into executable steps\n"
            "- Plan ahead before taking actions\n"
            "- Execute tasks continuously until completion\n"
            "- Reflect on results and self-correct when needed\n"
            "- Report progress transparently to the user"
        )

    def _load_mcp_constraint_prompt(self) -> str:
        """Load the token throttle MCP constraint fragment."""
        return (
            "\n\n[ Token Throttle - Code Retrieval Constraints ]\n"
            "The jCodeMunch MCP service is active.\n"
            "- ALWAYS use code search before reading full files\n"
            "- NEVER read entire project directories at once\n"
            "- Prefer targeted snippet retrieval over bulk reads\n"
            "- Cache frequently accessed code patterns\n"
            "- Minimize token usage by being precise in queries"
        )

    def assemble_prompt(self, autonomous_mode: bool, mcp_ready: bool) -> str:
        """Assemble the final system prompt based on active modes."""
        prompt = self.base_prompt
        if autonomous_mode:
            prompt += self.autonomous_prompt
        if mcp_ready:
            prompt += self.mcp_constraint_prompt
        return prompt

    def get_active_constraints(self, autonomous_mode: bool, mcp_ready: bool) -> list[str]:
        """Return list of active constraint fragment names."""
        constraints = []
        if autonomous_mode:
            constraints.append("autonomous_agent")
        if mcp_ready:
            constraints.append("token_throttle_mcp")
        return constraints

    def get_base_prompt(self) -> str:
        """Get the permanent base prompt."""
        return self.base_prompt

    def get_autonomous_prompt(self) -> str:
        """Get the autonomous mode prompt fragment."""
        return self.autonomous_prompt

    def get_mcp_constraint_prompt(self) -> str:
        """Get the MCP constraint prompt fragment."""
        return self.mcp_constraint_prompt
