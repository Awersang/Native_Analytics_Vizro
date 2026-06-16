from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1800, "height": 1400})
    page.goto("http://127.0.0.1:8050/app/d/amazon_2026/campaigns", wait_until="networkidle")
    page.wait_for_timeout(2000)
    page.evaluate("""
        const els = document.querySelectorAll('*');
        for (const el of els) {
            if (el.scrollHeight > el.clientHeight + 50 && el.clientHeight > 200) {
                el.scrollTop = el.scrollHeight;
            }
        }
    """)
    page.wait_for_timeout(500)
    page.evaluate("""
        const tds = document.querySelectorAll('td');
        for (const td of tds) {
            if (td.textContent.trim() === 'Cross-Border E-commerce') {
                td.click();
            }
        }
    """)
    page.wait_for_timeout(15000)
    page.evaluate("""
        const els = document.querySelectorAll('*');
        for (const el of els) {
            if (el.scrollHeight > el.clientHeight + 50 && el.clientHeight > 200) {
                el.scrollTop = el.scrollHeight;
            }
        }
    """)
    page.wait_for_timeout(1000)
    cb = page.locator("label", has_text="Narratives").last
    box = cb.bounding_box()
    page.mouse.click(box["x"]+5, box["y"]+box["height"]/2)
    page.wait_for_timeout(5000)
    graph = page.locator("[id*='timeline-graph']").last
    gbox = graph.bounding_box()
    page.screenshot(path="out_cross_border.png", clip={"x": gbox["x"]-20, "y": gbox["y"]-20, "width": gbox["width"]+40, "height": gbox["height"]+40})
    browser.close()
