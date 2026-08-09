"""Structured logging with disk persistence and crash dumps.

Console-only logging means a crash at 3am leaves no evidence. This module adds
rotating file handlers plus a crash dump writer so unattended runs are
debuggable after the fact.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

DEFAULT_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
MAX_BYTES = 10 * 1024 * 1024  # 10 MB per file
BACKUP_COUNT = 5

_configured = False


def get_log_dir() -> Path:
    from app.config import settings

    raw = getattr(settings, "log_dir", None) or DEFAULT_LOG_DIR
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


def configure_logging(level: str = "INFO", log_dir: Path | None = None) -> Path:
    """Set up structlog + stdlib logging with console and rotating file output.

    Returns the directory logs are written to.
    """
    global _configured

    directory = Path(log_dir) if log_dir else get_log_dir()
    directory.mkdir(parents=True, exist_ok=True)

    numeric_level = getattr(logging, str(level).upper(), logging.INFO)

    timestamper = structlog.processors.TimeStamper(fmt="iso")
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty()),
        foreign_pre_chain=shared_processors,
    )
    json_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )

    root = logging.getLogger()
    # Drop handlers we installed previously so repeat calls don't duplicate output
    for handler in list(root.handlers):
        if getattr(handler, "_climber_managed", False):
            root.removeHandler(handler)
            handler.close()

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(console_formatter)
    console.setLevel(numeric_level)
    console._climber_managed = True  # type: ignore[attr-defined]
    root.addHandler(console)

    main_file = logging.handlers.RotatingFileHandler(
        directory / "climber.log", maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    main_file.setFormatter(json_formatter)
    main_file.setLevel(numeric_level)
    main_file._climber_managed = True  # type: ignore[attr-defined]
    root.addHandler(main_file)

    error_file = logging.handlers.RotatingFileHandler(
        directory / "error.log", maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    error_file.setFormatter(json_formatter)
    error_file.setLevel(logging.ERROR)
    error_file._climber_managed = True  # type: ignore[attr-defined]
    root.addHandler(error_file)

    root.setLevel(numeric_level)

    # Quiet down the noisiest third parties
    for noisy in ("sqlalchemy.engine", "httpx", "httpcore", "urllib3", "asyncio"):
        logging.getLogger(noisy).setLevel(max(numeric_level, logging.WARNING))

    _configured = True
    return directory


def write_crash_dump(exc: BaseException, context: dict[str, Any] | None = None) -> Path | None:
    """Persist a full traceback so post-mortem analysis is possible."""
    try:
        directory = get_log_dir() / "crashes"
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        path = directory / f"crash-{stamp}.log"

        lines = [
            f"timestamp: {datetime.now(timezone.utc).isoformat()}",
            f"exception: {type(exc).__name__}: {exc}",
            "",
        ]
        if context:
            lines.append("context:")
            lines.extend(f"  {k}: {v}" for k, v in context.items())
            lines.append("")
        lines.append("traceback:")
        lines.append("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))

        path.write_text("\n".join(lines), encoding="utf-8")
        return path
    except Exception:  # pragma: no cover - crash handler must never crash
        return None


def get_recent_logs(lines: int = 200, error_only: bool = False) -> list[str]:
    """Tail the log file for the diagnostics endpoint."""
    path = get_log_dir() / ("error.log" if error_only else "climber.log")
    if not path.exists():
        return []
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return content[-lines:]
    except Exception:
        return []
