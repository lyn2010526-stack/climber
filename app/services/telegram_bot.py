"""Telegram transport adapter for the paired channel gateway."""

from __future__ import annotations

import os

import structlog

from app.core.channel_gateway import ChannelGateway, get_channel_gateway, set_channel_gateway
from app.services.channel_agent_handler import ChannelAgentHandler

logger = structlog.get_logger()

_bot_app = None
_registry = None  # ModelRegistry
_tool_registry = None  # ToolRegistry
_channel_handler: ChannelAgentHandler | None = None


def configure_bot(
    model_registry,
    tool_registry,
    *,
    dm_enabled: bool = False,
    pairing_ttl_seconds: int = 600,
    max_pending_pairings: int = 100,
) -> None:
    """Configure dependencies while preserving the existing two-argument call."""
    global _registry, _tool_registry, _channel_handler
    _registry = model_registry
    _tool_registry = tool_registry
    _channel_handler = None
    set_channel_gateway(
        ChannelGateway(
            dm_enabled=dm_enabled,
            pairing_ttl_seconds=pairing_ttl_seconds,
            max_pending_pairings=max_pending_pairings,
        )
    )


class TelegramAdapter:
    """Translate Telegram updates into channel-safe handler calls."""

    def __init__(self, handler: ChannelAgentHandler) -> None:
        self._handler = handler

    async def handle_message(self, update, _ctx) -> None:
        chat = getattr(update, "effective_chat", None)
        user = getattr(update, "effective_user", None)
        message = getattr(update, "message", None)
        text = getattr(message, "text", None)
        if chat is None or user is None or not text:
            return
        if str(getattr(chat, "type", "")) != "private":
            await chat.send_message("[DIRECT_MESSAGE_REQUIRED]")
            return

        await chat.send_chat_action("typing")
        try:
            response = await self._handler.handle_message(
                channel="telegram",
                external_user_id=str(user.id),
                conversation_id=str(chat.id),
                chat_type="private",
                text=text,
            )
        except Exception as exc:
            logger.warning("telegram.adapter_error", exception_type=type(exc).__name__)
            await chat.send_message("[CHANNEL_ERROR]")
            return
        if not response.ok:
            await chat.send_message(f"[{response.code}]")
            return
        for offset in range(0, len(response.text), 4000):
            await chat.send_message(response.text[offset : offset + 4000])

    async def handle_start(self, update, _ctx) -> None:
        chat = getattr(update, "effective_chat", None)
        if chat is None:
            return
        if str(getattr(chat, "type", "")) != "private":
            await chat.send_message("[DIRECT_MESSAGE_REQUIRED]")
            return
        await chat.send_message("Climber Agent ready. Send a private message to request pairing.")

    async def handle_capabilities(self, update, _ctx) -> None:
        chat = getattr(update, "effective_chat", None)
        if chat is None:
            return
        if str(getattr(chat, "type", "")) != "private":
            await chat.send_message("[DIRECT_MESSAGE_REQUIRED]")
            return
        await chat.send_message("dm:chat")


def _build_channel_handler() -> ChannelAgentHandler:
    from app.core.agent_engine import AgentEngine

    engine = AgentEngine(model_registry=_registry, tool_registry=_tool_registry)
    return ChannelAgentHandler(
        gateway=get_channel_gateway(),
        engine=engine,
        provider=os.environ.get("TELEGRAM_DEFAULT_PROVIDER", "openai"),
        model_id=os.environ.get("TELEGRAM_DEFAULT_MODEL", "gpt-4o-mini"),
        api_key=os.environ.get("USER_LLM_API_KEY", ""),
        base_url=os.environ.get("USER_LLM_BASE_URL") or None,
        system_prompt=os.environ.get("TELEGRAM_SYSTEM_PROMPT", "You are a helpful assistant."),
    )


async def start_telegram_bot() -> bool:
    """Start the Telegram bot in polling mode.

    Returns True if started, False if no token or already running.
    """
    global _bot_app, _channel_handler
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.info("Telegram bot disabled (no TELEGRAM_BOT_TOKEN)")
        return False
    if _bot_app is not None:
        logger.warning("Telegram bot already running")
        return True

    try:
        from telegram.ext import (
            ApplicationBuilder,
            CommandHandler,
            MessageHandler,
            filters,
        )
    except ImportError as exc:
        logger.error("python-telegram-bot not installed", exception_type=type(exc).__name__)
        return False

    try:
        application = ApplicationBuilder().token(token).build()
        if _channel_handler is None:
            _channel_handler = _build_channel_handler()
        adapter = TelegramAdapter(_channel_handler)

        application.add_handler(CommandHandler("start", adapter.handle_start))
        application.add_handler(CommandHandler("list", adapter.handle_capabilities))
        application.add_handler(CommandHandler("models", adapter.handle_capabilities))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, adapter.handle_message))

        await application.initialize()
        await application.start()
        await application.updater.start_polling()
    except Exception as exc:
        logger.error("Telegram bot startup failed", exception_type=type(exc).__name__)
        return False
    _bot_app = application
    logger.info("Telegram bot started")
    return True


async def stop_telegram_bot() -> None:
    """Stop the Telegram bot gracefully."""
    global _bot_app
    if _bot_app is None:
        return
    try:
        if _bot_app.updater and _bot_app.updater.running:
            await _bot_app.updater.stop()
        await _bot_app.stop()
        await _bot_app.shutdown()
    except Exception as exc:
        logger.warning("Telegram bot stop error", exception_type=type(exc).__name__)
    finally:
        _bot_app = None
