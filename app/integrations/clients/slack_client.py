"""Slack integration client."""
from __future__ import annotations

from dataclasses import dataclass

from ._http import IntegrationError, request_json, require_config, response_id, validate_text


@dataclass
class SlackConfig:
    token: str = ""
    channel: str = ""
    timeout: float = 15.0


class SlackClient:
    def __init__(self, config: SlackConfig | None = None):
        self.config = config or SlackConfig()
        self.last_message_id: str | None = None
        self.last_channel_id: str | None = None

    async def send_message(self, message: str) -> bool:
        """Post text; retain bool compatibility and expose the confirmed ts/channel.

        Contract: https://docs.slack.dev/reference/methods/chat.postMessage/
        A failure raises; last_message_id is cleared before each attempt.
        """
        self.last_message_id = None
        self.last_channel_id = None
        require_config("Slack", token=self.config.token, channel=self.config.channel)
        validate_text(message, "message", 40000)
        data = await request_json(
            "Slack", "POST", "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {self.config.token}"},
            timeout=self.config.timeout,
            payload={"channel": self.config.channel, "text": message},
        )
        if data.get("ok") is not True:
            # Do not include remote text, which can echo credentials or message contents.
            raise IntegrationError("Slack", "chat.postMessage did not confirm success", status_code=200)
        message_id = response_id(data, "ts", "Slack")
        channel_id = response_id(data, "channel", "Slack")
        self.last_message_id = message_id
        self.last_channel_id = channel_id
        return True
