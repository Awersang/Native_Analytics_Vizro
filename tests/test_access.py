"""Access-control logic: who can see / open which dashboard."""

from tenancy.access import accessible_slugs, can_access, resolve_client_dataset
from tenancy.models import User

ALL = ["timeline", "breakdown", "bq_sample"]


def test_admin_sees_everything():
    admin = User(uid="a", email="a@x", role="admin")
    assert accessible_slugs(admin, ALL) == ALL
    assert can_access(admin, "anything") is True


def test_user_limited_to_grants():
    user = User(uid="u", email="u@x", role="user", dashboard_slugs=["timeline"])
    assert accessible_slugs(user, ALL) == ["timeline"]
    assert can_access(user, "timeline") is True
    assert can_access(user, "breakdown") is False


def test_grant_order_follows_registry():
    user = User(uid="u", email="u@x", role="user", dashboard_slugs=["bq_sample", "timeline"])
    # preserves registry order, not grant order
    assert accessible_slugs(user, ALL) == ["timeline", "bq_sample"]


def test_dataset_convention(monkeypatch):
    from tenancy import users as users_mod

    # No client override -> conventional name
    user = User(uid="u", email="u@x", role="user", client_id="acme")

    class _Store:
        def get_client(self, cid):
            return None

    monkeypatch.setattr(users_mod, "get_user_store", lambda: _Store())
    assert resolve_client_dataset(user) == "client_acme"
