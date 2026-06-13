"""
Extension: Chat with your data  (detachable)
============================================

Adds a single Flask endpoint — ``POST /ext/chat/ask`` — that answers
natural-language questions about the dataset behind a dashboard.

How it answers
--------------
* If ``settings.gemini_api_key`` is set, the dataset's schema + a compact
  summary are sent to Gemini and its reply is returned.
* Otherwise (the default in dev, where there are no GCP creds) a small local
  pandas heuristic answers common questions so the feature is still demoable
  offline.

Security
--------
The endpoint is read-only (it never mutates state) and is authorisation-gated:
the caller must be logged in and able to access the requested dashboard slug
(``tenancy.access.can_access``), mirroring the company-first access model used
by the ``/app`` gate. Being read-only and same-origin, it is intentionally
CSRF-exempt.

To remove this feature
----------------------
Delete this module, ``assets/ext_chat.js`` + ``assets/ext_chat.css``, and the
``install_extensions(server)`` call in ``app.create_app()``. No core module
imports from here.
"""

from __future__ import annotations

import logging
from typing import Callable

import pandas as pd
from flask import Blueprint, jsonify, request

from config import settings

logger = logging.getLogger(__name__)

bp = Blueprint("ext_chat", __name__)

# Hard limits to keep prompts/answers bounded and cheap.
_MAX_QUESTION_LEN = 500
_SAMPLE_ROWS = 15


# ── Per-dashboard data providers ──────────────────────────────────────────────
# Kept here (rather than inside each dashboard package) so the whole feature
# lives in one place and stays trivially removable. A provider returns
# ``(DataFrame, human-readable description)``.

def _provider_timeline() -> tuple[pd.DataFrame, str]:
    from data import df_weekly

    return df_weekly, "Weekly reach & engagement by narrative and sentiment."


def _provider_breakdown() -> tuple[pd.DataFrame, str]:
    from data import df_weekly_narratives

    return df_weekly_narratives, "Weekly reach & engagement per narrative (no aggregate)."


def _provider_bq_sample() -> tuple[pd.DataFrame, str]:
    from dashboards.bq_sample.data import load_disinformation_timeline

    return load_disinformation_timeline(), "Daily publication counts per disinformation-lifecycle stage."


_DATA_PROVIDERS: dict[str, Callable[[], tuple[pd.DataFrame, str]]] = {
    "timeline": _provider_timeline,
    "breakdown": _provider_breakdown,
    "bq_sample": _provider_bq_sample,
}


# ── Answer engines ────────────────────────────────────────────────────────────

def _dataset_summary(df: pd.DataFrame) -> str:
    """Compact, prompt-friendly description of a dataframe."""
    lines = [
        f"Rows: {len(df)}",
        f"Columns: {', '.join(f'{c} ({df[c].dtype})' for c in df.columns)}",
    ]
    try:
        stats = df.describe(include="all").round(2)
        lines.append("Summary statistics:\n" + stats.to_string())
    except Exception:  # pragma: no cover - describe is robust but be safe
        pass
    lines.append(f"First {_SAMPLE_ROWS} rows:\n" + df.head(_SAMPLE_ROWS).to_string(index=False))
    return "\n\n".join(lines)


def _gemini_answer(df: pd.DataFrame, question: str, label: str) -> str | None:
    """Ask Gemini, or return None if unavailable so the caller can fall back."""
    if not settings.gemini_api_key:
        return None

    prompt = (
        "You are a concise data analyst. Answer the user's question using ONLY "
        "the dataset described below. If the data cannot answer it, say so.\n\n"
        f"Dataset: {label}\n\n{_dataset_summary(df)}\n\n"
        f"Question: {question}\n\nAnswer:"
    )

    # Prefer the modern google-genai SDK, fall back to google-generativeai.
    try:
        from google import genai  # type: ignore

        client = genai.Client(api_key=settings.gemini_api_key)
        resp = client.models.generate_content(model=settings.gemini_model, contents=prompt)
        text = getattr(resp, "text", None)
        if text:
            return text.strip()
    except Exception as exc:  # SDK missing, bad creds, network, etc.
        logger.debug("google-genai unavailable (%s); trying legacy SDK", exc)

    try:
        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)
        text = getattr(model.generate_content(prompt), "text", None)
        if text:
            return text.strip()
    except Exception as exc:
        logger.warning("Gemini call failed, using local fallback: %s", exc)

    return None


