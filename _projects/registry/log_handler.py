"""Centralized logging for the LIGO Registry.

Every service registration and usage event is logged through this handler.
Format: ISO_TIMESTAMP | LEVEL | MODULE | MESSAGE | CONTEXT_JSON
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any


# ------------------------------------------------------------------
# Log path — centralized via `_config` (no hardcoded paths!)
# ------------------------------------------------------------------

from _config import LOGS_DIR as _LOGS_DIR

os.makedirs(_LOGS_DIR, exist_ok=True)
_log_file = str(_LOGS_DIR / "registry.log")

_logger = logging.getLogger("ligo.registry")
_logger.setLevel(logging.INFO)

_handler = logging.FileHandler(_log_file, encoding="utf-8")
_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s | %(levelname)-5s | LIGO.%(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z"
    )
)
_logger.addHandler(_handler)


def _format_context(context: dict[str, Any] | None) -> str:
    """Format context dict as a compact JSON string."""
    if not context:
        return ""
    try:
        return json.dumps(context, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(context)


def log_event(
    level: str,
    message: str,
    **context: Any,
) -> None:
    """Log a registry event with structured context.

    Args:
        level: Log level string ("info", "warning", "error").
        message: Human-readable message.
        **context: Key-value pairs to include in the log entry.
    """
    ctx_str = _format_context(context)
    full_message = f"{message}" + (f" | context={ctx_str}" if ctx_str else "")

    getattr(_logger, level.lower(), _logger.info)(full_message)


def info(message: str, **context: Any) -> None:
    """Convenience wrapper for INFO-level registry events."""
    log_event("info", message, **context)


def warning(message: str, **context: Any) -> None:
    """Convenience wrapper for WARNING-level registry events."""
    log_event("warning", message, **context)


def error(message: str, **context: Any) -> None:
    """Convenience wrapper for ERROR-level registry events."""
    log_event("error", message, **context)