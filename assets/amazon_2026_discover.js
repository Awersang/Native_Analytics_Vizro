/* Amazon 2026 — Discover page search bar UX.
 *
 * The search bar's clear (X) button only reflects the debounced Dash
 * "value" prop, which lags behind what's actually typed until blur/Enter.
 * Listening to the native "input" event keeps it in sync with every
 * keystroke instead, matching the Reference Publication clear button's
 * immediate responsiveness.
 *
 * Clicking anywhere inside the bar (not just squarely on the text) should
 * focus it, so a delegated click handler forwards focus to the input
 * whenever the wrap itself is clicked.
 */
(function () {
  "use strict";

  var WRAP_SELECTOR = ".amazon-discover-search-input-wrap";
  var INPUT_ID = "amazon-2026-discover-search";
  var CLEAR_ID = "amazon-2026-discover-search-clear";

  document.addEventListener("click", function (event) {
    var wrap = event.target.closest(WRAP_SELECTOR);
    if (!wrap) return;
    var input = document.getElementById(INPUT_ID);
    if (!input || input.contains(event.target)) return;
    var clear = document.getElementById(CLEAR_ID);
    if (clear && clear.contains(event.target)) return;
    input.focus();
  });

  document.addEventListener(
    "input",
    function (event) {
      if (event.target.id !== INPUT_ID) return;
      var clear = document.getElementById(CLEAR_ID);
      if (!clear) return;
      clear.classList.toggle("is-visible", !!event.target.value);
    },
    true
  );
})();
