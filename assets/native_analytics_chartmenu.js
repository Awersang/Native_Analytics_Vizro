/* Native Analytics — experimental chart context menu.
 *
 * Injects a small ⋮ button into the top-right corner of every .na-panel
 * on the Overview page. Clicking opens a dropdown with:
 *   - Copy Image to Clipboard
 *   - Download Image
 *   - Copy Data to Clipboard
 *   - Download Data
 *
 * A global toggle widget (fixed bottom-right) persists enabled/disabled
 * state in localStorage so it survives page navigation.
 */
(function () {
  "use strict";

  var STORAGE_KEY = "na-chart-menu-enabled";
  var OVERVIEW_ID = "amazon-2026-overview";
  var ATTR = "data-chart-menu";

  // -----------------------------------------------------------------------
  // Toggle state
  // -----------------------------------------------------------------------

  function isEnabled() {
    try {
      var v = localStorage.getItem(STORAGE_KEY);
      return v === null ? true : v === "true";
    } catch (e) {
      return true;
    }
  }

  function setEnabled(val) {
    try {
      localStorage.setItem(STORAGE_KEY, val ? "true" : "false");
    } catch (e) {}
    updateAllBtnVisibility(val);
    updateToggleWidget(val);
  }

  function updateAllBtnVisibility(enabled) {
    var btns = document.querySelectorAll(".na-chart-menu-btn");
    for (var i = 0; i < btns.length; i++) {
      btns[i].style.display = enabled ? "" : "none";
    }
  }

  // -----------------------------------------------------------------------
  // Toast feedback
  // -----------------------------------------------------------------------

  function showToast(msg) {
    var old = document.getElementById("na-chart-menu-toast");
    if (old) old.remove();
    var el = document.createElement("div");
    el.id = "na-chart-menu-toast";
    el.className = "na-chart-menu-toast";
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(function () {
      el.classList.add("na-chart-menu-toast--fade");
      setTimeout(function () {
        el.remove();
      }, 350);
    }, 1800);
  }

  // -----------------------------------------------------------------------
  // Data extraction helpers
  // -----------------------------------------------------------------------

  function plotlyDataToCsv(graphDiv) {
    var data = graphDiv._fullData;
    if (!data || !data.length) return "";
    var rows = [];
    var header = [];
    var columns = {};

    for (var i = 0; i < data.length; i++) {
      var trace = data[i];
      var name = trace.name || ("series" + (i + 1));

      if (trace.type === "pie" || trace.type === "sunburst") {
        var labels = trace.labels || trace.x || [];
        var values = trace.values || trace.y || [];
        if (!columns["Label"]) { columns["Label"] = []; }
        if (!columns[name]) { columns[name] = []; }
        for (var j = 0; j < labels.length; j++) {
          columns["Label"].push(labels[j]);
          columns[name].push(values[j] !== undefined ? values[j] : "");
        }
      } else {
        var xs = trace.x || [];
        var ys = trace.y || [];
        if (!columns["x"]) { columns["x"] = []; }
        if (!columns[name]) { columns[name] = []; }
        var maxLen = Math.max(columns["x"].length, xs.length);
        // Pad existing column to length
        while (columns["x"].length < maxLen) { columns["x"].push(""); }
        for (var k = 0; k < xs.length; k++) {
          if (k < columns["x"].length) {
            if (columns["x"][k] === "") columns["x"][k] = xs[k];
          } else {
            columns["x"].push(xs[k]);
          }
          columns[name].push(ys[k] !== undefined ? ys[k] : "");
        }
      }
    }

    var keys = Object.keys(columns);
    if (!keys.length) return "";
    var maxRows = 0;
    for (var ki = 0; ki < keys.length; ki++) {
      if (columns[keys[ki]].length > maxRows) maxRows = columns[keys[ki]].length;
    }

    rows.push(keys.map(quoteCsv).join(","));
    for (var r = 0; r < maxRows; r++) {
      var row = [];
      for (var ki2 = 0; ki2 < keys.length; ki2++) {
        var val = columns[keys[ki2]][r];
        row.push(val !== undefined ? quoteCsv(val) : "");
      }
      rows.push(row.join(","));
    }
    return rows.join("\n");
  }

  function tableDataToCsv(panel) {
    var table = panel.querySelector("table");
    if (!table) return "";
    var rows = [];
    var allRows = table.querySelectorAll("tr");
    for (var i = 0; i < allRows.length; i++) {
      var cells = allRows[i].querySelectorAll("th, td");
      if (!cells.length) continue;
      var row = [];
      for (var j = 0; j < cells.length; j++) {
        var text = cells[j].textContent || cells[j].innerText || "";
        row.push(quoteCsv(text.trim()));
      }
      rows.push(row.join(","));
    }
    return rows.join("\n");
  }

  function quoteCsv(val) {
    var s = String(val);
    if (s.indexOf(",") !== -1 || s.indexOf('"') !== -1 || s.indexOf("\n") !== -1) {
      return '"' + s.replace(/"/g, '""') + '"';
    }
    return s;
  }

  function triggerDownload(content, filename, mime) {
    var blob = content instanceof Blob ? content : new Blob([content], { type: mime });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 100);
  }

  function panelTitle(panel) {
    var titleEl = panel.querySelector(".na-element-title");
    if (titleEl) return titleEl.textContent.trim().replace(/[^a-z0-9]+/gi, "_").toLowerCase();
    return "chart";
  }

  // -----------------------------------------------------------------------
  // Action handlers
  // -----------------------------------------------------------------------

  function dataUrlToBlob(dataUrl) {
    var parts = dataUrl.split(",");
    var mime = parts[0].match(/:(.*?);/)[1];
    var bytes = atob(parts[1]);
    var buf = new Uint8Array(bytes.length);
    for (var i = 0; i < bytes.length; i++) { buf[i] = bytes.charCodeAt(i); }
    return new Blob([buf], { type: mime });
  }

  function handleCopyImage(panel) {
    var plotEl = panel.querySelector(".js-plotly-plot");
    if (!plotEl || !window.Plotly) { showToast("No chart to export"); return; }
    window.Plotly.toImage(plotEl, { format: "png", scale: 2 })
      .then(function (src) {
        var blob = dataUrlToBlob(src);
        return navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
      })
      .then(function () { showToast("Image copied to clipboard"); })
      .catch(function (e) { showToast("Could not copy image"); console.error(e); });
  }

  function handleDownloadImage(panel) {
    var plotEl = panel.querySelector(".js-plotly-plot");
    if (!plotEl || !window.Plotly) { showToast("No chart to export"); return; }
    var filename = (panelTitle(panel) || "chart") + ".png";
    // Same as copy: toImage → blob → blob URL. Plotly.downloadImage internally uses
    // a data: URL href which Chrome 65+ silently ignores for programmatic <a> clicks.
    window.Plotly.toImage(plotEl, { format: "png", scale: 2 })
      .then(function (src) {
        triggerDownload(dataUrlToBlob(src), filename, "image/png");
        showToast("Image downloaded");
      })
      .catch(function (e) { console.error("toImage failed:", e); showToast("Could not download image"); });
  }

  function handleCopyData(panel) {
    var plotEl = panel.querySelector(".js-plotly-plot");
    var csv;
    if (plotEl && window.Plotly) {
      csv = plotlyDataToCsv(plotEl);
    } else {
      csv = tableDataToCsv(panel);
    }
    if (!csv) { showToast("No data to copy"); return; }
    navigator.clipboard.writeText(csv)
      .then(function () { showToast("Data copied to clipboard"); })
      .catch(function () { showToast("Could not copy data"); });
  }

  function handleDownloadData(panel) {
    var plotEl = panel.querySelector(".js-plotly-plot");
    var csv;
    if (plotEl && window.Plotly) {
      csv = plotlyDataToCsv(plotEl);
    } else {
      csv = tableDataToCsv(panel);
    }
    if (!csv) { showToast("No data to export"); return; }
    var filename = (panelTitle(panel) || "data") + ".csv";
    triggerDownload(csv, filename, "text/csv");
    showToast("Downloading data…");
  }

  // -----------------------------------------------------------------------
  // Menu injection
  // -----------------------------------------------------------------------

  var MENU_ITEMS = [
    { label: "Copy Image to Clipboard", icon: "⧉", action: handleCopyImage, requiresPlotly: true },
    { label: "Download Image", icon: "↓", action: handleDownloadImage, requiresPlotly: true },
    { separator: true },
    { label: "Copy Data to Clipboard", icon: "⬚", action: handleCopyData, requiresPlotly: false },
    { label: "Download Data", icon: "↓", action: handleDownloadData, requiresPlotly: false },
  ];

  function injectIntoPanel(panel) {
    if (panel.getAttribute(ATTR)) return;
    panel.setAttribute(ATTR, "true");

    var hasPlotly = !!panel.querySelector(".js-plotly-plot");

    // Trigger button
    var btn = document.createElement("button");
    btn.className = "na-chart-menu-btn";
    btn.title = "Chart options";
    btn.setAttribute("aria-label", "Chart options");
    btn.textContent = "⋮";
    if (!isEnabled()) btn.style.display = "none";

    // Dropdown
    var dropdown = document.createElement("div");
    dropdown.className = "na-chart-menu-dropdown";

    MENU_ITEMS.forEach(function (item) {
      if (item.separator) {
        var sep = document.createElement("div");
        sep.className = "na-chart-menu-separator";
        dropdown.appendChild(sep);
        return;
      }
      var el = document.createElement("button");
      el.className = "na-chart-menu-item";
      if (item.requiresPlotly && !hasPlotly) {
        el.classList.add("na-chart-menu-item--disabled");
        el.title = "Not available for this panel type";
      }
      var iconSpan = document.createElement("span");
      iconSpan.className = "na-chart-menu-item-icon";
      iconSpan.textContent = item.icon;
      var labelSpan = document.createElement("span");
      labelSpan.textContent = item.label;
      el.appendChild(iconSpan);
      el.appendChild(labelSpan);

      if (!(item.requiresPlotly && !hasPlotly)) {
        el.addEventListener("click", function (e) {
          e.stopPropagation();
          closeDropdown(btn, dropdown);
          item.action(panel);
        });
      }
      dropdown.appendChild(el);
    });

    btn.appendChild(dropdown);
    panel.appendChild(btn);

    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var isOpen = dropdown.classList.contains("na-chart-menu-dropdown--open");
      // Close all other open dropdowns first
      closeAllDropdowns();
      if (!isOpen) {
        // Re-check hasPlotly — Plotly mounts after panel (async)
        var nowHasPlotly = !!panel.querySelector(".js-plotly-plot");
        if (nowHasPlotly !== hasPlotly) {
          hasPlotly = nowHasPlotly;
          var disabledItems = dropdown.querySelectorAll(".na-chart-menu-item--disabled");
          disabledItems.forEach(function (el) {
            el.classList.remove("na-chart-menu-item--disabled");
            el.removeAttribute("title");
          });
        }
        dropdown.classList.add("na-chart-menu-dropdown--open");
        btn.classList.add("na-chart-menu-btn--open");
      }
    });
  }

  function closeDropdown(btn, dropdown) {
    dropdown.classList.remove("na-chart-menu-dropdown--open");
    btn.classList.remove("na-chart-menu-btn--open");
  }

  function closeAllDropdowns() {
    var open = document.querySelectorAll(".na-chart-menu-dropdown--open");
    for (var i = 0; i < open.length; i++) {
      open[i].classList.remove("na-chart-menu-dropdown--open");
      var b = open[i].closest(".na-chart-menu-btn");
      if (b) b.classList.remove("na-chart-menu-btn--open");
    }
  }

  document.addEventListener("click", closeAllDropdowns);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeAllDropdowns();
  });

  function injectAll() {
    var overview = document.getElementById(OVERVIEW_ID);
    if (!overview) return;
    var panels = overview.querySelectorAll(".na-panel");
    for (var i = 0; i < panels.length; i++) {
      injectIntoPanel(panels[i]);
    }
  }

  // -----------------------------------------------------------------------
  // Toggle widget
  // -----------------------------------------------------------------------

  function createToggleWidget() {
    if (document.getElementById("na-chart-menu-toggle-root")) return;
    var root = document.createElement("div");
    root.id = "na-chart-menu-toggle-root";

    var btn = document.createElement("button");
    btn.className = "na-chart-menu-toggle-btn";
    btn.id = "na-chart-menu-toggle-btn";

    var label = document.createElement("span");
    label.textContent = "Chart Menu";

    var pill = document.createElement("span");
    pill.className = "na-chart-menu-toggle-pill";
    pill.id = "na-chart-menu-toggle-pill";

    btn.appendChild(label);
    btn.appendChild(pill);
    root.appendChild(btn);
    document.body.appendChild(root);

    btn.addEventListener("click", function () {
      setEnabled(!isEnabled());
    });

    updateToggleWidget(isEnabled());
  }

  function updateToggleWidget(enabled) {
    var pill = document.getElementById("na-chart-menu-toggle-pill");
    if (!pill) return;
    if (enabled) {
      pill.textContent = "ON";
      pill.classList.add("na-chart-menu-toggle-pill--on");
    } else {
      pill.textContent = "OFF";
      pill.classList.remove("na-chart-menu-toggle-pill--on");
    }
  }

  // -----------------------------------------------------------------------
  // Observer — re-inject when Dash re-renders the overview
  // -----------------------------------------------------------------------

  function observe() {
    createToggleWidget();
    injectAll();

    var observer = new MutationObserver(function () {
      injectAll();
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", observe);
  } else {
    observe();
  }
})();
