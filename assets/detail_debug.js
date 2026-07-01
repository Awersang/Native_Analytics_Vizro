/* TEMPORARY DEBUG — detail-section collapse investigation (v2).
 * Delete this file once the root cause is found. Logs to the BROWSER console.
 *
 * The collapse fires on a CLICK with NO server round-trip. This version pins
 * down which of the two remaining mechanisms it is:
 *   [DASH-REQ]/[DASH-RESP]  server callback (patched fetch)
 *   [SET-PROPS]             a clientside callback / dash-renderer writing a prop
 *   [REVERT]                content-content became the placeholder (+ what fired
 *                           in the preceding 300ms, and a stack trace)
 *   [CLICK]                 what you clicked inside the details
 *   [LOADING]               the section's dcc.Loading wrapper toggled
 */
(function () {
  "use strict";

  var CONTENT_IDS = [
    "amazon-2026-ta-topicarea-details-content",
    "amazon-2026-narrative-details-content",
    "amazon-2026-publisher-details-content",
    "amazon-2026-campaign-details-content",
  ];
  var SECTION_IDS = [
    "amazon-2026-topic-area-details-section",
    "amazon-2026-narratives-detail-section",
    "amazon-2026-publishers-details-section",
    "amazon-2026-campaign-details-section",
  ];
  var PLACEHOLDER_RE = /Select (a|an) .* to see details/i;

  function stamp() {
    return new Date().toISOString().substr(11, 12);
  }

  // Ring buffer of recent events so a REVERT can report what preceded it.
  var recent = [];
  function note(kind, detail) {
    recent.push({ t: Date.now(), kind: kind, detail: detail });
    if (recent.length > 40) recent.shift();
  }
  function precededBy(ms) {
    var cutoff = Date.now() - ms;
    return recent.filter(function (e) { return e.t >= cutoff; }).map(function (e) { return e.kind + "(" + e.detail + ")"; });
  }

  // --- Patch fetch (server callbacks) -------------------------------------
  var origFetch = window.fetch;
  window.fetch = function (input, init) {
    var url = typeof input === "string" ? input : (input && input.url) || "";
    if (url.indexOf("_dash-update-component") !== -1 && init && init.body) {
      try {
        var body = JSON.parse(init.body);
        var changed = body.changedPropIds || Object.keys(body.inputs || {});
        note("REQ", JSON.stringify(changed));
        console.log("%c[DASH-REQ " + stamp() + "] trigger:", "color:#e67e22", changed);
      } catch (e) {}
    }
    return origFetch.apply(this, arguments);
  };

  // --- Patch dash_clientside.set_props (clientside callbacks / renderer) ---
  function patchSetProps() {
    var dc = window.dash_clientside;
    if (!dc || !dc.set_props || dc.__na_patched) return false;
    var orig = dc.set_props;
    dc.set_props = function (id, props) {
      try {
        var idStr = typeof id === "string" ? id : JSON.stringify(id);
        var keys = props ? Object.keys(props) : [];
        note("SET_PROPS", idStr + ":" + keys.join(","));
        console.log("%c[SET-PROPS " + stamp() + "]", "color:#f1c40f", idStr, keys);
      } catch (e) {}
      return orig.apply(this, arguments);
    };
    dc.__na_patched = true;
    return true;
  }
  if (!patchSetProps()) {
    var tries = 0;
    var iv = setInterval(function () { if (patchSetProps() || ++tries > 100) clearInterval(iv); }, 100);
  }

  // --- Watch content divs for reverting to placeholder --------------------
  function isPlaceholder(node) {
    return !!node && PLACEHOLDER_RE.test(node.textContent || "");
  }
  var lastState = {};
  new MutationObserver(function () {
    CONTENT_IDS.forEach(function (id) {
      var node = document.getElementById(id);
      if (!node) return;
      var ph = isPlaceholder(node);
      if (ph && lastState[id] === false) {
        console.warn("%c[REVERT " + stamp() + "] " + id + " -> PLACEHOLDER", "color:#e74c3c;font-weight:bold");
        console.warn("  preceded by (last 300ms):", precededBy(300));
        console.trace("collapse stack");
      }
      lastState[id] = ph;
    });
  }).observe(document.body, { childList: true, subtree: true, characterData: true });

  // --- Watch the section's dcc.Loading wrapper class toggles --------------
  new MutationObserver(function (muts) {
    muts.forEach(function (m) {
      if (m.type !== "attributes" || m.attributeName !== "class") return;
      var el = m.target;
      if (!el.className || typeof el.className !== "string") return;
      if (el.className.indexOf("dash-loading") === -1 && el.className.indexOf("_dash-loading") === -1) return;
      var sec = SECTION_IDS.some(function (sid) { var s = document.getElementById(sid); return s && s.contains(el); });
      if (sec) { note("LOADING", el.className); console.log("%c[LOADING " + stamp() + "]", "color:#1abc9c", el.className); }
    });
  }).observe(document.body, { attributes: true, subtree: true, attributeFilter: ["class"] });

  // --- Log clicks inside details ------------------------------------------
  document.addEventListener("click", function (e) {
    var t = e.target;
    var inside = t.closest && t.closest(".amazon-publishers-detail-content, .amazon-publishers-details");
    if (!inside) return;
    var desc = t.tagName + (t.id ? "#" + t.id : "");
    note("CLICK", desc);
    console.log("%c[CLICK " + stamp() + "] inside details:", "color:#3498db", desc, t);
  }, true);

  console.log("%c[DETAIL-DEBUG v2] probe loaded", "color:#9b59b6;font-weight:bold");
})();
