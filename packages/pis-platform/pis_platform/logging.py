from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

from pis_platform.correlation import get_correlation_id, get_trace_id


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service,
            "level": record.levelname,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
            "trace_id": get_trace_id(),
            "logger": record.name,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(service: str, level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service))
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

