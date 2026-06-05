# Operations dashboard

Targets `main` directly (PRs #3–#5 merged).

## What

Promotes the lightweight "Product Health" tab into a full single-pane
**Operations dashboard** — the authoritative "can I trust and operate this data
product right now?" view. Deterministic, read straight from the standard's
Observability + trust metadata; no AI client involved.

### KPI cards
Trust score · quality pass rate · failed lineage runs · last-run freshness ·
change events (window) · agent success rate.

### Inline charts (zero dependencies, hand-rolled SVG)
- Quality pass-rate trend (14-day sparkline)
- Change volume (14-day bars)
- Records written per run (bars, failed runs flagged)

### Panels
- Trust engine detail (status, checks, readiness scores)
- Data quality · Lineage runs · Change activity tables
- **Agent outcomes** — status breakdown pills + recent activity table
  (from `agent_outcome`)

## Notes

- No new dependencies — charts are small inline `<svg>` built in vanilla JS, in
  keeping with the static, build-step-free frontend.
- The nav item is renamed `Operations`; it remains the default landing view on
  product load. Entity browsing (Schema/Relationships/Glossary/Decisions) is
  unchanged.

## Verification

- `uv run pytest` — 15 passed; `ruff`-clean.
- Rendered end-to-end via the preview harness (enriched with time-spread quality
  and change data plus agent outcomes): KPI cards, all three charts, and the
  four tables incl. agent outcomes — no console errors.
