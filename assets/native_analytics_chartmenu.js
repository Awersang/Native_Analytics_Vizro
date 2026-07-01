/* Native Analytics — chart context menu.
 *
 * The `.na-chart-menu-btn` + dropdown markup is rendered server-side by
 * `chart_menu_button()` (ui_components.py) as a normal child of each
 * `.na-panel` / `.amazon-publishers-mini-donut` / `.amazon-publishers-venn`
 * that has a chart or table — Dash/React owns those nodes from the start.
 * This file only attaches behavior to that existing markup via event
 * delegation; it never creates or inserts DOM nodes itself, so there's
 * nothing here that can desync React's reconciliation for those panels
 * (previously this injected the button with a raw `appendChild`, which did
 * exactly that and caused the panel's content to revert unpredictably on
 * the next render — see git history for the narrative/publisher/campaign
 * detail-panel collapse bug).
 *
 * Click opens a dropdown with:
 *   - Copy Image to Clipboard
 *   - Download Image
 *   - Copy Data to Clipboard
 *   - Download Data
 */
(function () {
  "use strict";

  var CHART_MENU_ENABLED = typeof window.__NA_CHART_MENU_ENABLED__ === "boolean"
    ? window.__NA_CHART_MENU_ENABLED__
    : true;
  var HOST_SELECTORS = [
    ".amazon-publishers-mini-donut",
    ".amazon-publishers-venn",
    ".na-panel",
    ".amazon-publishers-section",
  ];
  var TITLE_SELECTOR = [
    ".na-element-title",
    ".amazon-publishers-mini-title",
    ".amazon-publishers-section-header h2",
    "h2",
    "h3",
  ].join(", ");

  function isEnabled() {
    return CHART_MENU_ENABLED;
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

  function closestHost(el) {
    if (!el) return null;
    for (var i = 0; i < HOST_SELECTORS.length; i++) {
      var host = el.closest(HOST_SELECTORS[i]);
      if (host) return host;
    }
    return null;
  }

  function tableElement(panel) {
    var tables = panel.querySelectorAll("table");
    for (var i = 0; i < tables.length; i++) {
      if (closestHost(tables[i]) === panel) return tables[i];
    }
    return null;
  }

  function tableDataToCsv(panel) {
    var table = tableElement(panel);
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
    var titleEl = panel.querySelector(TITLE_SELECTOR);
    if (titleEl && titleEl.textContent) {
      return titleEl.textContent.trim().replace(/[^a-z0-9]+/gi, "_").toLowerCase();
    }
    if (panel.id) {
      return panel.id.replace(/[^a-z0-9]+/gi, "_").toLowerCase();
    }
    return "chart";
  }

  function plotlyElement(panel) {
    var plots = panel.querySelectorAll(".js-plotly-plot");
    for (var i = 0; i < plots.length; i++) {
      if (closestHost(plots[i]) === panel) return plots[i];
    }
    return null;
  }

  function clonePlain(value) {
    return JSON.parse(JSON.stringify(value || {}));
  }

  function resolveCssColor(value, probe) {
    if (typeof value !== "string" || value.indexOf("var(") === -1) return value;
    probe.style.color = "";
    probe.style.color = value;
    var resolved = getComputedStyle(probe).color;
    return resolved || value;
  }

  function resolveThemeColors(value, probe) {
    if (Array.isArray(value)) {
      return value.map(function (item) { return resolveThemeColors(item, probe); });
    }
    if (value && typeof value === "object") {
      Object.keys(value).forEach(function (key) {
        value[key] = resolveThemeColors(value[key], probe);
      });
      return value;
    }
    return resolveCssColor(value, probe);
  }

  function currentExportTheme(probe) {
    var rootStyle = getComputedStyle(document.documentElement);
    function cssVar(name) {
      probe.style.color = "";
      probe.style.color = rootStyle.getPropertyValue(name).trim();
      return getComputedStyle(probe).color;
    }
    return {
      text: cssVar("--na-text"),
      muted: cssVar("--na-text-muted"),
      grid: cssVar("--na-grid"),
      border: cssVar("--na-border"),
      surface: cssVar("--na-surface"),
    };
  }

  function isObject(value) {
    return value && typeof value === "object" && !Array.isArray(value);
  }

  function fontColorForKey(key, theme) {
    return key === "tickfont" ? theme.muted : theme.text;
  }

  function themeFontObject(font, key, theme) {
    if (!isObject(font)) return;
    font.color = fontColorForKey(key, theme);
  }

  function applyPlotlyExportTheme(value, theme, key) {
    if (Array.isArray(value)) {
      value.forEach(function (item) {
        applyPlotlyExportTheme(item, theme, key);
      });
      return;
    }
    if (!isObject(value)) return;

    if (/font$/i.test(key || "")) {
      themeFontObject(value, String(key).toLowerCase(), theme);
    }

    Object.keys(value).forEach(function (childKey) {
      var child = value[childKey];
      var lowerKey = childKey.toLowerCase();

      if (isObject(child) || Array.isArray(child)) {
        applyPlotlyExportTheme(child, theme, lowerKey);
        return;
      }

      if (typeof child !== "string") return;

      if (/font$/i.test(key || "") && lowerKey === "color") {
        value[childKey] = fontColorForKey(String(key).toLowerCase(), theme);
      } else if (lowerKey === "gridcolor") {
        value[childKey] = theme.grid;
      } else if (lowerKey === "linecolor" || lowerKey === "zerolinecolor" || lowerKey === "tickcolor") {
        value[childKey] = theme.border;
      } else if (lowerKey === "bordercolor") {
        value[childKey] = theme.border;
      }
    });
  }

  function applyExportDefaults(data, layout, theme) {
    layout.font = layout.font || {};
    layout.font.color = theme.text;
    layout.legend = layout.legend || {};
    layout.legend.font = layout.legend.font || {};
    layout.legend.font.color = theme.text;
    layout.legend.bgcolor = "rgba(0,0,0,0)";
    layout.hoverlabel = layout.hoverlabel || {};
    layout.hoverlabel.bgcolor = theme.surface;
    layout.hoverlabel.bordercolor = theme.border;
    layout.hoverlabel.font = layout.hoverlabel.font || {};
    layout.hoverlabel.font.color = theme.text;

    data.forEach(function (trace) {
      if (trace.text || trace.texttemplate || trace.textinfo || trace.type === "pie" || trace.type === "bar") {
        trace.textfont = trace.textfont || {};
        trace.textfont.color = theme.text;
        trace.insidetextfont = trace.insidetextfont || {};
        trace.insidetextfont.color = theme.text;
        trace.outsidetextfont = trace.outsidetextfont || {};
        trace.outsidetextfont.color = theme.text;
      }
    });
  }

  function themedExportPayload(plotEl) {
    var probe = document.createElement("span");
    probe.style.display = "none";
    document.body.appendChild(probe);
    var fullLayout = plotEl._fullLayout || {};
    var layout = resolveThemeColors(clonePlain(plotEl.layout), probe);
    var data = resolveThemeColors(clonePlain(plotEl.data || []), probe);
    var theme = currentExportTheme(probe);
    document.body.removeChild(probe);

    applyExportDefaults(data, layout, theme);
    applyPlotlyExportTheme(layout, theme, "layout");
    applyPlotlyExportTheme(data, theme, "data");
    layout.width = fullLayout.width || plotEl.clientWidth || layout.width;
    layout.height = fullLayout.height || plotEl.clientHeight || layout.height;
    layout.autosize = false;
    return { data: data, layout: layout, theme: theme };
  }

  function withThemedExportPlot(plotEl, callback) {
    var payload = themedExportPayload(plotEl);
    var exportEl = document.createElement("div");
    exportEl.style.position = "fixed";
    exportEl.style.left = "-10000px";
    exportEl.style.top = "-10000px";
    exportEl.style.width = (payload.layout.width || plotEl.clientWidth || 700) + "px";
    exportEl.style.height = (payload.layout.height || plotEl.clientHeight || 450) + "px";
    exportEl.style.pointerEvents = "none";
    document.body.appendChild(exportEl);

    return window.Plotly.newPlot(exportEl, payload.data, payload.layout, {
      displayModeBar: false,
      responsive: false,
      staticPlot: true,
    })
      .then(function () {
        return callback(exportEl);
      })
      .finally(function () {
        window.Plotly.purge(exportEl);
        exportEl.remove();
      });
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
    var plotEl = plotlyElement(panel);
    if (!plotEl || !window.Plotly) { showToast("No chart to export"); return; }
    withThemedExportPlot(plotEl, function (exportEl) {
      return window.Plotly.toImage(exportEl, { format: "png", scale: 2 });
    })
      .then(function (src) {
        var blob = dataUrlToBlob(src);
        return navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
      })
      .then(function () { showToast("Image copied to clipboard"); })
      .catch(function (e) { showToast("Could not copy image"); console.error(e); });
  }

  function handleDownloadImage(panel) {
    var plotEl = plotlyElement(panel);
    if (!plotEl || !window.Plotly) { showToast("No chart to export"); return; }
    var filename = panelTitle(panel) || "chart";
    withThemedExportPlot(plotEl, function (exportEl) {
      return window.Plotly.downloadImage(exportEl, { format: "png", filename: filename, scale: 2 });
    })
      .then(function () { showToast("Downloading image..."); })
      .catch(function (e) { console.error("downloadImage failed:", e); showToast("Could not download image"); });
  }

  function handleCopyData(panel) {
    var plotEl = plotlyElement(panel);
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
    var plotEl = plotlyElement(panel);
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
  // Menu behavior — event delegation against server-rendered markup
  // -----------------------------------------------------------------------

  var ACTIONS = {
    "copy-image": handleCopyImage,
    "download-image": handleDownloadImage,
    "copy-data": handleCopyData,
    "download-data": handleDownloadData,
  };

  function closeDropdown(btn) {
    var dropdown = btn.querySelector(".na-chart-menu-dropdown");
    if (dropdown) dropdown.classList.remove("na-chart-menu-dropdown--open");
    btn.classList.remove("na-chart-menu-btn--open");
  }

  function closeAllDropdowns() {
    var open = document.querySelectorAll(".na-chart-menu-btn--open");
    for (var i = 0; i < open.length; i++) {
      closeDropdown(open[i]);
    }
  }

  document.addEventListener("click", function (e) {
    if (!isEnabled()) {
      closeAllDropdowns();
      return;
    }

    var item = e.target.closest(".na-chart-menu-item");
    if (item) {
      e.stopPropagation();
      if (item.classList.contains("na-chart-menu-item--disabled")) return;
      var btn = item.closest(".na-chart-menu-btn");
      var panel = btn && closestHost(btn);
      var action = ACTIONS[item.getAttribute("data-action")];
      if (btn) closeDropdown(btn);
      if (panel && action) action(panel);
      return;
    }

    var btn2 = e.target.closest(".na-chart-menu-btn");
    if (btn2) {
      e.stopPropagation();
      var dropdown = btn2.querySelector(".na-chart-menu-dropdown");
      var isOpen = dropdown && dropdown.classList.contains("na-chart-menu-dropdown--open");
      closeAllDropdowns();
      if (!isOpen && dropdown) {
        dropdown.classList.add("na-chart-menu-dropdown--open");
        btn2.classList.add("na-chart-menu-btn--open");
      }
      return;
    }

    closeAllDropdowns();
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      closeAllDropdowns();
      return;
    }
    if (e.key !== "Enter" && e.key !== " ") return;
    // Only the trigger is a plain div[role=button]; dropdown items are real
    // <button>s and already get native Enter/Space activation.
    var target = e.target.closest(".na-chart-menu-btn");
    if (!target || target !== e.target) return;
    e.preventDefault();
    target.click();
  });
})();
