import os

import pytest

os.environ.setdefault("AUTH_ENABLED", "false")


@pytest.fixture(autouse=True)
def reset_user_store():
    """Clear the cached user-store singleton before and after every test.

    ``get_user_store()`` is decorated with ``@lru_cache``, which means a single
    ``InMemoryUserStore`` instance is reused for the whole test session.  Any
    mutations made by one test (creating users, changing grants, adding audit
    events) would bleed into subsequent tests.  Clearing the cache forces a
    fresh, fixture-seeded store to be created on the first call inside each
    test.
    """
    from tenancy import users as users_mod

    users_mod.get_user_store.cache_clear()
    yield
    users_mod.get_user_store.cache_clear()
