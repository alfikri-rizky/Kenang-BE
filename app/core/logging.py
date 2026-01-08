import logging
import sys
from typing import Any, Dict

import structlog

from app.core.config import settings


def setup_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            (
                structlog.processors.JSONRenderer()
                if settings.is_production
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.APP_DEBUG else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.APP_DEBUG else logging.INFO,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)


def mask_phone(phone: str) -> str:
    if len(phone) < 8:
        return "****"
    return f"{phone[:4]}****{phone[-4:]}"


def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    sensitive_keys = {"phone_number", "phone", "otp", "code", "token", "password"}
    masked = {}
    for key, value in data.items():
        if key.lower() in sensitive_keys:
            if isinstance(value, str):
                masked[key] = (
                    "****" if len(value) < 8 else f"{value[:2]}****{value[-2:]}"
                )
            else:
                masked[key] = "****"
        else:
            masked[key] = value
    return masked
