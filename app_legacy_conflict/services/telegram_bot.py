"""Telegram Bot integration for remote agent control.

Allows users to chat with their agents via Telegram, receive task status
updates, and trigger workflows remotely — all running locally.

Usage:
    Set TELEGRAM_BOT_TOKEN env var, then call start_telegram_bot() from
    the app lifespan or a management command.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import structlog

logger = structlog.get_logger()

_bot_app = None
_registry = None  # ModelRegistry
_tool_registry = None  # ToolRegistry
_user_sessions: dict[int, dict[str, Any]] = {}  # tg_user_id -> session state


def configure_bot(model_registry, tool_registry) -> None:
    """Configure the bot with engine dependencies."""
    global _registry, _tool_registry
    _registry = model_registry
    _tool_registry = tool_registry


async def start_telegram_bot() -> bool:
    """Start the Telegram bot in polling mode.

    Returns True if started, False if no token or already running.
    """
    global _bot_app
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.info("Telegram bot disabled (no TELEGRAM_BOT_TOKEN)")
        return False
    if _bot_app is not None:
        logger.warning("Telegram bot already running")
        return True

    try:
        from telegram import Update
        from telegram.ext import (
            ApplicationBuilder,
            CommandHandler,
            MessageHandler,
            ContextTypes,
            filters,
        )
    except ImportError as e:
        logger.error("python-telegram-bot not installed", error=str(e))
        return False

    application = ApplicationBuilder().token(token).build()

    async def cmd_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_chat:
            await update.effective_chat.send_message(
                "Climber Agent 已就绪。\n直接发消息即可与 Agent 对话；\n/list — 列出可用工具；/models — 可用模型。"
            )

    async def cmd_list_tools(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not _tool_registry or not update.effective_chat:
            return
        tools = _tool_registry.list_tools()
        names = "\n".join(f"- {t.name}: {t.description[:40]}" for t in tools[:20])
        await update.effective_chat.send_message(f"可用工具 ({len(tools)}):\n{names}")

    async def cmd_list_models(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not _registry or not update.effective_chat:
            return
        providers = list(_registry.PROVIDERS.keys()) if hasattr(_registry, "PROVIDERS") else []
        await update.effective_chat.send_message(f"已注册 Provider: {', '.join(providers) or '(none)'}")

    async def handle_message(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or not update.message or not update.message.text:
            return
        tg_user_id = update.effective_chat.id
        user_text = update.message.text

        # Load or create a session for this Telegram user
        state = _user_sessions.get(tg_user_id)
        if state is None:
            state = {
                "provider": os.environ.get("TELEGRAM_DEFAULT_PROVIDER", "openai"),
                "model_id": os.environ.get("TELEGRAM_DEFAULT_MODEL", "gpt-4o-mini"),
                "api_key": os.environ.get("USER_LLM_API_KEY", ""),
                "base_url": os.environ.get("USER_LLM_BASE_URL") or None,
                "system_prompt": os.environ.get("TELEGRAM_SYSTEM_PROMPT", "You are a helpful assistant."),
                "agent_id": f"tg-{tg_user_id}",
                "messages": [],
            }
            _user_sessions[tg_user_id] = state

        # Send "typing..." indicator
        await update.effective_chat.send_chat_action("typing")

        try:
            from app.core.agent_engine import AgentEngine

            engine = AgentEngine(
                model_registry=_registry,
                tool_registry=_tool_registry,
            )
            session = engine.create_session(
                agent_id=state["agent_id"],
                user_id=str(tg_user_id),
                provider=state["provider"],
                model_id=state["model_id"],
                api_key=state["api_key"],
                base_url=state["base_url"],
                system_prompt=state["system_prompt"],
            )
            # Restore conversation history
            if state["messages"]:
                session.messages = list(state["messages"])

            # Run agent and stream text back
            parts: list[str] = []
            async for event in engine.run(session, user_text):
                if event.type.value == "text":
                    parts.append(event.data.get("content", ""))
                elif event.type.value == "done":
                    pass
                elif event.type.value == "error":
                    await update.effective_chat.send_message(f"[Error] {event.data.get('error', '')}")
                    return

            # Telegram message limit is 4096 chars
            reply = "".join(parts) or "(no response)"
            for i in range(0, len(reply), 4000):
                await update.effective_chat.send_message(reply[i : i + 4000])

            # Persist history (keep last 20 messages)
            state["messages"] = session.messages[-20:]
        except Exception as e:
            logger.error("Telegram handler error", error=str(e))
            await update.effective_chat.send_message(f"[内部错误] {str(e)}")

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("list", cmd_list_tools))
    application.add_handler(CommandHandler("models", cmd_list_models))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    _bot_app = application
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
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
    except Exception as e:
        logger.warning("Telegram bot stop error", error=str(e))
    finally:
        _bot_app = None
