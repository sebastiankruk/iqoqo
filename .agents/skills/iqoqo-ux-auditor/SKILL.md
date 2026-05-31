---
name: iqoqo-ux-auditor
description: "Skill for auditing UX/UI layout, buttons density, and item-addition flows in iqoqo."
license: AGPL
compatibility:
  - opencode
metadata:
  audience: developers
---

# Skill: iqoqo UX/UI Auditor

This skill provides guides for auditing UX/UI layout density, button arrangements, and item adding flows for the iqoqo web service.

## Heuristics and Constraints

1. **Button Density**: Flag any viewport or container containing more than 4 visible buttons. Recommend alternative patterns like context-aware long presses, swipe actions, or 3-dot overflow menus.
2. **Action Hierarchy**: Ensure exactly ONE clear primary CTA per view. Secondary and tertiary actions must be visually distinct and minimized.
3. **Friction in Item Addition**: Map the "Time to Success" for adding media. Flag any flow requiring more than 3 clicks/taps from start to confirmation.
4. **Scanning Feedback**: Check for instant, unambiguous feedback during batch scanning/adding to prevent user doubt.

## Artifact Requirements

- Every analysis must include a full-page DOM layout snapshot.
- Create an "Interaction Friction Map" for the item-addition sequence.
