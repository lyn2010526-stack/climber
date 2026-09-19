"""Slack integration client."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SlackConfig:
    token: str = ""
    channel: str = ""


class SlackClient:
    def __init__(self, config: SlackConfig | None = None):
        self.config = config or SlackConfig()

    async def send_message(self, message: str) -> bool:
        return True
