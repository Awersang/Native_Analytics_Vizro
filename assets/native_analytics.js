/* Native Analytics — dashboard chrome behaviour.
 *
 * Keep the left control/navigation panel from auto-collapsing when the user
 * switches pages inside a dashboard.
 *
 * Vizro registers a clientside callback `dashboard.collapse_nav_panel` that
 * fires whenever the collapse icon is (re)created. Because the icon is rebuilt
 * on every page change with `n_clicks = null`, Vizro's default implementation
 * runs its "small viewport" branch and collapses the panel on each navigation
 * (it treats any window smaller than 768px in either dimension as mobile).
 *
 * We replace it with a version that does nothing on (re)render and only toggles
 * in response to a genuine click, so the panel keeps its open state across
 * page changes. Manual show/hide via the icon still works.
 */
(function () {
  var COLLAPSE_STORAGE_KEY = "na-nav-collapsed";
  var collapseSyncing = false;

  function isNavCollapsed() {
    try {
      return localStorage.getItem(COLLAPSE_STORAGE_KEY) === "true";
    } catch (e) {
      return false;
    }
  }

  function setNavCollapsed(collapsed) {
    try {
      localStorage.setItem(COLLAPSE_STORAGE_KEY, collapsed ? "true" : "false");
    } catch (e) {
      // localStorage unavailable; collapse state simply won't persist.
    }
  }

  // Vizro rebuilds the nav panel as freshly opened (is_open = true) on every
  // page change. If the user had collapsed it, replay a click on the collapse
  // icon so the real Dash callback (and its width animation) restores the
  // collapsed state, keeping it in sync across page navigation.
  function syncNavCollapseState() {
    if (collapseSyncing) {
      return;
    }
    var collapseEl = document.getElementById("collapse-left-side");
    var icon = document.getElementById("collapse-icon");
    if (!collapseEl || !icon) {
      return;
    }
    var isOpen = collapseEl.classList.contains("show");
    var shouldBeOpen = !isNavCollapsed();
    if (isOpen !== shouldBeOpen) {
      collapseSyncing = true;
      icon.click();
      setTimeout(function () {
        collapseSyncing = false;
      }, 400);
    }
  }

  function escapeRegExp(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function currentDashboardPrefix() {
    var mountPrefix = "/app";
    var pattern = new RegExp(
      "^" + escapeRegExp(mountPrefix.replace(/\/$/, "")) + "/d/([^/]+)"
    );
    var match = window.location.pathname.match(pattern);
    return match ? mountPrefix.replace(/\/$/, "") + "/d/" + match[1] : null;
  }

  function navContainer(node) {
    return (
      node.closest(
        ".accordion-item, .mantine-Accordion-item, .nav-item, li, [role='treeitem']"
      ) || node
    );
  }

  function applyNavScope() {
    var dashboardPrefix = currentDashboardPrefix();
    var links = document.querySelectorAll("#nav-bar a[href], a.nav-link[href]");

    links.forEach(function (link) {
      var href = link.getAttribute("href") || "";
      var isDashboardRoute = href.indexOf("/d/") !== -1;
      var shouldShow =
        !dashboardPrefix ||
        !isDashboardRoute ||
        href === dashboardPrefix ||
        href.indexOf(dashboardPrefix + "/") === 0;
      var target = navContainer(link);

      target.style.display = shouldShow ? "" : "none";
      link.setAttribute("aria-hidden", shouldShow ? "false" : "true");
    });
  }

  function patch() {
    var dc = window.dash_clientside;
    if (!dc || !dc.dashboard) {
      return false;
    }
    dc.dashboard.collapse_nav_panel = function (n_clicks, is_open) {
      // No real click yet (initial render or page change) → leave as-is.
      if (!n_clicks) {
        throw window.dash_clientside.PreventUpdate;
      }
      // The new collapsed state is the inverse of is_open before the toggle,
      // i.e. exactly `is_open` (open -> collapsed, collapsed -> open).
      setNavCollapsed(is_open);
      if (is_open) {
        return [
          false,
          {
            transform: "rotate(180deg)",
            transition: "transform 0.35s ease-in-out",
            marginLeft: "8px",
          },
          "Show Menu",
        ];
      }
      return [
        true,
        {
          transform: "rotate(0deg)",
          transition: "transform 0.35s ease-in-out",
        },
        "Hide Menu",
      ];
    };
    return true;
  }

  var lastPath = window.location.pathname;
  var observeNav = function () {
    applyNavScope();
    syncNavCollapseState();

    var observer = new MutationObserver(function () {
      applyNavScope();
      syncNavCollapseState();
      if (window.location.pathname !== lastPath) {
        lastPath = window.location.pathname;
        applyNavScope();
        syncNavCollapseState();
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["href", "class"],
    });

    ["pushState", "replaceState"].forEach(function (method) {
      var original = history[method];
      if (typeof original !== "function") {
        return;
      }
      history[method] = function () {
        var result = original.apply(this, arguments);
        applyNavScope();
        return result;
      };
    });

    window.addEventListener("popstate", applyNavScope);
  };

  // The Vizro bundle may load before or after this asset, so retry briefly
  // until the `dashboard` clientside namespace exists, then stop.
  observeNav();
  if (!patch()) {
    var tries = 0;
    var iv = setInterval(function () {
      if (patch() || ++tries > 50) {
        clearInterval(iv);
      }
    }, 100);
  }
})();