def _local_answer(df: pd.DataFrame, question: str, label: str) -> str:
    """Offline pandas heuristic for common questions (no AI required)."""
    q = question.lower()
    numeric = df.select_dtypes("number").columns.tolist()
    categorical = [c for c in df.columns if c not in numeric]

    def _find_numeric() -> str | None:
        for c in numeric:
            if c.lower() in q:
                return c
        return numeric[0] if numeric else None

    def _find_group() -> str | None:
        for c in categorical:
            if c.lower() in q:
                return c
        return categorical[0] if categorical else None

    # Row / column shape questions.
    if "how many row" in q or ("rows" in q and "how many" in q):
        return f"The dataset has {len(df):,} rows."
    if "column" in q or "field" in q:
        return f"Columns ({len(df.columns)}): {', '.join(df.columns)}."

    col = _find_numeric()
    if col:
        if any(w in q for w in ("average", "mean", "avg")):
            return f"The average {col} is {df[col].mean():,.2f}."
        if any(w in q for w in ("max", "highest", "most", "largest", "peak", "top")):
            grp = _find_group()
            if grp:
                top = df.groupby(grp)[col].sum().sort_values(ascending=False)
                lead = top.index[0]
                return f"By {grp}, '{lead}' has the highest total {col} ({top.iloc[0]:,.0f})."
            return f"The maximum {col} is {df[col].max():,.0f}."
        if any(w in q for w in ("min", "lowest", "least", "smallest")):
            return f"The minimum {col} is {df[col].min():,.0f}."
        if any(w in q for w in ("sum", "total")):
            return f"The total {col} is {df[col].sum():,.0f}."

    # Generic descriptive fallback.
    return (
        f"{label}\n\nThis dataset has {len(df):,} rows and {len(df.columns)} columns "
        f"({', '.join(df.columns)}). Set GEMINI_API_KEY to enable full "
        "natural-language answers; offline I can report totals, averages, "
        "maxima/minima and row/column counts."
    )


# ── Route ─────────────────────────────────────────────────────────────────────

@bp.route("/ext/chat/ask", methods=["POST"])
def ask():
    from auth.middleware import current_user
    from tenancy.access import can_access

    user = current_user()
    if user is None:
        return jsonify(error="Not authenticated."), 401

    payload = request.get_json(silent=True) or {}
    slug = str(payload.get("slug", "")).strip()
    question = str(payload.get("question", "")).strip()[:_MAX_QUESTION_LEN]

    if not slug or not question:
        return jsonify(error="Both 'slug' and 'question' are required."), 400
    if not (user.is_admin or can_access(user, slug)):
        return jsonify(error="You do not have access to this dashboard."), 403

    provider = _DATA_PROVIDERS.get(slug)
    if provider is None:
        return jsonify(
            answer="Chat is not available for this dashboard yet.",
            source="local",
            dataset=slug,
        )

    try:
        df, label = provider()
    except Exception as exc:
        logger.warning("Chat data provider failed for %s: %s", slug, exc)
        return jsonify(error="Could not load this dashboard's data."), 503

    answer = _gemini_answer(df, question, label)
    source = "gemini" if answer is not None else "local"
    if answer is None:
        answer = _local_answer(df, question, label)

    return jsonify(answer=answer, source=source, dataset=slug)


def register_chat(server) -> None:
    """Attach the chat blueprint to the Flask ``server`` (idempotent)."""
    if "ext_chat" not in server.blueprints:
        server.register_blueprint(bp)
