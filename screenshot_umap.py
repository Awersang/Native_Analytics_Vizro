from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1800, "height": 1400})
    page.on("pageerror", lambda exc: print("PAGEERROR:", exc))
    for attempt in range(5):
        page.goto("http://127.0.0.1:8051/app/d/amazon_2026/discover", wait_until="load")
        try:
            page.wait_for_selector("#amazon-2026-discover-clusters-graph .js-plotly-plot", timeout=15000)
            break
        except Exception:
            print(f"attempt {attempt} failed, retrying...")
    else:
        raise RuntimeError("plotly never loaded")
    page.wait_for_timeout(2000)

    graph = page.locator("#amazon-2026-discover-clusters-graph .js-plotly-plot")
    box = graph.bounding_box()
    print("graph box:", box)

    # Switch to box-select tool (the "select" dragmode button in the modebar)
    page.locator("#amazon-2026-discover-clusters-graph .modebar-btn[data-title='Box Select']").click()
    page.wait_for_timeout(500)

    # Drag a box selection in the middle of the chart
    cx, cy = box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.3
    cx2, cy2 = box["x"] + box["width"] * 0.6, box["y"] + box["height"] * 0.6
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx2, cy2, steps=10)
    page.mouse.up()
    page.wait_for_timeout(1500)

    page.screenshot(path="out_umap_selected.png")
    graph.screenshot(path="out_umap_selected_graph.png")

    # Now change a filter (Source -> Trad)
    page.locator("#amazon-2026-discover-source-filter").click()
    page.wait_for_timeout(300)
    page.locator("#amazon-2026-discover-filters-section").get_by_text("Trad", exact=True).click()
    page.wait_for_timeout(2000)
    # close the dropdown by clicking the page title
    page.locator("h2", has_text="Discover").first.click()
    page.wait_for_timeout(1000)

    page.screenshot(path="out_umap_after_filter.png")
    graph.screenshot(path="out_umap_after_filter_graph.png")

    browser.close()
