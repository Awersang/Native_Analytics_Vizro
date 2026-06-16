from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1800, "height": 1400})
    page.on("console", lambda msg: print("CONSOLE:", msg.type, msg.text))
    page.on("pageerror", lambda exc: print("PAGEERROR:", exc))
    page.goto("http://127.0.0.1:8051/app/d/amazon_2026/discover", wait_until="load")
    try:
        page.wait_for_selector("#amazon-2026-discover-clusters-graph .js-plotly-plot", timeout=60000)
    except Exception as e:
        print("ERR", e)
        page.screenshot(path="out_debug2.png", full_page=True)
        raise
    page.wait_for_timeout(2000)

    graph = page.locator("#amazon-2026-discover-clusters-graph .js-plotly-plot")
    box = graph.bounding_box()

    page.evaluate("""
        const gd = document.querySelector('#amazon-2026-discover-clusters-graph .js-plotly-plot');
        window.__events = [];
        gd.on('plotly_selected', e => window.__events.push(['selected', e ? e.range || e.lassoPoints : null]));
        gd.on('plotly_relayout', e => window.__events.push(['relayout', JSON.parse(JSON.stringify(e))]));
        gd.on('plotly_deselect', () => window.__events.push(['deselect', null]));
    """)

    page.locator("#amazon-2026-discover-clusters-graph .modebar-btn[data-title='Box Select']").click()
    page.wait_for_timeout(300)
    cx, cy = box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.3
    cx2, cy2 = box["x"] + box["width"] * 0.6, box["y"] + box["height"] * 0.6
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx2, cy2, steps=10)
    page.mouse.up()
    page.wait_for_timeout(1000)

    layout_selections = page.evaluate("""
        () => {
            const gd = document.querySelector('#amazon-2026-discover-clusters-graph .js-plotly-plot');
            return gd.layout.selections || null;
        }
    """)
    print("layout.selections:", layout_selections)

    events = page.evaluate("window.__events")
    print("events:", events)

    browser.close()
