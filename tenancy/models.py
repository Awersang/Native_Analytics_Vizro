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

Role = Literal["admin", "user"]
RequestStatus = Literal["pending", "approved", "denied"]


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
            dashboard_slugs=list(data.get("dashboard_slugs", [])),
        )

    def to_doc(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "bq_dataset": self.bq_dataset,
            "brand_name": self.brand_name,
            "accent_color": self.accent_color,
            "dashboard_slugs": self.dashboard_slugs,
        }


@dataclass
class User:
    """An authenticated principal.

    * ``role == "admin"`` → full access to every dashboard + the admin panel.
    * ``role == "user"``  → access derives mainly from the user's company
      (``client_id`` → ``Client.dashboard_slugs``). ``dashboard_slugs`` here are
      optional per-user *extra* grants layered on top of the company's set.
    """

    uid: str
    email: str
    role: Role = "user"
    client_id: str = ""
    display_name: str = ""
    # Slugs of dashboards this user may open (ignored for admins, who see all).
    dashboard_slugs: list[str] = field(default_factory=list)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def can_access(self, slug: str) -> bool:
        return self.is_admin or slug in self.dashboard_slugs

    @classmethod
    def from_doc(cls, doc_id: str, data: dict[str, Any]) -> "User":
        return cls(
            uid=doc_id,
            email=data.get("email", ""),
            role=data.get("role", "user"),
            client_id=data.get("client_id", ""),
            display_name=data.get("display_name", ""),
            dashboard_slugs=list(data.get("dashboard_slugs", [])),
        )

    def to_doc(self) -> dict[str, Any]:
        return {
            "email": self.email,
            "role": self.role,
            "client_id": self.client_id,
            "display_name": self.display_name,
            "dashboard_slugs": self.dashboard_slugs,
        }


@dataclass
class AccessRequest:
    """A user's self-service request for access to a dashboard.

    Created from the user panel and resolved (approved/denied) by an admin in
    the admin queue. ``id`` is deterministic per (uid, slug) so re-requesting
    the same dashboard updates the existing pending row rather than piling up.
    """

    uid: str
    email: str
    slug: str
    status: RequestStatus = "pending"
    created_at: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"{self.uid}__{self.slug}"

    @classmethod
    def from_doc(cls, doc_id: str, data: dict[str, Any]) -> "AccessRequest":
        return cls(
            id=doc_id,
            uid=data.get("uid", ""),
            email=data.get("email", ""),
            slug=data.get("slug", ""),
            status=data.get("status", "pending"),
            created_at=data.get("created_at", ""),
        )

    def to_doc(self) -> dict[str, Any]:
        return {
            "uid": self.uid,
            "email": self.email,
            "slug": self.slug,
            "status": self.status,
            "created_at": self.created_at,
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
