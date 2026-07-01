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

  // The saved-views and chat panels live OUTSIDE Dash's #page-container (the
  // saved-views shell is a sibling of the whole Vizro layout; the chat root is
  // appended to <body>), so navigation never destroys them. We used to
  // appendChild them into Vizro's #nav-control-panel, but Dash rebuilds that
  // subtree on every page change — React then destroyed or misplaced the
  // grafted node, leaving an empty panel and a dock button stuck "open". Now we
  // leave them in place and overlay them on the left column with position:fixed,
  // measuring the live nav-control-panel box so the overlay tracks the header
  // height, nav-rail width, and responsive zoom.
  function positionSidebarPanels() {
    var anchor = sidebarHost();
    if (!anchor) {
      return;
    }
    var rect = anchor.getBoundingClientRect();
    // Collapsed/hidden (or mid-animation): panels are hidden too, so keep the
    // last good geometry rather than snapping the overlay to a zero-size box.
    if (rect.width < 10 || rect.height < 10) {
      return;
    }
    [chatPanelRoot(), viewsPanel()].forEach(function (panel) {
      if (!panel) {
        return;
      }
      panel.style.top = rect.top + "px";
      panel.style.left = rect.left + "px";
      panel.style.width = rect.width + "px";
      panel.style.height = rect.height + "px";
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

  // Set while ensureSidebarOpen() synthesizes a click to expand the panel for
  // a specific mode, so the collapse-icon click listener below doesn't treat
  // a slow open transition as the user collapsing it and revert to "menu".
  var openingSidebarForMode = false;

  function ensureSidebarOpen() {
    if (!isSidebarOpen()) {
      var icon = sidebarIcon();
      if (icon) {
        openingSidebarForMode = true;
        icon.click();
        openingSidebarForMode = false;
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
    // Only "menu" if Vizro's own control panel is actually showing. If no panel
    // is visible (e.g. a panel failed to render), return null so no dock button
    // is wrongly lit as "open".
    var controlPanel = document.getElementById("control-panel");
    if (controlPanel && controlPanel.style.display !== "none") {
      return "menu";
    }
    return null;
  }

  function showSidebarMode(mode) {
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
    positionSidebarPanels();
    setTimeout(function () {
      positionSidebarPanels();
      syncMenuButtonState();
    }, 80);
    // Re-measure after the collapse open-animation settles (opening from a
    // collapsed sidebar grows the column from 0 → full width over ~350ms).
    setTimeout(positionSidebarPanels, 420);
  }

  window.NativeAnalyticsSidebar = {
    show: showSidebarMode,
    close: closeSidebar,
    sync: function () {
      positionSidebarPanels();
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

  // Nav-rail scoping (which dashboard's pages are visible) is computed
  // server-side, per page render, by app.py's ScopedNavBar — no DOM-querying
  // or MutationObserver-based client-side filtering needed here at all.

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
        var openedForMode = openingSidebarForMode;
        manualToggleInProgress = true;
        setTimeout(function () {
          manualToggleInProgress = false;
          if (!isSidebarOpen() && !openedForMode) {
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
    positionSidebarPanels();
    syncNavCollapseState();

    // NB: deliberately no positionSidebarPanels() here — this fires on every
    // DOM mutation (Plotly churns the DOM heavily while charts render) and
    // getBoundingClientRect forces a reflow. Geometry only changes on
    // navigation/resize/open, which are handled explicitly below.
    var observer = new MutationObserver(function () {
      syncNavCollapseState();
      syncMenuButtonState();
      if (window.location.pathname !== lastPath) {
        lastPath = window.location.pathname;
        activeSidebarMode = "menu";
        showChatPanel(false);
        showViewsPanel(false);
        showVizroControlPanel(true);
        positionSidebarPanels();
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
        positionSidebarPanels();
        syncMenuButtonState();
        return result;
      };
    });

    window.addEventListener("resize", positionSidebarPanels);

    window.addEventListener("popstate", function () {
      activeSidebarMode = "menu";
      showChatPanel(false);
      showViewsPanel(false);
      showVizroControlPanel(true);
      positionSidebarPanels();
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
