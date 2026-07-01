/* Native Analytics — "Chat with your data" widget  (detachable feature)
 *
 * A left-rail button + panel shown only on dashboard pages (/app/d/<slug>).
 * It POSTs questions to /ext/chat/ask and renders the answer.
 *
 * To remove this feature: delete this file, assets/ext_chat.css, the
 * extensions/ package, and the install_extensions() hook in app.py.
 */
(function () {
    var PREFIX = "/app/d/";
    var scriptSrc = document.currentScript && document.currentScript.src;

    function ensureStylesheet() {
        if (document.getElementById("ext-chat-css")) return;
        var href = scriptSrc
            ? scriptSrc.replace(/\.js(\?.*)?$/, ".css$1")
            : "/app/assets/ext_chat.css";
        var link = document.createElement("link");
        link.id = "ext-chat-css";
        link.rel = "stylesheet";
        link.href = href;
        document.head.appendChild(link);
    }

    function currentSlug() {
        var p = window.location.pathname;
        if (p.indexOf(PREFIX) !== 0) return null;
        return p.slice(PREFIX.length).split("/")[0] || null;
    }

    function el(tag, cls, text) {
        var e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text != null) e.textContent = text;
        return e;
    }

    function ensureRoot() {
        var root = document.getElementById("ext-chat-root");
        if (root) return root;

        root = el("div", null);
        root.id = "ext-chat-root";
        root.className = "na-sidebar-panel-hidden";

        var panel = el("div", "ext-chat-panel ext-chat-hidden");
        panel.id = "ext-chat-panel";
        panel.setAttribute("aria-hidden", "true");
        var header = el("div", "ext-chat-header", "Chat with your data");
        var log = el("div", "ext-chat-log");
        var hint = el("div", "ext-chat-msg ext-chat-bot",
            "Ask a question about this dashboard's data, e.g. \u201cWhich has the highest total reach?\u201d");
        log.appendChild(hint);

        var form = el("form", "ext-chat-form");
        var input = el("input", "ext-chat-input");
        input.type = "text";
        input.placeholder = "Ask a question\u2026";
        input.autocomplete = "off";
        var send = el("button", "ext-chat-send", "Send");
        send.type = "submit";
        form.appendChild(input);
        form.appendChild(send);

        panel.appendChild(header);
        panel.appendChild(log);
        panel.appendChild(form);
        root.appendChild(panel);

        function addMsg(text, who) {
            var m = el("div", "ext-chat-msg " + (who === "user" ? "ext-chat-user" : "ext-chat-bot"));
            m.textContent = text;
            log.appendChild(m);
            log.scrollTop = log.scrollHeight;
            return m;
        }

        form.addEventListener("submit", function (ev) {
            ev.preventDefault();
            var q = input.value.trim();
            var slug = currentSlug();
            if (!q || !slug) return;
            addMsg(q, "user");
            input.value = "";
            var pending = addMsg("\u2026", "bot");
            send.disabled = true;

            fetch("/ext/chat/ask", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify({ slug: slug, question: q }),
            })
                .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
                .then(function (res) {
                    pending.textContent = res.ok
                        ? res.d.answer + (res.d.source === "local" ? "\n\n(offline answer)" : "")
                        : (res.d.error || "Something went wrong.");
                    log.scrollTop = log.scrollHeight;
                })
                .catch(function () { pending.textContent = "Network error \u2014 please try again."; })
                .finally(function () { send.disabled = false; input.focus(); });
        });

        return root;
    }

    function ensureToggle() {
        var toggle = document.getElementById("ext-chat-toggle");
        if (toggle) return toggle;

        toggle = el("button", "na-left-dock-button ext-chat-toggle");
        toggle.id = "ext-chat-toggle";
        toggle.type = "button";
        toggle.setAttribute("aria-label", "Chat with your data");
        toggle.setAttribute("title", "AI chart");
        var icon = el("span", "material-symbols-outlined", "smart_toy");
        toggle.appendChild(icon);

        toggle.addEventListener("click", function () {
            if (window.NativeAnalyticsSidebar) {
                window.NativeAnalyticsSidebar.show("chat");
            }
        });

        return toggle;
    }

    function build() {
        var dock = document.getElementById("na-left-action-dock");
        if (!dock) return;

        var root = ensureRoot();
        var toggle = ensureToggle();
        // Keep the panel at <body> level (stable). It used to be appended into
        // Vizro's #nav-control-panel, which Dash rebuilds on every navigation —
        // that destroyed the node. native_analytics.js overlays it on the left
        // column with position:fixed instead. See positionSidebarPanels().
        if (root.parentNode !== document.body) {
            document.body.appendChild(root);
        }

        var viewsButton = document.getElementById("saved-views-toggle");
        if (toggle.parentNode !== dock) {
            if (viewsButton && viewsButton.parentNode === dock) {
                dock.insertBefore(toggle, viewsButton);
            } else {
                dock.appendChild(toggle);
            }
        } else if (viewsButton && toggle.nextSibling !== viewsButton) {
            dock.insertBefore(toggle, viewsButton);
        }
    }

    function detach() {
        var root = document.getElementById("ext-chat-root");
        var toggle = document.getElementById("ext-chat-toggle");
        if (root) {
            root.remove();
        }
        if (toggle) {
            toggle.remove();
        }
    }

    function sync() {
        var onDashboard = currentSlug() !== null;
        if (onDashboard) {
            build();
        } else {
            detach();
        }
    }

    // Vizro is a single-page app, so re-check on navigation/DOM changes.
    ensureStylesheet();
    if (document.body) sync();
    new MutationObserver(sync).observe(document.documentElement, { subtree: true, childList: true });
})();
