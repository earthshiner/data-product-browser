# Architecture

A single Python package, three layers: **collector** (Teradata → typed models), **renderers** (typed models → HTML/SVG), **server** (FastAPI shell + cached service serving the same typed models as JSON to a static SPA).

```
┌──────────────┐       ┌───────────┐       ┌─────────────────┐       ┌─────────┐
│ Teradata     │──────▶│ collector │──────▶│ DataProduct     │──────▶│ render  │──▶ Cookbook / Ops HTML
│ (DBC + each  │       │  (one     │       │ (pydantic v2)   │       │         │
│  module's    │       │   query   │       │                 │       └─────────┘
│  catalogue)  │       │   per     │       │                 │       ┌─────────┐
└──────────────┘       │   table)  │       │                 │──────▶│ server  │──▶ /api JSON ─▶ SPA
                       └───────────┘       └─────────────────┘       └─────────┘
```

Files: `cli.py` is the entry point; everything else is library code that can be imported and called from a notebook or another service.

## `collector.py`

`collect(product_name, connection)` runs one `SELECT *` per catalogue table and returns a `tuple[DataProduct, list[str]]`. Each query is wrapped in `q_opt(...)` so a missing table, permission gap, or pydantic validation failure becomes a warning string rather than aborting the whole collection. Result: the browser still loads when one module is half-deployed.

Inputs:

- `<registry_db>.active_data_product_registry` — list of `RegistryEntry` rows, one per product, naming the module databases.
- Per module (`semantic`, `memory`, `observability`, …) — `entity_metadata`, `column_metadata`, `table_relationship`, `view_metadata`, `data_lineage`, `Query_Cookbook`, `Business_Glossary`, `Design_Decision`, `data_quality_metric`, `change_event`, `lineage_run`, `agent_outcome`, etc.
- `DBC.TablesV` — for the uncatalogued-table coverage check (see [docs/browser-ui.md](browser-ui.md#coverage-check--uncatalogued-tables)). Soft-degrades on permission failure.

The `column_catalogue` view is read after `column_metadata` and used to **overlay** the friendly `data_type` (e.g. `'DECIMAL(7,4)'`) onto each column — `column_metadata` only stores the raw dictionary code (`'D'`, `'CV'`).

## `models.py`

Pydantic v2 models, one per catalogue table, plus the aggregate `DataProduct`. All fields are deliberately permissive (`Optional`) so minor version drift in a deployment downgrades to missing values, not a hard validation error. `model_config = ConfigDict(extra="ignore")` means deployments with extra columns still parse.

Notable types: `EntityMetadata`, `ColumnMetadata`, `TableRelationship`, `ViewMetadata`, `Recipe`, `GlossaryTerm`, `DesignDecision`, `QualityMetric`, `LineageRun`, `AgentOutcome`, `TrustReport`, `OrphanTable`. The aggregate is `DataProduct`.

## `server/`

`server/app.py` builds a FastAPI app with three routes:

| Route | Purpose |
|---|---|
| `GET /api/products` | List active product names from the registry. |
| `GET /api/products/{name}?lookback&refresh` | Full `DataProduct` JSON + warnings. Cached. |
| `GET /api/ddl?database&table` | Lazy `SHOW TABLE` returning raw + syntax-highlighted DDL. Identifiers validated against a safe-name regex before interpolation. |

`server/service.py` is the cached `DataProductService`. It takes a `connection_factory` (zero-arg callable returning a fresh `teradatasql` connection — never shared across threads), a TTL, and a registry-db override. `get(product_name)` returns the cached `(DataProduct, warnings)` if it's still fresh; otherwise opens a connection, calls `collector.collect`, caches the result, and closes the connection.

`server/static/` is the SPA:

- `index.html` — single-page shell, all CSS inline.
- `app.js` — vanilla JS (no framework), ~1700 lines. Renders the navigation tree, entity detail tabs, operations dashboard, cookbook, and entity-map ERD from `state.data`.
- `brand/` — Teradata wordmark + symbol PNGs (used in the header and as the favicon — never recreated, per brand guidelines).
- `favicon.svg` — superseded by `brand/teradata_sym_rgb_pos.png`; retained only because the file is small and harmless.

## `renderers/`

| File | Output |
|---|---|
| `cookbook.py` | Jinja2-rendered Cookbook HTML (one file per product). |
| `ops_dashboard.py` | Operational health HTML dashboard. |
| `erd.py` | Column-level ERD SVG. Embedded in the cookbook recipes; mirrored visually by the live entity-map in `app.js`. |
| `svg.py` | Recipe entity-flow SVG (boxes + arrows between tables a recipe touches). |
| `sql_highlight.py` | Teradata SQL syntax highlighter — vocabulary built from `teradata.syn`: ~190 keywords, ~30 types, ~100 functions. Emits `<span class="sql-keyword">`, `<span class="sql-type">`, `<span class="sql-function">`, `<span class="sql-string">`, `<span class="sql-number">`, `<span class="sql-comment">`. The class palette is defined in both `index.html` (live app) and `templates/cookbook.html.j2`. |
| `jupyter.py` | Same metadata, rendered for a notebook. |
| `templates/` | Jinja2 sources. |

## CLI

`cli.py` wires the library to Typer. Each command resolves credentials via `_resolve_host_user` + `_get_password` (see [docs/configuration.md](configuration.md)), opens a `teradatasql.connect`, and dispatches:

- `serve` → builds a `DataProductService` with a `connection_factory` lambda and starts Uvicorn on `--host:--port`.
- `generate` → opens one connection, calls `collect`, renders the requested artefacts to `--output`.
- `dump` → opens one connection, calls `collect`, writes the `DataProduct` JSON to `--output`.
- `render` → loads a snapshot JSON (no connection), renders artefacts.
- `store-password` → prompts and saves to OS keyring.

All command-line failures route through `_handle_connection_error`, which translates Teradata error codes (8017 / 1017 / 28000 / "invalid credentials" / "unable to connect" / 10054) into one of three branded help messages with cross-shell env-var snippets.

## Cache strategy

Two levels:

- **Per-process** — `DataProductService` keeps `(expires_at, DataProduct, warnings)` per product name. TTL configured via `--ttl` (default 300s).
- **Per-browser** — `app.js?v=<n>` cache-buster on the JS bundle in `index.html`. Bump the integer on any JS change to force every browser to re-fetch.

## Adding a new catalogue table

1. Add a pydantic model in `models.py` and a list field on `DataProduct`.
2. Add a `q_opt(...)` call in `collector.py` after the existing reads for the same module.
3. Add the field to the `DataProduct(...)` return at the bottom of `collect`.
4. Either render it in one of the existing renderers, or surface it in `app.js` as a new section/tab.

No server route change is needed — `DataProduct.model_dump(mode="json")` automatically includes new fields.

## Adding a new highlight token

Edit `_TYPES`, `_KEYWORDS`, or `_FUNCTIONS` in `renderers/sql_highlight.py`. The matching order is types → keywords → functions, so the same identifier in two sets resolves to the earlier classification (use this deliberately when a word is ambiguous — `INTERVAL` is a type, not a keyword).
