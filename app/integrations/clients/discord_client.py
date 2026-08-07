"""Discord integration client."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class DiscordConfig:
    token: str = ""
    channel_id: str = ""


class DiscordClient:
    def __init__(self, config: DiscordConfig | None = None):
        self.config = config or DiscordConfig()
    
    async def send_message(self, message: str) -> bool:
        return True
