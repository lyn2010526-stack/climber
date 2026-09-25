"""Discord integration client."""
from __future__ import annotations

from dataclasses import dataclass

from ._http import IntegrationError, request_json, require_config, response_id, validate_text


@dataclass
class DiscordConfig:
    token: str = ""
    channel_id: str = ""
    timeout: float = 15.0


class DiscordClient:
    def __init__(self, config: DiscordConfig | None = None):
        self.config = config or DiscordConfig()
        self.last_message_id: str | None = None

    async def send_message(self, message: str) -> bool:
        """Post as a bot; retain bool compatibility and expose last_message_id.

        Contract: https://docs.discord.com/developers/resources/message#create-message
        Only bot tokens and existing channel IDs are supported.
        """
        self.last_message_id = None
        require_config("Discord", token=self.config.token, channel_id=self.config.channel_id)
        if not self.config.channel_id.isascii() or not self.config.channel_id.isdecimal():
            raise ValueError("channel_id must be a Discord snowflake string")
        validate_text(message, "message", 2000)
        data = await request_json(
            "Discord", "POST",
            f"https://discord.com/api/v10/channels/{self.config.channel_id}/messages",
            headers={"Authorization": f"Bot {self.config.token}"},
            timeout=self.config.timeout, payload={"content": message},
        )
        message_id = response_id(data, "id", "Discord")
        if response_id(data, "channel_id", "Discord") != self.config.channel_id:
            raise IntegrationError("Discord", "response channel mismatch; outcome unknown")
        self.last_message_id = message_id
        return True
