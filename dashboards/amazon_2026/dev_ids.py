"""Dev-mode element reference codes.

Every element that should carry a "P1S2G1"-style reference code in dev mode has that
code hardcoded as a literal string at its definition site (see page modules under
``dashboards/amazon_2026/pages`` and the ``charts_*`` modules). The helpers here only
control whether those literal codes are shown.

Naming convention (for assigning new codes): ``P<page><Snnn>[Nx...][Type+index]``.
Page numbers follow the order pages are built in ``pages/__init__.py`` (P1 = Overview,
P2 = Narratives, P3 = Publishers, P5 = Clusters). ``S<n>`` is the nth
top-level component on the page, ``N<n>`` a nested container (own counter per parent),
and the type codes for leaf items are ``C`` card, ``G`` graph, ``T`` table, ``B``
button, ``A`` ag_grid, ``X`` text, ``U`` tabs.
"""
from __future__ import annotations

_ENABLED = False


def set_dev_mode(enabled: bool) -> None:
    global _ENABLED
    _ENABLED = enabled


def is_enabled() -> bool:
    return _ENABLED


def ref_label(label: str, ref: str) -> str:
    """Prefix a visible label with its hardcoded ref code when dev mode is on."""
    if not _ENABLED or not ref or not label:
        return label
    return f"{ref} {label}"


def ref_only(ref: str) -> str:
    """Title for elements with no natural title of their own.

    Returns the ref code when dev mode is on, else "" so no title bar renders.
    """
    return ref if _ENABLED else ""


def ref_badge(ref: str) -> str:
    """Inline badge text showing just the ref code, when dev mode is on."""
    return ref if _ENABLED else ""
