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

  // The Vizro bundle may load before or after this asset, so retry briefly
  // until the `dashboard` clientside namespace exists, then stop.
  if (!patch()) {
    var tries = 0;
    var iv = setInterval(function () {
      if (patch() || ++tries > 50) {
        clearInterval(iv);
      }
    }, 100);
  }
})();
