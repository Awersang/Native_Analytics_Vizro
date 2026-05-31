"""
Native Analytics Vizro — Amazon Media Monitoring Dashboard
Rebuilt from the reference notebook with full Vizro controls.

Pages
  1. Reach & Engagement Timeline  — dual-axis chart + campaign Gantt
  2. Narrative Breakdown          — bar, stacked-area, and scatter charts

Run:
  python app.py
  → http://127.0.0.1:8050
"""

import vizro.models as vm
from vizro import Vizro

from pages.breakdown import breakdown_page
from pages.timeline import timeline_page

dashboard = vm.Dashboard(
    title="Native Analytics · Amazon Media Monitor",
    pages=[timeline_page, breakdown_page],
)

if __name__ == "__main__":
    Vizro().build(dashboard).run(debug=True)
