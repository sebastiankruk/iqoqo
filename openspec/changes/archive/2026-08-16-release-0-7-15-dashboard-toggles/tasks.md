## 1. Mobile Layout

- [x] 1.1 Add `overflow-x-auto flex-nowrap` classes to top metric tiles container.
- [x] 1.2 Verify single-line horizontal scrolling on mobile viewports.

## 2. UI Toggles

- [x] 2.1 Implement view toggle switch (Top Tiles vs Stats Tiles).
- [x] 2.2 Implement scope toggle switch (Global vs Personal).

## 3. Backend Scoping

- [x] 3.1 Update `app/api/profile.py` to accept `scope` query parameter.
- [x] 3.2 Implement conditional `UserWorkIntent` joins based on the scope parameter for accurate personal inventory counts.

## 4. UX Audit Fixes

- [x] 4.1 Rename view toggle options to "Stats" and "Insights".
- [x] 4.2 Remove FRBR stats presentation and replace with custom metrics (My items, Reading, etc.).
- [x] 4.3 Implement conditional label mapping based on scope ("My items" -> "All items", "Reading" -> "Being read", "On wish list" -> "On wish lists").
- [x] 4.4 Implement Insights view showing time charts (e.g., acquisition velocity).
- [x] 4.5 Apply full-width horizontal scroll layout to Insights charts on mobile viewports.
- [x] 4.6 Apply horizontal scroll layout to the Wish list section on mobile viewports.
- [x] 4.7 Pass `scope` prop into `CollectionInsights`, `VelocityChart`, and `TypeDistributionChart` to accurately reflect personal vs global scope in Insights view.
