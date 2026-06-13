/* Native Analytics — "Chat with your data" widget  (detachable feature)
 *
 * A floating button + panel shown only on dashboard pages (/app/d/<slug>).
 * It POSTs questions to /ext/chat/ask and renders the answer.
 *
 * To remove this feature: delete this file, assets/ext_chat.css, the
 * extensions/ package, and the install_extensions() hook in app.py.
 */
(function () {
    var PREFIX = "/app/d/";

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

    function build() {
        if (document.getElementById("ext-chat-root")) return;

        var root = el("div", null);
        root.id = "ext-chat-root";

        var toggle = el("button", "ext-chat-toggle", "Ask the data");
        toggle.type = "button";
        toggle.setAttribute("aria-label", "Chat with your data");

        var panel = el("div", "ext-chat-panel ext-chat-hidden");
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
        root.appendChild(toggle);
        document.body.appendChild(root);

        toggle.addEventListener("click", function () {
            panel.classList.toggle("ext-chat-hidden");
            if (!panel.classList.contains("ext-chat-hidden")) input.focus();
        });

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
    }

    function sync() {
        var onDashboard = currentSlug() !== null;
        var root = document.getElementById("ext-chat-root");
        if (onDashboard && !root) build();
        else if (!onDashboard && root) root.remove();
    }

    // Vizro is a single-page app, so re-check on navigation/DOM changes.
    if (document.body) sync();
    new MutationObserver(sync).observe(document.documentElement, { subtree: true, childList: true });
})();
