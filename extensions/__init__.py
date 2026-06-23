"""
Detachable, self-contained feature add-ons.

Everything in this package is optional. To remove a feature entirely, delete its
module here, its ``assets/ext_*.{js,css}`` files, and the single
``install_extensions(server)`` call in ``app.create_app()``. Nothing in the core
app imports from here except that one hook.

Current extensions:
  * chat_with_data — a floating "ask the data" widget on dashboard pages.
"""

from __future__ import annotations

import logging

from config import settings

logger = logging.getLogger(__name__)


def install_extensions(server, dash_app=None) -> None:
    """Register all enabled extensions onto the Flask ``server``.

    Safe to delete: removing this call (and the ``extensions/`` package) fully
    detaches every optional feature.
    """
    if settings.features_chat_enabled:
        from extensions.chat_with_data import register_chat

        register_chat(server)
        logger.info("Extension enabled: chat_with_data")

    if dash_app is not None:
        from extensions.saved_views import register_saved_views

        register_saved_views(dash_app)
