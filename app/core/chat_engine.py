"""Chat engine integration for agent mode and MCP control."""

from __future__ import annotations

from typing import Optional

from app.core.mcp_controller import McpController, McpStatus
from app.core.prompt_manager import PromptManager
from app.services.settings_service import SettingsService


class ChatEngine:
    """Integrates prompt management and MCP control for chat sessions."""

    def __init__(
        self,
        prompt_manager: PromptManager,
        mcp_controller: McpController,
        settings_service: SettingsService,
    ) -> None:
        self.prompt_manager = prompt_manager
        self.mcp_controller = mcp_controller
        self.settings_service = settings_service

    async def get_system_prompt(self, user_id: str) -> str:
        """Assemble system prompt based on user settings and MCP status."""
        settings = await self.settings_service.get_settings(user_id)
        mcp_status = self.mcp_controller.get_status()

        return self.prompt_manager.assemble_prompt(
            autonomous_mode=settings.autonomous_agent_mode,
            mcp_ready=mcp_status == McpStatus.READY,
        )

    async def get_active_constraints(self, user_id: str) -> list[str]:
        """Get list of active constraint names."""
        settings = await self.settings_service.get_settings(user_id)
        mcp_status = self.mcp_controller.get_status()

        return self.prompt_manager.get_active_constraints(
            autonomous_mode=settings.autonomous_agent_mode,
            mcp_ready=mcp_status == McpStatus.READY,
        )

    async def ensure_mcp_ready(self, user_id: str) -> McpStatus:
        """Ensure MCP is ready if enabled, return current status."""
        settings = await self.settings_service.get_settings(user_id)

        if not settings.token_throttle_mcp_enabled:
            return McpStatus.DISCONNECTED

        status = self.mcp_controller.get_status()

        if status == McpStatus.READY:
            return McpStatus.READY

        if status in (McpStatus.DISCONNECTED, McpStatus.ERROR):
            result = await self.mcp_controller.start()
            await self.settings_service.update_mcp_status(user_id, result.status)
            return result.status

        return status

    async def get_effective_mode(self, user_id: str) -> dict:
        """Get effective running mode for the user."""
        settings = await self.settings_service.get_settings(user_id)
        mcp_status = self.mcp_controller.get_status()

        return {
            "autonomous_agent_mode": settings.autonomous_agent_mode,
            "token_throttle_mcp_enabled": settings.token_throttle_mcp_enabled,
            "mcp_status": mcp_status.value,
            "mcp_ready": mcp_status == McpStatus.READY,
        }
