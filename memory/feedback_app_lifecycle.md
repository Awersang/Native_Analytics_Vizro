---
name: feedback-app-lifecycle
description: Do NOT auto-restart or manage the app — user explicitly removed this requirement
metadata:
  type: feedback
---

Do not attempt to restart or manage the app lifecycle (`python app.py`) as part of task completion.

**Why:** User explicitly asked to remove this instruction. The app-restart-on-finish requirement was removed from CLAUDE.md and this memory on 2026-06-09.
**How to apply:** Never try to kill or start the app as part of code changes. Do not verify changes by launching the app.
