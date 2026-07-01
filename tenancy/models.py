"""
Domain models for users, clients (tenants) and dashboard access grants.

These are deliberately plain dataclasses so they are trivial to construct in
tests and in the in-memory dev store, and easy to (de)serialise to/from
Firestore documents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

Role = Literal["admin", "operator", "user"]


@dataclass
class Client:
    """A tenant. All of a client's data lives in its own BigQuery dataset."""

    id: str
    name: str
    # BigQuery dataset holding this client's data. If empty, the conventional
    # name f"{settings.bq_dataset_prefix}{id}" is used.
    bq_dataset: str = ""
    # Per-tenant branding shown on the user panel / account / admin shell.
    brand_name: str = ""
    accent_color: str = ""
    # Uploaded logo, stored inline as a data: URI (small images only - this
    # rides in the same Firestore doc as everything else, so no separate
    # file storage/bucket is needed for what's expected to be a handful of
    # KB per client).
    logo_data_uri: str = ""
    # Dashboards assigned to this company. Every user of the company inherits
    # access to these (this is the primary access-control mechanism).
    dashboard_slugs: list[str] = field(default_factory=list)

    @classmethod
    def from_doc(cls, doc_id: str, data: dict[str, Any]) -> "Client":
        return cls(
            id=doc_id,
            name=data.get("name", doc_id),
            bq_dataset=data.get("bq_dataset", ""),
            brand_name=data.get("brand_name", ""),
            accent_color=data.get("accent_color", ""),
            logo_data_uri=data.get("logo_data_uri", ""),
            dashboard_slugs=list(data.get("dashboard_slugs", [])),
        )

    def to_doc(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "bq_dataset": self.bq_dataset,
            "brand_name": self.brand_name,
            "accent_color": self.accent_color,
            "logo_data_uri": self.logo_data_uri,
            "dashboard_slugs": self.dashboard_slugs,
        }


@dataclass
class User:
    """An authenticated principal.

    * ``role == "admin"``    -> full access to every dashboard + the admin panel.
    * ``role == "operator"`` -> cross-client access to whole companies
      (``allowed_client_ids``), inheriting every dashboard those companies
      own - the same inheritance model as a company user's own client.
    * ``role == "user"``     -> access derives from the user's company
      (``client_id`` -> ``Client.dashboard_slugs``), minus any per-user
      restrictions.
    """

    uid: str
    email: str
    role: Role = "user"
    client_id: str = ""
    display_name: str = ""
    # Operator-only: companies whose dashboards they may access.
    allowed_client_ids: list[str] = field(default_factory=list)
    # Company-user-only dashboard removals from the inherited company scope.
    restricted_dashboard_slugs: list[str] = field(default_factory=list)
    # Legacy additive grants kept only long enough to surface migration gaps.
    legacy_dashboard_slugs: list[str] = field(default_factory=list, repr=False, compare=False)
    # Suspended accounts are denied at the auth layer (auth/middleware.py)
    # without losing their grants/audit history, unlike delete.
    disabled: bool = False

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_operator(self) -> bool:
        return self.role == "operator"

    @property
    def is_company_user(self) -> bool:
        return self.role == "user"

    @classmethod
    def from_doc(cls, doc_id: str, data: dict[str, Any]) -> "User":
        role = data.get("role", "user")
        client_id = data.get("client_id", "")
        return cls(
            uid=doc_id,
            email=data.get("email", ""),
            role=role,
            client_id=client_id if role == "user" else "",
            display_name=data.get("display_name", ""),
            allowed_client_ids=list(data.get("allowed_client_ids", [])),
            restricted_dashboard_slugs=list(data.get("restricted_dashboard_slugs", [])),
            legacy_dashboard_slugs=list(data.get("dashboard_slugs", [])),
            disabled=bool(data.get("disabled", False)),
        )

    def to_doc(self) -> dict[str, Any]:
        return {
            "email": self.email,
            "role": self.role,
            "client_id": self.client_id if self.role == "user" else "",
            "display_name": self.display_name,
            "allowed_client_ids": self.allowed_client_ids,
            "restricted_dashboard_slugs": self.restricted_dashboard_slugs,
            "disabled": self.disabled,
        }


@dataclass
class AuditEvent:
    """An admin-relevant action, recorded for the activity feed.

    Captures *who* did *what* to *which target* and *when* (ISO-8601 UTC).
    """

    actor_uid: str
    actor_email: str
    action: str
    target: str = ""
    detail: str = ""
    created_at: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = uuid4().hex

    @classmethod
    def from_doc(cls, doc_id: str, data: dict[str, Any]) -> "AuditEvent":
        return cls(
            id=doc_id,
            actor_uid=data.get("actor_uid", ""),
            actor_email=data.get("actor_email", ""),
            action=data.get("action", ""),
            target=data.get("target", ""),
            detail=data.get("detail", ""),
            created_at=data.get("created_at", ""),
        )

    def to_doc(self) -> dict[str, Any]:
        return {
            "actor_uid": self.actor_uid,
            "actor_email": self.actor_email,
            "action": self.action,
            "target": self.target,
            "detail": self.detail,
            "created_at": self.created_at,
        }


@dataclass
class UsageEvent:
    """A single dashboard open, used for admin usage analytics."""

    uid: str
    email: str
    slug: str
    created_at: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = uuid4().hex

    @classmethod
    def from_doc(cls, doc_id: str, data: dict[str, Any]) -> "UsageEvent":
        return cls(
            id=doc_id,
            uid=data.get("uid", ""),
            email=data.get("email", ""),
            slug=data.get("slug", ""),
            created_at=data.get("created_at", ""),
        )

    def to_doc(self) -> dict[str, Any]:
        return {
            "uid": self.uid,
            "email": self.email,
            "slug": self.slug,
            "created_at": self.created_at,
        }
