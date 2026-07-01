"""Nav-rail scoping (ScopedNavBar in app.py).

The icon rail must show only the *active* dashboard's own pages, computed
fresh on every page render. The original bug this guards against: every
dashboard's pages were visible at once on first load, and only narrowed down
client-side after a page was clicked — too late, and the wrong layer to fix
it in. These tests build the navigation the same way app.py does and assert
the rendered rail's contents directly, with no browser involved.
"""

import app as appmod


def _visible_pages(active_page_id):
    """Return the set of page ids actually rendered in the nav rail for
    `active_page_id`, by mapping each rendered NavLink's id back to the page
    it covers via the source NavLink models (NavLink.id is an opaque,
    auto-generated model id — unrelated to the page id(s) it links to;
    NavLink.pages is the actual page-id list)."""
    nav = appmod._build_navigation()
    # Mirrors what vm.Dashboard.pre_build()'s set_navigation_pages validator
    # does for the real app: Navigation.pre_build() requires `pages` to be
    # non-empty before it will build its nav_selector.
    nav.pages = [page.id for pages in appmod._PAGES_BY_SLUG.values() for page in pages]
    nav.pre_build()
    items = nav.nav_selector.items  # full, unfiltered source list
    built = nav.build(active_page_id=active_page_id)
    navbar = built["nav-bar"]
    rendered_ids = {child.id for child in navbar.children}
    return {item.pages[0] for item in items if item.id in rendered_ids}


def test_rail_shows_only_the_active_dashboards_pages():
    amazon_ids = {page.id for page in appmod._PAGES_BY_SLUG["amazon_2026"]}
    timeline_ids = {page.id for page in appmod._PAGES_BY_SLUG["timeline"]}

    shown = _visible_pages("amazon-2026-overview")
    assert shown == amazon_ids
    assert not (shown & timeline_ids)


def test_rail_shows_only_a_different_dashboards_pages_when_that_one_is_active():
    timeline_ids = {page.id for page in appmod._PAGES_BY_SLUG["timeline"]}
    amazon_ids = {page.id for page in appmod._PAGES_BY_SLUG["amazon_2026"]}

    shown = _visible_pages("timeline")
    assert shown == timeline_ids
    assert not (shown & amazon_ids)


def test_rail_is_empty_for_a_page_outside_any_dashboard():
    """The Client-Hub-redirect placeholder page ('overview', path '/overview')
    belongs to no dashboard. The rail must render nothing here — never fall
    back to showing every page, which would silently reproduce the original
    "see every dashboard's pages at once" bug."""
    assert _visible_pages("overview") == set()


def test_rail_is_empty_for_an_unknown_page_id():
    assert _visible_pages("not-a-real-page-id") == set()


def test_every_amazon_2026_page_link_is_only_ever_amazon_2026_pages():
    """Each of amazon_2026's own pages, individually, must scope to exactly
    amazon_2026's page set — not a subset, not a superset, and never another
    dashboard's pages (the strict client/dashboard separation this exists to
    enforce)."""
    amazon_ids = {page.id for page in appmod._PAGES_BY_SLUG["amazon_2026"]}
    for page_id in amazon_ids:
        assert _visible_pages(page_id) == amazon_ids
