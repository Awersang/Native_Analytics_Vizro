# Feedback: Always update STYLE_GUIDE.md on styling changes

Whenever making a change to the styling of the Amazon 2026 dashboard or its
elements (colors, tokens, panel/box variants, CSS rules, palettes, etc.),
always update `dashboards/amazon_2026/STYLE_GUIDE.md` to document the change.

**Why:** The user explicitly asked (2026-06-15) that this become a standing
rule, after a series of styling fixes (Key Insight card borders, treemap
divider colors, `TOPIC_AREA_PALETTE` saturation) where the style guide also
needed corresponding updates/gotchas documented.

**How to apply:** Treat a styling change as incomplete until the relevant
STYLE_GUIDE.md section (color system, panel variants, gotchas, deliberate
exceptions, etc.) reflects the new state — including removing stale
references to tokens/constants that get deleted as part of the change. See
`screenshot_verification.md` for how to visually verify styling changes
before considering them done.
