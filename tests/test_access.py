"""Access-control logic: who can see / open which dashboard."""

from tenancy.access import accessible_slugs, can_access, resolve_client_dataset
from tenancy.models import User

ALL = ["timeline", "breakdown", "bq_sample"]


def test_admin_sees_everything():
    admin = User(uid="a", email="a@x", role="admin")
    assert accessible_slugs(admin, ALL) == ALL
    assert can_access(admin, "anything") is True


def test_company_user_inherits_company_dashboards(monkeypatch):
    from tenancy import users as users_mod
    from tenancy.models import Client

    class _Store:
        def get_client(self, cid):
            return Client(id=cid, name="ACME", dashboard_slugs=["timeline", "bq_sample"])

    monkeypatch.setattr(users_mod, "get_user_store", lambda: _Store())
    user = User(uid="u", email="u@x", role="user", client_id="acme")
    assert accessible_slugs(user, ALL) == ["timeline", "bq_sample"]
    assert can_access(user, "timeline") is True
    assert can_access(user, "breakdown") is False


def test_company_user_restrictions_only_remove_dashboards(monkeypatch):
    from tenancy import users as users_mod
    from tenancy.models import Client

    class _Store:
        def get_client(self, cid):
            return Client(id=cid, name="ACME", dashboard_slugs=["timeline", "bq_sample"])

    monkeypatch.setattr(users_mod, "get_user_store", lambda: _Store())
    user = User(
        uid="u",
        email="u@x",
        role="user",
        client_id="acme",
        restricted_dashboard_slugs=["bq_sample", "breakdown"],
    )
    assert accessible_slugs(user, ALL) == ["timeline"]
    assert can_access(user, "timeline") is True
    assert can_access(user, "bq_sample") is False


def test_operator_sees_only_their_cross_client_access(monkeypatch):
    from tenancy import users as users_mod
    from tenancy.models import Client

    clients = {
        "acme": Client(id="acme", name="ACME", dashboard_slugs=["timeline", "bq_sample"]),
        "globex": Client(id="globex", name="Globex", dashboard_slugs=["breakdown"]),
    }

    class _Store:
        def get_client(self, cid):
            return clients.get(cid)

    monkeypatch.setattr(users_mod, "get_user_store", lambda: _Store())
    operator = User(
        uid="op",
        email="op@x",
        role="operator",
        allowed_client_ids=["acme"],
    )
    assert accessible_slugs(operator, ALL) == ["timeline", "bq_sample"]
    assert can_access(operator, "timeline") is True
    assert can_access(operator, "breakdown") is False


def test_dataset_convention(monkeypatch):
    from tenancy import users as users_mod

    user = User(uid="u", email="u@x", role="user", client_id="acme")

    class _Store:
        def get_client(self, cid):
            return None

    monkeypatch.setattr(users_mod, "get_user_store", lambda: _Store())
    assert resolve_client_dataset(user) == "client_acme"
