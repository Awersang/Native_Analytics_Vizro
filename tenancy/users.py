"""
User / client / grant persistence.

Two interchangeable backends implement the same ``UserStore`` protocol:

* ``InMemoryUserStore`` - seeded with fixture data, used whenever
  ``AUTH_ENABLED=false`` (local development). No GCP needed.
* ``FirestoreUserStore`` - Firestore (Native mode) collections, used in
  production. ``google-cloud-firestore`` is imported lazily so dev never needs
  it installed.

Get the active store via ``get_user_store()``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from config import settings
from tenancy.models import AuditEvent, Client, UsageEvent, User


class UserStore(Protocol):
    # Users
    def get_user(self, uid: str) -> User | None: ...
    def get_user_by_email(self, email: str) -> User | None: ...
    def list_users(self) -> list[User]: ...
    def upsert_user(self, user: User) -> None: ...
    def delete_user(self, uid: str) -> None: ...
    def reclaim_user(self, old_uid: str, new_uid: str) -> None: ...

    # Clients
    def get_client(self, client_id: str) -> Client | None: ...
    def list_clients(self) -> list[Client]: ...
    def upsert_client(self, client: Client) -> None: ...
    def delete_client(self, client_id: str) -> None: ...
    def set_client_dashboards(self, client_id: str, dashboard_slugs: list[str]) -> None: ...

    # User lifecycle
    def set_user_client(self, uid: str, client_id: str) -> None: ...
    def set_user_role(self, uid: str, role: str) -> None: ...
    def set_user_disabled(self, uid: str, disabled: bool) -> None: ...

    # Audit log
    def add_audit_event(self, event: AuditEvent) -> None: ...
    def list_audit_events(self, limit: int = 100) -> list[AuditEvent]: ...

    # Usage analytics
    def add_usage_event(self, event: UsageEvent) -> None: ...
    def list_usage_events(self, limit: int = 1000) -> list[UsageEvent]: ...


def _normalize_unique_dashboard_ownership(
    clients: list[Client], target_client_id: str, dashboard_slugs: list[str]
) -> list[Client]:
    """Return clients with unique dashboard ownership enforced.

    The target client's dashboards become exactly ``dashboard_slugs``. Any slug
    selected there is removed from every other client because a dashboard can
    belong to only one company at a time.
    """
    desired = list(dict.fromkeys(dashboard_slugs))
    desired_set = set(desired)
    normalized: list[Client] = []
    for client in clients:
        slugs = list(client.dashboard_slugs)
        if client.id == target_client_id:
            slugs = desired
        else:
            slugs = [slug for slug in slugs if slug not in desired_set]
        normalized.append(
            Client(
                id=client.id,
                name=client.name,
                bq_dataset=client.bq_dataset,
                brand_name=client.brand_name,
                accent_color=client.accent_color,
                logo_data_uri=client.logo_data_uri,
                dashboard_slugs=slugs,
            )
        )
    return normalized


class InMemoryUserStore:
    """Non-persistent store seeded with fixture users and clients."""

    def __init__(self, users: list[User] | None = None, clients: list[Client] | None = None):
        self._users: dict[str, User] = {u.uid: u for u in (users or [])}
        self._clients: dict[str, Client] = {c.id: c for c in (clients or [])}
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

    def reclaim_user(self, old_uid: str, new_uid: str) -> None:
        user = self._users.pop(old_uid, None)
        if user is not None:
            user.uid = new_uid
            self._users[new_uid] = user

    def get_client(self, client_id: str) -> Client | None:
        return self._clients.get(client_id)

    def list_clients(self) -> list[Client]:
        return list(self._clients.values())

    def upsert_client(self, client: Client) -> None:
        self._clients[client.id] = client

    def delete_client(self, client_id: str) -> None:
        self._clients.pop(client_id, None)

    def set_client_dashboards(self, client_id: str, dashboard_slugs: list[str]) -> None:
        normalized = _normalize_unique_dashboard_ownership(
            list(self._clients.values()), client_id, dashboard_slugs
        )
        self._clients = {client.id: client for client in normalized}

    def set_user_client(self, uid: str, client_id: str) -> None:
        user = self._users.get(uid)
        if user is not None:
            user.client_id = client_id

    def set_user_role(self, uid: str, role: str) -> None:
        user = self._users.get(uid)
        if user is not None:
            user.role = role  # type: ignore[assignment]

    def set_user_disabled(self, uid: str, disabled: bool) -> None:
        user = self._users.get(uid)
        if user is not None:
            user.disabled = disabled

    def add_audit_event(self, event: AuditEvent) -> None:
        self._audit.append(event)
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


class FirestoreUserStore:
    """Firestore-backed store. Collections: ``users`` and ``clients``."""

    USERS = "users"
    CLIENTS = "clients"
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

    def reclaim_user(self, old_uid: str, new_uid: str) -> None:
        old_ref = self._db.collection(self.USERS).document(old_uid)
        snap = old_ref.get()
        if not snap.exists:
            return
        batch = self._db.batch()
        batch.set(self._db.collection(self.USERS).document(new_uid), snap.to_dict())
        batch.delete(old_ref)
        batch.commit()

    def get_client(self, client_id: str) -> Client | None:
        snap = self._db.collection(self.CLIENTS).document(client_id).get()
        return Client.from_doc(snap.id, snap.to_dict()) if snap.exists else None

    def list_clients(self) -> list[Client]:
        return [Client.from_doc(s.id, s.to_dict()) for s in self._db.collection(self.CLIENTS).stream()]

    def upsert_client(self, client: Client) -> None:
        self._db.collection(self.CLIENTS).document(client.id).set(client.to_doc())

    def delete_client(self, client_id: str) -> None:
        self._db.collection(self.CLIENTS).document(client_id).delete()

    def set_client_dashboards(self, client_id: str, dashboard_slugs: list[str]) -> None:
        normalized = _normalize_unique_dashboard_ownership(
            self.list_clients(), client_id, dashboard_slugs
        )
        batch = self._db.batch()
        for client in normalized:
            batch.set(self._db.collection(self.CLIENTS).document(client.id), client.to_doc())
        batch.commit()

    def set_user_client(self, uid: str, client_id: str) -> None:
        self._db.collection(self.USERS).document(uid).update({"client_id": client_id})

    def set_user_role(self, uid: str, role: str) -> None:
        self._db.collection(self.USERS).document(uid).update({"role": role})

    def set_user_disabled(self, uid: str, disabled: bool) -> None:
        self._db.collection(self.USERS).document(uid).update({"disabled": disabled})

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
