# PR: Cookbook pop + Query_Cookbook.is_batch + bolder ops headers

## Summary
- **`Query_Cookbook.is_batch` surfaced** — added `is_batch: Optional[int]` to the `Recipe` model; `recipeMode()` now prefers the explicit column and falls back to the `:param` heuristic only when the column isn't deployed.
- **Pills get pop** — Interactive/Batch pills now use solid Teradata-brand gradient fills (sky blue / orange), uppercase, with a soft glow. Complexity and module pills get tinted backgrounds (green/red/blue) instead of muted outlines.
- **Bigger headings** — recipe title up to 20px in warm cream; pills inline at 14px radius.
- **Ops dashboard sections** — summary bars bumped to 16px uppercase bold with a hover state so the collapsible affordance is unmistakable. (Also cache-busts `app.js?v=3` so browsers actually pick up the new JS.)

## Test plan
- [ ] Load a product with `Query_Cookbook.is_batch` populated — pills show correct mode.
- [ ] Load a product without the column — heuristic fallback still works.
- [ ] Operations dashboard: Data quality / Lineage runs / Change activity / Agent outcomes are collapsed by default and toggle on click.
- [ ] Visual: Teradata orange/blue/navy/teal accents render in dark mode.
