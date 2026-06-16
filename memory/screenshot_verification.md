---
name: screenshot-verification
description: How to run the Vizro app on a separate port and capture screenshots to visually verify UI changes
metadata:
  type: project
---

This project has Playwright (with Chromium) already installed and working, and local auth is disabled — so UI changes can be verified visually without login.

**Port conflict**: the user often runs `python app.py` themselves on the default port 8050. Do NOT use that port — launch a second instance on a different port (e.g. 8051) instead.

Workflow:
1. Start a verification instance on a non-default port, e.g.:
   ```
   python -c "import app as appmod; appmod.app.dash.run(host='127.0.0.1', port=8051, debug=False, use_reloader=False)"
   ```
   run with `run_in_background: true`.
2. Use a small Playwright script (sync API) to navigate to `http://127.0.0.1:8051/...` and save PNG screenshots to a temp/screenshots folder.
3. Use the `Read` tool on the PNG files to visually inspect the rendered UI.
4. ALWAYS kill the background server (TaskStop / process kill) when done — never leave a stray instance running.

**Why:** User asked (2026-06-14) to enable this verification loop, then flagged that running on the default port would collide with their own running instance.

**How to apply:** For any task touching `assets/*.css`, `assets/*.js`, or dashboard page layouts (e.g. `dashboards/amazon_2026/`), proactively run this verification loop before reporting the change as done — always on port 8051 (or another free port), and always clean up afterward.
