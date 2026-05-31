"""
Centralised logging configuration.

Call :func:`configure_logging` once at process start. Modules then use the
standard ``logging.getLogger(__name__)`` pattern instead of ``print``.
"""

from __future__ import annotations

import logging

from config import settings

_CONFIGURED = False


def configure_logging() -> None:
    """Configure root logging once, honouring ``settings.log_level``."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    _CONFIGURED = True
