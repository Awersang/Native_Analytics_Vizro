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
  var manualToggleInProgress = false;
  var activeSidebarMode = "menu";

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
    if (collapseSyncing || manualToggleInProgress) {
      return;
    }
    var collapseEl = document.getElementById("collapse-left-side");
    var icon = document.getElementById("collapse-icon");
    if (!collapseEl || !icon) {
      return;
    }
    // Ignore mid-transition mutations: Bootstrap adds a transient "collapsing"
    // class while animating, during which "show" is briefly absent/present
    // and doesn't reflect the settled state yet.
    if (collapseEl.classList.contains("collapsing")) {
      return;
    }
    var isOpen = collapseEl.classList.contains("show");
    var shouldBeOpen = !isNavCollapsed();
    if (isOpen !== shouldBeOpen) {
      collapseSyncing = true;
      icon.click();
      setTimeout(function () {
        collapseSyncing = false;
        syncMenuButtonState();
      }, 400);
    }
    syncMenuButtonState();
  }

  function syncMenuButtonState() {
    var collapseEl = document.getElementById("collapse-left-side");
    var isOpen =
      !!collapseEl &&
      collapseEl.classList.contains("show") &&
      !collapseEl.classList.contains("collapsing");
    var mode = isOpen ? currentSidebarMode() : null;

    [
      ["na-menu-toggle", mode === "menu"],
      ["ext-chat-toggle", mode === "chat"],
      ["saved-views-toggle", mode === "views"],
    ].forEach(function (entry) {
      var button = document.getElementById(entry[0]);
      if (!button) {
        return;
      }
      button.classList.toggle("is-open", entry[1]);
      button.setAttribute("aria-pressed", entry[1] ? "true" : "false");
    });

    var menuButton = document.getElementById("na-menu-toggle");
    if (menuButton) {
      menuButton.setAttribute("title", isOpen && mode === "menu" ? "Hide menu" : "Show menu");
    }
  }

  function sidebarHost() {
    return document.getElementById("nav-control-panel");
  }

  function sidebarCollapse() {
    return document.getElementById("collapse-left-side");
  }

  function sidebarIcon() {
    return document.getElementById("collapse-icon");
  }

  function ensureSidebarPanelPlacement() {
    var host = sidebarHost();
    if (!host) {
      return;
    }
    ["ext-chat-root", "saved-views-panel"].forEach(function (id) {
      var panel = document.getElementById(id);
      if (panel && panel.parentNode !== host) {
        host.appendChild(panel);
      }
    });
  }

  function chatPanelRoot() {
    return document.getElementById("ext-chat-root");
  }

  function chatPanel() {
    return document.getElementById("ext-chat-panel");
  }

  function viewsPanel() {
    return document.getElementById("saved-views-panel");
  }

  function showChatPanel(show) {
    var root = chatPanelRoot();
    var panel = chatPanel();
    if (root) {
      root.classList.toggle("na-sidebar-panel-hidden", !show);
    }
    if (panel) {
      panel.classList.toggle("ext-chat-hidden", !show);
      panel.setAttribute("aria-hidden", show ? "false" : "true");
      if (show) {
        var input = panel.querySelector(".ext-chat-input");
        if (input) {
          setTimeout(function () {
            input.focus();
          }, 50);
        }
      }
    }
  }

  function showViewsPanel(show) {
    var panel = viewsPanel();
    if (panel) {
      panel.classList.toggle("na-sidebar-panel-hidden", !show);
      panel.setAttribute("aria-hidden", show ? "false" : "true");
    }
  }

  function showVizroControlPanel(show) {
    var panel = document.getElementById("control-panel");
    if (panel) {
      panel.style.display = show ? "" : "none";
      panel.setAttribute("aria-hidden", show ? "false" : "true");
    }
  }

  function isSidebarOpen() {
    var collapseEl = sidebarCollapse();
    return !!collapseEl && collapseEl.classList.contains("show");
  }

  function ensureSidebarOpen() {
    if (!isSidebarOpen()) {
      var icon = sidebarIcon();
      if (icon) {
        icon.click();
      }
    }
  }

  function closeSidebar() {
    activeSidebarMode = "menu";
    showChatPanel(false);
    showViewsPanel(false);
    showVizroControlPanel(true);
    if (isSidebarOpen()) {
      var icon = sidebarIcon();
      if (icon) {
        icon.click();
      }
    }
    setNavCollapsed(true);
    setTimeout(syncMenuButtonState, 450);
  }

  function currentSidebarMode() {
    var chatRoot = chatPanelRoot();
    var chat = chatPanel();
    var views = viewsPanel();
    if (
      chatRoot &&
      chat &&
      !chatRoot.classList.contains("na-sidebar-panel-hidden") &&
      !chat.classList.contains("ext-chat-hidden")
    ) {
      return "chat";
    }
    if (views && !views.classList.contains("na-sidebar-panel-hidden")) {
      return "views";
    }
    return "menu";
  }

  function showSidebarMode(mode) {
    ensureSidebarPanelPlacement();
    activeSidebarMode = mode;
    ensureSidebarOpen();
    if (mode === "chat") {
      showVizroControlPanel(false);
      showViewsPanel(false);
      showChatPanel(true);
    } else if (mode === "views") {
      showVizroControlPanel(false);
      showChatPanel(false);
      showViewsPanel(true);
    } else {
      showChatPanel(false);
      showViewsPanel(false);
      showVizroControlPanel(true);
      activeSidebarMode = "menu";
    }
    setNavCollapsed(false);
    setTimeout(syncMenuButtonState, 80);
  }

  window.NativeAnalyticsSidebar = {
    show: showSidebarMode,
    close: closeSidebar,
    sync: function () {
      ensureSidebarPanelPlacement();
      syncMenuButtonState();
    },
  };

  function handleSidebarDockClick(event) {
    var menuButton = event.target.closest && event.target.closest("#na-menu-toggle");
    var chatButton = event.target.closest && event.target.closest("#ext-chat-toggle");
    var viewsButton = event.target.closest && event.target.closest("#saved-views-toggle");

    if (menuButton) {
      event.preventDefault();
      if (isSidebarOpen() && currentSidebarMode() === "menu") {
        closeSidebar();
      } else {
        showSidebarMode("menu");
      }
      return true;
    }

    if (chatButton) {
      event.preventDefault();
      if (isSidebarOpen() && currentSidebarMode() === "chat") {
        closeSidebar();
      } else {
        showSidebarMode("chat");
      }
      return true;
    }

    if (viewsButton) {
      event.preventDefault();
      if (isSidebarOpen() && currentSidebarMode() === "views") {
        closeSidebar();
      } else {
        showSidebarMode("views");
      }
      return true;
    }

    return false;
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

  // A genuine user click on the collapse icon kicks off Bootstrap's collapse
  // transition. Suppress syncNavCollapseState() for the duration so it
  // doesn't see the transient mid-animation state and replay a click that
  // would cancel the user's toggle out.
  document.addEventListener(
    "click",
    function (event) {
      var icon = document.getElementById("collapse-icon");
      if (icon && (event.target === icon || icon.contains(event.target))) {
        manualToggleInProgress = true;
        setTimeout(function () {
          manualToggleInProgress = false;
          if (!isSidebarOpen()) {
            showChatPanel(false);
            showViewsPanel(false);
            showVizroControlPanel(true);
            activeSidebarMode = "menu";
          }
          syncMenuButtonState();
        }, 400);
      }

      handleSidebarDockClick(event);
    },
    true
  );

  var lastPath = window.location.pathname;
  var observeNav = function () {
    applyNavScope();
    ensureSidebarPanelPlacement();
    syncNavCollapseState();

    var observer = new MutationObserver(function () {
      applyNavScope();
      ensureSidebarPanelPlacement();
      syncNavCollapseState();
      syncMenuButtonState();
      if (window.location.pathname !== lastPath) {
        lastPath = window.location.pathname;
        applyNavScope();
        activeSidebarMode = "menu";
        showChatPanel(false);
        showViewsPanel(false);
        showVizroControlPanel(true);
        ensureSidebarPanelPlacement();
        syncNavCollapseState();
        syncMenuButtonState();
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
        ensureSidebarPanelPlacement();
        syncMenuButtonState();
        return result;
      };
    });

    window.addEventListener("popstate", function () {
      applyNavScope();
      activeSidebarMode = "menu";
      showChatPanel(false);
      showViewsPanel(false);
      showVizroControlPanel(true);
      ensureSidebarPanelPlacement();
      syncMenuButtonState();
    });
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
