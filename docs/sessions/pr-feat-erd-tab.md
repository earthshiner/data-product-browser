# Entity map (ERD) tab

Targets `main`.

## What

A product-level **entity-relationship diagram** as a new nav view ("Entity map"),
built deterministically from `entity_metadata` + `table_relationship`.

- One column per module; entity nodes coloured by module.
- Relationship edges (source → target) as curved connectors with arrowheads and
  `relationship_meaning` tooltips; only edges whose both endpoints are mapped
  entities are drawn.
- Nodes show entity name, backing table, and column count; clicking a node opens
  that entity's detail page.
- Hand-rolled inline SVG — no graph library, no build step. Horizontal scroll for
  wide products.

## Verification

- `uv run pytest` — 15 passed; `ruff`-clean; `node --check` clean.
- Rendered end-to-end via the preview harness (enriched with Domain + Prediction
  entities and four relationships): two module columns, coloured nodes, edges
  with arrowheads, and a node click correctly opening the entity. No console
  errors.
