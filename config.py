"""
Central application configuration.

All settings are environment-driven so the same image runs locally and on
Cloud Run. In local development a `.env` file is loaded automatically (see
`.env.example`). In production, values come from Cloud Run env vars / Secret
Manager.

The single most important toggle is ``AUTH_ENABLED``:
  * ``false`` (default for local dev) → no Firebase, no login screen. A fake
    admin user is injected so every dashboard is reachable instantly.
  * ``true``  → Firebase / Identity Platform auth is enforced.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Environment ───────────────────────────────────────────────────────────
    env: Literal["dev", "staging", "prod"] = "dev"

    # Logging verbosity (standard library level name).
    log_level: str = "INFO"

    # ── Auth toggle ───────────────────────────────────────────────────────────
    auth_enabled: bool = False

    # When True, a user who authenticates with Firebase but has no store record
    # is auto-created with zero dashboard access (an admin grants access later).
    # When False, unprovisioned users are denied until an admin creates them.
    auto_provision_users: bool = False

    # Seconds to cache a verified session cookie's claims in-process, to avoid
    # re-verifying (and re-checking revocation) on every single request.
    session_verify_cache_ttl: int = 300
    # How often (seconds) to force a revocation check for a cached cookie.
    session_revocation_check_interval: int = 600

    # ── Flask / session ───────────────────────────────────────────────────────
    session_secret: str = "dev-insecure-secret-change-me"
    session_cookie_name: str = "na_session"

    # ── GCP ───────────────────────────────────────────────────────────────────
    gcp_project_id: str = ""
    gcp_region: str = "europe-west1"

    # ── Firebase / Identity Platform (only used when auth_enabled) ────────────
    firebase_api_key: str = ""
    firebase_auth_domain: str = ""
    # Path to the Firebase Admin service-account JSON. Empty → use ADC.
    firebase_credentials_file: str = ""
    # Firestore database ID. "(default)" is the default; set to your named DB if needed.
    firestore_database: str = "(default)"

    # ── BigQuery ──────────────────────────────────────────────────────────────
    # Each client's data lives in its own dataset, conventionally named
    # f"{bq_dataset_prefix}{client_id}". Override per-client in the `clients`
    # store when the convention does not hold.
    bq_dataset_prefix: str = "client_"
    # Dataset used by the bq_sample dashboard.
    bq_sample_project: str = "native-analytics-486522"
    bq_sample_dataset: str = "amazon_2025"
    bq_sample_table: str = "disinformation_timeline"

    # ── URL layout ────────────────────────────────────────────────────────────
    # Vizro (all dashboards) is mounted under this prefix so that "/" stays free
    # for our own landing / login pages.
    vizro_mount_prefix: str = "/app/"

    # Upper limit on bytes read per BigQuery query (safety net against runaway
    # queries from aggressive dashboard filters). 0 = unlimited (default for
    # dev). Set e.g. 10_000_000_000 (10 GB) for production.
    bq_max_bytes_billed: int = 0

    # ── Optional / detachable features ────────────────────────────────────────
    # "Chat with your data" widget (extensions/chat_with_data.py). Toggle off to
    # disable the feature without removing the code. Delete the `extensions/`
    # package + ``assets/ext_chat.*`` + the hook in app.py to remove it entirely.
    features_chat_enabled: bool = True
    # Gemini API key for the chat feature. Empty → a local pandas fallback
    # answers questions offline (no GCP creds needed in dev).
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    @property
    def is_dev(self) -> bool:
        return self.env == "dev"


@lru_cache
def get_settings() -> Settings:
    """Cached singleton accessor for application settings."""
    return Settings()


settings = get_settings()
