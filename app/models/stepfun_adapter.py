"""StepFun model adapter - OpenAI-compatible API."""

from __future__ import annotations

from app.models.openai_adapter import ModelCapability, OpenAIAdapter


class StepFunAdapter(OpenAIAdapter):
    """Adapter for StepFun API (OpenAI-compatible)."""

    def __init__(self, model_id: str, api_key: str, base_url: str = "https://api.stepfun.com/v1", capabilities: "ModelCapability | None" = None):
        super().__init__(model_id, api_key, base_url)
        self._capabilities = capabilities

    @property
    def provider(self) -> str:
        return "stepfun"

    @property
    def capabilities(self) -> ModelCapability:
        if self._capabilities is not None:
            return self._capabilities
        return ModelCapability(
            chat=True,
            streaming=False,
            tools=True,
            vision=False,
            embedding=False,
            max_tokens=128_000,
        )

    async def chat(
        self,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]] | None = None,
        **kwargs: object,
    ) -> object:
        """Non-streaming chat completion for StepFun."""
        return await self._chat_non_streaming(messages, tools, **kwargs)
