# Browser UI

The web browser (`data-product-browser serve`) is a thin single-page app served by FastAPI from `src/data_product_browser/server/static/`. It reads `/api/products/<name>` once per product (cached server-side for 5 minutes by default) and renders everything from that one JSON snapshot.

## Header

Teradata-branded Navy bar with the official `teradata.` wordmark, a vertical divider, and an "Data Product Browser" subtitle in Inter Light. A 3px orange brand accent runs along the bottom. The product picker on the right lists every `ACTIVE` row from the governance registry; an optional refresh checkbox skips the cache for the next request.

## Navigation tree

Three pinned views at the top, then a per-module entity list:

- **📊 Operations** — trust score, quality metrics, freshness, lineage runs, agent outcomes. Sections are collapsible (`<details>` blocks).
- **🗺 Entity map (ERD)** — see below.
- **📖 Cookbook** — every recipe with parameters, complexity, performance notes, and an embedded column ERD per recipe.

Below those, each **module** (Domain, Semantic, Memory, Observability, Prediction, Search, …) is a click-to-expand group with an entity count. The tree starts compact — every module collapsed. Typing in the search box force-expands every module so matches always show.

## Entity detail

Clicking an entity opens its detail panel with a metadata grid (database/table, module, surrogate/natural key, temporal pattern, industry standard) and six tabs:

| Tab | What it shows |
|---|---|
| Schema | Every column from `column_metadata`, badges for PK / NK / FK / PII / SENS / NN, friendly type from `column_catalogue`. |
| Views | Locking-view companions and business views from `view_metadata`. |
| Relationships | Every incoming and outgoing relationship with cardinality, type, and meaning. |
| **DDL** | Lazy `SHOW TABLE` via `/api/ddl`. Result is syntax-highlighted with the full Teradata vocabulary (~190 keywords, ~30 types, ~100 functions), copied verbatim to the clipboard via the **Copy** button. Cached per entity for the session. |
| Glossary | Business-glossary entries that reference this entity. |
| Decisions | Design decisions affecting this entity. |

## Entity map (ERD)

Attribute-level column ERD with layered left-to-right layout (referenced tables left, dependents right).

- **Boxes** carry the module colour as a left bar; columns show name + type + PK/NK/FK/PII/SENS/NN badges.
- **Collapse / expand** per entity via the `−` / `+` toggle in the box header; **Collapse all** / **Expand all** in the toolbar.
- **Crow's foot endpoints** — the parser recognises `1:N`, `N:1`, `1:1`, `M:N`, `0..1:N`, `1..*:1`, `one-to-many`, etc., and draws the conventional five glyphs (one / zero-or-one / many / one-or-many / zero-or-many). Unparseable cardinality falls back to a dot.
- **Edge labels** are capped to the available inter-lane gap (max ~220px). Cardinality is preserved verbatim; long meaning text is ellipsised with the full text in a `<title>` hover tooltip.
- **Hover** any box: it and its connected boxes stay opaque, every other element dims to 12% so the relationship trace is easy to follow.
- **Uncatalogued tables** are rendered as dashed PII-coloured placeholder boxes in a "Uncatalogued (N)" block beneath the layered graph. Tooltip explains they exist in the database but are missing from `entity_metadata`.
- **Scroll** — horizontal scrollbar is always visible (small diagrams included, for affordance), the scroll container is capped to `calc(100vh - 220px)` so the scrollbar stays in the viewport rather than below the page fold.

### SVG export

Two ways to export the current ERD as a standalone, self-contained SVG:

- **Toolbar `⤓ Export SVG`** — the entire diagram. CSS variables are read from the live document and inlined alongside the `.erd-*` rules, so the file renders correctly outside the app.
- **Per-box `⤓` icon** (left of the `+/−` toggle in each entity header) — a sub-graph of just that entity, the entities directly connected to it, and the edges between them. ViewBox is computed tight to the kept boxes so the page-level legend is clipped out.

In-app toggle and export controls are stripped from the exported SVG.

## Cookbook

Each recipe is a `<details>` block with a coloured left border (orange for interactive, navy for batch) and pills for mode, complexity, and module. Inside:

- The original `use_case` statement.
- The SQL template with full Teradata syntax highlighting (keywords, data types, functions, strings, numbers, comments — separate colours per class).
- Inline column ERD showing only the tables touched by the recipe.
- Parameter notes (`params-note`) and performance notes (`perf-note`).
- A **Copy** button per recipe.

## Coverage check — uncatalogued tables

On every collection, the server queries `DBC.TablesV` for every database referenced by either `entity_metadata.database_name` or `data_product_map.database_name`. Any physical table (`TableKind = 'T'`) without a matching `entity_metadata` row is surfaced two ways:

1. A grouped warning banner (visible on every view of the browser) listing each orphan under its database, plus a fix hint.
2. Dashed placeholder boxes in the entity-map view (see above).

If the connecting user lacks `SELECT` on `DBC.TablesV`, the check degrades to a single skip warning ("DBC.TablesV not accessible") and nothing crashes.

## Loading + error states

- **Loading a product** — the detail pane shows a 56px Teradata-orange ring spinner (pure CSS conic-gradient; no GIF) labelled "Loading <product-name>…". Honours `prefers-reduced-motion`.
- **DDL fetch** — the same spinner with "Running SHOW TABLE…".
- **API errors** — surfaced inline in the relevant panel with the first line of the database error message.

## Cache busting

`index.html` references `app.js?v=<n>`. Bumping the integer after a JS change forces every browser to re-fetch. Current value is the `v=` in the `<script>` tag near the bottom of `index.html`.
