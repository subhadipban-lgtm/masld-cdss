"""Structured JSON logging for the MASLD DrugScope pipeline.

Provides a custom JSON formatter that injects timestamp, level, job_id,
and module into every log record.  Two handlers are configured:
  * console  — StreamHandler writing to stderr
  * file     — RotatingFileHandler (10 MB, 5 backups)
"""

import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON line.

    Fields included: timestamp, level, job_id (if present in the
    ``extra`` dict), module, message.
    """

    # Keys accepted via the ``extra`` parameter on logging calls.
    EXTRA_KEYS = ("job_id",)

    def format(self, record: logging.LogRecord) -> str:
        """Return a JSON-encoded string for *record*."""
        now = datetime.now(timezone.utc).isoformat()
        payload: dict = {
            "timestamp": now,
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        # Attach any recognised extra keys.
        for key in self.EXTRA_KEYS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        # Include exception info when present.
        if record.exc_info and record.exc_info[1] is not None:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger configured with JSON handlers.

    Parameters
    ----------
    name:
        Logger name, typically ``__name__`` of the calling module.
    """
    logger = logging.getLogger(name)

    # Avoid re-adding handlers on repeated calls.
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    formatter = JSONFormatter()

    # ── Console handler ────────────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ── Rotating file handler ──────────────────────────────────────────
    log_file = Path(settings.log_file_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Prevent propagation to the root logger to avoid duplicate output.
    logger.propagate = False
    return logger