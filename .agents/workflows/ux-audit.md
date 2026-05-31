---
description: Evaluate button layout overcrowding and item-adding flows for iqoqo
---

# Workflow: UX Audit

This workflow evaluates button layouts, density, and item addition processes.

## Objectives

1. **Target**: https://dev.iqoqo.cc (or local address like http://localhost:3000).
2. **Steps**:
   - Open Chrome browser. Navigate to main view or dashboard.
   - Run audit on buttons: check if too many buttons in one section. Follow `iqoqo-ux-auditor` skill rules.
   - Run manual item addition flow.
   - Run scan/batch addition flow.
   - Count clicks, inputs, and screens needed.
3. **Outcome**:
   - Save Interaction Friction Map.
   - Highlight bad layouts or high button counts.
   - Suggest CSS Grid, Flexbox, or dropdown fixes.
