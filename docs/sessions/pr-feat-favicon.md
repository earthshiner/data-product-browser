# Tab favicon + hierarchical ERD layout

Targets `main`. Bundles two UI improvements (the ERD work was committed onto this
branch before it was split out — kept together rather than force-pushing).

## 1. Favicon
- `static/favicon.svg` — a branded data-product mark (three rounded bars in the
  app's accent/status colours on the dark panel), linked from `index.html`.
- Browser tabs (Edge/Chrome/Firefox) show a custom icon instead of the default.
- Covered by a static-serving test.

## 2. Hierarchical ERD layout
Replaces the one-column-per-module Entity Map with a layered (Sugiyama-style)
layout:
- **Longest-path layering**: referenced tables on the left, dependents flowing
  right (e.g. `Agent → Call → {Call Score, Call Features} → Model Prediction`).
- **Barycenter sweep** within layers to reduce edge crossings; per-column
  vertical centring.
- **Unconnected entities** collect into a tidy wrapped grid below, instead of
  padding a tall column.
- Module colour legend + a "left = referenced, right = dependent" hint.
- Still zero-dependency inline SVG; node-click still opens the entity.

## Verification

- `uv run pytest` — 19 passed; `ruff`/`node --check` clean.
- Rendered end-to-end via preview: correct layer ordering (verified node x-positions
  Agent=0 → Call → Score/Features → Model Prediction), unconnected grid, legend,
  and node-click jump. Favicon served (200). No console errors.
