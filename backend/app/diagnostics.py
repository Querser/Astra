"""Bounded local diagnostics without request bodies or health measurements."""

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime, timezone

MAX_LOG_BYTES = 2_000_000
BACKUP_COUNT = 4


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.msg,
        }
        for field in ("request_id", "method", "route", "status", "duration_ms", "error_type", "code",
                      "attempt", "outcome", "category", "input_utf8_bytes", "prompt_eval_count", "eval_count",
                      "done_reason", "retry_reason", "will_retry", "radlab_total", "lab_total",
                      "radlab_inserted", "lab_inserted"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logger(log_dir: Path) -> logging.Logger:
    """Write rotating JSON lines to a user data directory outside the repository."""

    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("astra.diagnostics")
    logger.disabled = False
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    handler = RotatingFileHandler(
        log_dir / "astra.jsonl", maxBytes=MAX_LOG_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger
