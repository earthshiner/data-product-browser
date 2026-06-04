# Local server browser (steps 1–4)

**Stacked on `feat/rebrand-data-product-browser`** — review/merge that PR first.

Scope grew during the session: this branch now covers plumbing, the SPA shell,
entity cross-linking, and the product health dashboard. See "Roadmap" below.

Verified visually via a DB-free preview harness (`scripts/_preview_harness.py`):
shell, health cards/tables with status colouring, entity tabs with counts,
relationship cards with working cross-entity jumps, glossary and decision cards.

## Why

We need a way for a human to explore an AI-Native Data Product that does **not**
depend on an AI client being present. The metadata standard is self-describing,
so a browser only needs lookup and cross-linking — no generative reasoning. This
adds the consumption layer; the AI skills remain the authoring layer.

## What this adds

A `serve` command and a FastAPI app that reads metadata live from Teradata
(cached) and serves an interactive single-page browser.

- `server/service.py` — `DataProductService`: TTL-cached `collect()` wrapper +
  product discovery via a `DBC.DatabasesV` `*_Semantic` scan. Opens/closes a
  fresh connection per request (never shared across threads).
- `server/app.py` — `create_app(service)` with:
  - `GET /api/products` — deployed product names
  - `GET /api/products/{name}?lookback=&refresh=` — full `DataProduct` JSON +
    collection warnings (same shape as the CLI `dump` snapshot)
  - static SPA mounted at `/`
- `server/static/` — module/entity navigation tree, per-entity schema detail
  (columns with type, description, samples, PII/REQUIRED tags), filter box, and
  a warnings banner for non-fatal collection gaps.
- `cli.py serve --host/--port/--ttl` — resolves credentials once, verifies the
  connection (fail-fast), then runs uvicorn.

## Bundled fix

The repo-wide `*.html` ignore in `.gitignore` was silently excluding the SPA
shell `index.html` (the server would ship with no UI). Added a negation for the
static dir and refreshed the stale template-negation path.

## Verification

- `uv run pytest` — 32 passed (new: API shape, static serving, cache hit/refresh,
  `*_Semantic` suffix strip).
- New code is `ruff`-clean. (Pre-existing `F541`/svg.py lint left untouched.)
- End-to-end `serve` against a live system not run here (no DB access in this
  environment); app logic covered by TestClient + unit tests.

## Run it

```
uv run data-product-browser serve     # → http://127.0.0.1:8080
```

## Roadmap

1 plumbing ✓ · 2 shell ✓ · 3 cross-linking ✓ · 4 health tab ✓ · 5 ERD tab · 6 cookbook tab
