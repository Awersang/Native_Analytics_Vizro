/* Native Analytics — Cross-filtering & drill-down  (detachable feature)
 *
 * Click a bar / point / segment in any chart on a dashboard page and every
 * chart dims the slices that don't match the clicked series, so you can read a
 * single category (sentiment, stage, narrative, ...) across all charts at once.
 * A breadcrumb chip shows the active selection; click it (or the chart again)
 * to clear.
 *
 * This is purely client-side (Plotly.restyle) and never touches Vizro's own
 * filter/parameter controls, so it can't break them.
 *
 * To remove this feature: delete this file and assets/ext_crossfilter.css.
 * Nothing else references them.
 */
(function () {
    var DIM = 0.18;
    var active = null; // currently highlighted series name

    function plots() {
        return Array.prototype.slice.call(document.querySelectorAll(".js-plotly-plot"));
    }

    function apply(key) {
        plots().forEach(function (gd) {
            if (!gd.data || !window.Plotly) return;
            gd.data.forEach(function (tr, i) {
                var match = key === null || tr.name === key;
                try {
                    window.Plotly.restyle(gd, { opacity: match ? 1 : DIM }, [i]);
                } catch (e) {
                    /* trace may not support opacity; ignore */
                }
            });
        });
    }

    function chip() {
        var c = document.getElementById("ext-xfilter-chip");
        if (active === null) {
            if (c) c.remove();
            return;
        }
        if (!c) {
            c = document.createElement("div");
            c.id = "ext-xfilter-chip";
            c.addEventListener("click", clear);
            document.body.appendChild(c);
        }
        c.textContent = "Filtered: " + active + "  \u2715";
    }

    function clear() {
        active = null;
        apply(null);
        chip();
    }

    function onClick(ev) {
        if (!ev || !ev.points || !ev.points.length) return;
        var pt = ev.points[0];
        var key = (pt.data && pt.data.name) || pt.label || pt.x;
        if (key == null) return;
        active = active === key ? null : String(key);
        apply(active);
        chip();
    }

    function bind() {
        plots().forEach(function (gd) {
            if (gd.__extXfilterBound) return;
            gd.__extXfilterBound = true;
            if (gd.on) gd.on("plotly_click", onClick);
            // Re-apply current selection when Plotly redraws this graph.
            if (gd.on) gd.on("plotly_afterplot", function () { if (active !== null) apply(active); });
        });
    }

    // Vizro is a single-page app and redraws charts on navigation/filtering.
    bind();
    new MutationObserver(function () {
        bind();
        // A page change wipes any selection context.
        if (active !== null && plots().length === 0) clear();
    }).observe(document.documentElement, { subtree: true, childList: true });
})();
