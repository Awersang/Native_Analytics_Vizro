"""
Fixture users and clients for local development (AUTH_ENABLED=false).

These seed the in-memory user store so the landing page, admin panel and
per-dashboard access control are all fully exercisable without Firebase or any
GCP project.
"""

from __future__ import annotations

from tenancy.models import Client, User
from tenancy.users import InMemoryUserStore

# A fake admin returned by the middleware whenever auth is disabled so that the
# whole app is reachable instantly during development.
DEV_ADMIN = User(
    uid="dev-admin",
    email="admin@dev.local",
    role="admin",
    display_name="Dev Admin",
)


def _fixture_clients() -> list[Client]:
    return [
        Client(
            id="acme",
            name="ACME Corp",
            bq_dataset="",
            brand_name="ACME Analytics",
            accent_color="#e6512b",
            dashboard_slugs=["timeline", "bq_sample"],
        ),
        Client(
            id="globex",
            name="Globex Inc",
            bq_dataset="",
            brand_name="Globex Insights",
            accent_color="#2b8ae6",
            dashboard_slugs=["breakdown"],
        ),
        Client(
            id="amazon",
            name="Amazon",
            bq_dataset="amazon_2026",
            brand_name="Amazon Intelligence",
            accent_color="#ff9900",
            dashboard_slugs=["amazon_2026"],
        ),
    ]


def _fixture_users() -> list[User]:
    return [
        DEV_ADMIN,
        User(
            uid="dev-user-acme",
            email="user@acme.local",
            role="user",
            client_id="acme",
            display_name="ACME Analyst",
        ),
        User(
            uid="dev-user-acme-2",
            email="user2@acme.local",
            role="user",
            client_id="acme",
            display_name="ACME Analyst 2",
        ),
        User(
            uid="dev-user-acme-3",
            email="user3@acme.local",
            role="user",
            client_id="acme",
            display_name="ACME Analyst 3",
        ),
        User(
            uid="dev-user-globex",
            email="user@globex.local",
            role="user",
            client_id="globex",
            display_name="Globex Analyst",
        ),
        User(
            uid="dev-user-globex-2",
            email="user2@globex.local",
            role="user",
            client_id="globex",
            display_name="Globex Analyst 2",
        ),
        User(
            uid="dev-user-globex-3",
            email="user3@globex.local",
            role="user",
            client_id="globex",
            display_name="Globex Analyst 3",
        ),
        User(
            uid="dev-user-amazon",
            email="user@amazon.local",
            role="user",
            client_id="amazon",
            display_name="Amazon Analyst",
        ),
        User(
            uid="dev-user-amazon-2",
            email="user2@amazon.local",
            role="user",
            client_id="amazon",
            display_name="Amazon Analyst 2",
        ),
        User(
            uid="dev-user-amazon-3",
            email="user3@amazon.local",
            role="user",
            client_id="amazon",
            display_name="Amazon Analyst 3",
        ),
        User(
            uid="dev-operator",
            email="operator@dev.local",
            role="operator",
            display_name="Platform Operator",
            allowed_client_ids=["acme", "amazon"],
        ),
    ]


def seed_dev_store() -> InMemoryUserStore:
    return InMemoryUserStore(users=_fixture_users(), clients=_fixture_clients())
