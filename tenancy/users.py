"""
User / client / grant persistence.

Two interchangeable backends implement the same ``UserStore`` protocol:

* ``InMemoryUserStore`` — seeded with fixture data, used whenever
  ``AUTH_ENABLED=false`` (local development). No GCP needed.
* ``FirestoreUserStore`` — Firestore (Native mode) collections, used in
  production. ``google-cloud-firestore`` is imported lazily so dev never needs
  it installed.

Get the active store via ``get_user_store()``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from config import settings
from tenancy.models import AccessRequest, AuditEvent, Client, UsageEvent, User


class UserStore(Protocol):
    # Users
    def get_user(self, uid: str) -> User | None: ...
    def get_user_by_email(self, email: str) -> User | None: ...
    def list_users(self) -> list[User]: ...
    def upsert_user(self, user: User) -> None: ...
    def delete_user(self, uid: str) -> None: ...

    # Clients
    def get_client(self, client_id: str) -> Client | None: ...
    def list_clients(self) -> list[Client]: ...
    def upsert_client(self, client: Client) -> None: ...
    def set_client_dashboards(self, client_id: str, dashboard_slugs: list[str]) -> None: ...

    # Grants
    def set_grants(self, uid: str, dashboard_slugs: list[str]) -> None: ...
    def set_user_client(self, uid: str, client_id: str) -> None: ...

    # Access requests
    def add_access_request(self, req: AccessRequest) -> None: ...
    def list_access_requests(self, status: str | None = None) -> list[AccessRequest]: ...
    def set_request_status(self, request_id: str, status: str) -> None: ...

    # Audit log
    def add_audit_event(self, event: AuditEvent) -> None: ...
    def list_audit_events(self, limit: int = 100) -> list[AuditEvent]: ...

    # Usage analytics
    def add_usage_event(self, event: UsageEvent) -> None: ...
    def list_usage_events(self, limit: int = 1000) -> list[UsageEvent]: ...


# ── In-memory backend (dev) ──────────────────────────────────────────────────
class InMemoryUserStore:
    """Non-persistent store seeded with fixture users and clients."""

    def __init__(self, users: list[User] | None = None, clients: list[Client] | None = None):
        self._users: dict[str, User] = {u.uid: u for u in (users or [])}
        self._clients: dict[str, Client] = {c.id: c for c in (clients or [])}
        self._requests: dict[str, AccessRequest] = {}
        self._audit: list[AuditEvent] = []
        self._usage: list[UsageEvent] = []

    def get_user(self, uid: str) -> User | None:
        return self._users.get(uid)

    def get_user_by_email(self, email: str) -> User | None:
        email = email.lower()
        return next((u for u in self._users.values() if u.email.lower() == email), None)

    def list_users(self) -> list[User]:
        return list(self._users.values())

    def upsert_user(self, user: User) -> None:
        self._users[user.uid] = user

    def delete_user(self, uid: str) -> None:
        self._users.pop(uid, None)

    def get_client(self, client_id: str) -> Client | None:
        return self._clients.get(client_id)

    def list_clients(self) -> list[Client]:
        return list(self._clients.values())

    def upsert_client(self, client: Client) -> None:
        self._clients[client.id] = client

    def set_client_dashboards(self, client_id: str, dashboard_slugs: list[str]) -> None:
        client = self._clients.get(client_id)
        if client is not None:
            client.dashboard_slugs = list(dashboard_slugs)

    def set_grants(self, uid: str, dashboard_slugs: list[str]) -> None:
        user = self._users.get(uid)
        if user is not None:
            user.dashboard_slugs = list(dashboard_slugs)

    def set_user_client(self, uid: str, client_id: str) -> None:
        user = self._users.get(uid)
        if user is not None:
            user.client_id = client_id

    def add_access_request(self, req: AccessRequest) -> None:
        self._requests[req.id] = req

    def list_access_requests(self, status: str | None = None) -> list[AccessRequest]:
        reqs = list(self._requests.values())
        if status is not None:
            reqs = [r for r in reqs if r.status == status]
        return sorted(reqs, key=lambda r: r.created_at, reverse=True)

    def set_request_status(self, request_id: str, status: str) -> None:
        req = self._requests.get(request_id)
        if req is not None:
            req.status = status  # type: ignore[assignment]

    def add_audit_event(self, event: AuditEvent) -> None:
        self._audit.append(event)
        # Keep memory bounded in long-running dev sessions.
        if len(self._audit) > 2000:
            self._audit = self._audit[-2000:]

    def list_audit_events(self, limit: int = 100) -> list[AuditEvent]:
        events = sorted(self._audit, key=lambda e: e.created_at, reverse=True)
        return events[:limit]

    def add_usage_event(self, event: UsageEvent) -> None:
        self._usage.append(event)
        if len(self._usage) > 5000:
            self._usage = self._usage[-5000:]

    def list_usage_events(self, limit: int = 1000) -> list[UsageEvent]:
        events = sorted(self._usage, key=lambda e: e.created_at, reverse=True)
        return events[:limit]


# ── Firestore backend (prod) ─────────────────────────────────────────────────
class FirestoreUserStore:
    """Firestore-backed store. Collections: ``users`` and ``clients``."""

    USERS = "users"
    CLIENTS = "clients"
    REQUESTS = "access_requests"
    AUDIT = "audit_events"
    USAGE = "usage_events"

    def __init__(self, project_id: str | None = None):
        from google.cloud import firestore  # lazy import

        self._db = firestore.Client(
            project=project_id or settings.gcp_project_id or None,
            database=settings.firestore_database,
        )

    def get_user(self, uid: str) -> User | None:
        snap = self._db.collection(self.USERS).document(uid).get()
        return User.from_doc(snap.id, snap.to_dict()) if snap.exists else None

    def get_user_by_email(self, email: str) -> User | None:
        docs = self._db.collection(self.USERS).where("email", "==", email.lower()).limit(1).stream()
        for snap in docs:
            return User.from_doc(snap.id, snap.to_dict())
        return None

    def list_users(self) -> list[User]:
        return [User.from_doc(s.id, s.to_dict()) for s in self._db.collection(self.USERS).stream()]

    def upsert_user(self, user: User) -> None:
        self._db.collection(self.USERS).document(user.uid).set(user.to_doc())

    def delete_user(self, uid: str) -> None:
        self._db.collection(self.USERS).document(uid).delete()

    def get_client(self, client_id: str) -> Client | None:
        snap = self._db.collection(self.CLIENTS).document(client_id).get()
        return Client.from_doc(snap.id, snap.to_dict()) if snap.exists else None

    def list_clients(self) -> list[Client]:
        return [Client.from_doc(s.id, s.to_dict()) for s in self._db.collection(self.CLIENTS).stream()]

    def upsert_client(self, client: Client) -> None:
        self._db.collection(self.CLIENTS).document(client.id).set(client.to_doc())

    def set_client_dashboards(self, client_id: str, dashboard_slugs: list[str]) -> None:
        self._db.collection(self.CLIENTS).document(client_id).update(
            {"dashboard_slugs": list(dashboard_slugs)}
        )

    def set_grants(self, uid: str, dashboard_slugs: list[str]) -> None:
        self._db.collection(self.USERS).document(uid).update({"dashboard_slugs": list(dashboard_slugs)})

    def set_user_client(self, uid: str, client_id: str) -> None:
        self._db.collection(self.USERS).document(uid).update({"client_id": client_id})

    def add_access_request(self, req: AccessRequest) -> None:
        self._db.collection(self.REQUESTS).document(req.id).set(req.to_doc())

    def list_access_requests(self, status: str | None = None) -> list[AccessRequest]:
        col = self._db.collection(self.REQUESTS)
        stream = col.where("status", "==", status).stream() if status is not None else col.stream()
        reqs = [AccessRequest.from_doc(s.id, s.to_dict()) for s in stream]
        return sorted(reqs, key=lambda r: r.created_at, reverse=True)

    def set_request_status(self, request_id: str, status: str) -> None:
        self._db.collection(self.REQUESTS).document(request_id).update({"status": status})

    def add_audit_event(self, event: AuditEvent) -> None:
        self._db.collection(self.AUDIT).document(event.id).set(event.to_doc())

    def list_audit_events(self, limit: int = 100) -> list[AuditEvent]:
        from google.cloud import firestore  # lazy import

        docs = (
            self._db.collection(self.AUDIT)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [AuditEvent.from_doc(s.id, s.to_dict()) for s in docs]

    def add_usage_event(self, event: UsageEvent) -> None:
        self._db.collection(self.USAGE).document(event.id).set(event.to_doc())

    def list_usage_events(self, limit: int = 1000) -> list[UsageEvent]:
        from google.cloud import firestore  # lazy import

        docs = (
            self._db.collection(self.USAGE)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [UsageEvent.from_doc(s.id, s.to_dict()) for s in docs]


@lru_cache
def get_user_store() -> UserStore:
    """Return the active user store based on configuration.

    In dev (auth disabled) we use an in-memory store seeded from fixtures so the
    admin panel is fully functional without any GCP dependency.
    """
    if settings.auth_enabled:
        return FirestoreUserStore()

    from auth.dev_users import seed_dev_store

    return seed_dev_store()
