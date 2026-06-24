# data-product-browser

Browse and document any **AI-Native Data Product** deployed on Teradata. Connects directly to the governance registry, reads each module live, and presents the metadata three ways: an interactive web UI, static HTML artefacts (Cookbook, Ops Dashboard), and raw JSON snapshots.

Brand-aligned UI (Teradata orange + Navy, Inter typography) with a hover-traced column-level ERD, crow's-foot cardinality, SVG export, a DDL tab per entity, and an uncatalogued-tables coverage check.

## Quick start

```bash
cp .env.example .env       # fill in TD_HOST, TD_USER
uv sync
uv run data-product-browser store-password   # optional — saves to OS keyring
uv run data-product-browser serve            # http://127.0.0.1:8080
```

That's it. Open the URL, pick a product from the dropdown, and the tree fills in.

## Commands

| Command | Description |
|---|---|
| `serve` | Run the interactive web browser (see **[docs/browser-ui.md](docs/browser-ui.md)**) |
| `generate <product>` | Write Cookbook + Ops Dashboard HTML for one product |
| `dump <product>` | Save the full metadata snapshot as JSON (offline-friendly) |
| `render <snapshot.json>` | Render the HTML artefacts from a saved snapshot (no DB connection) |
| `store-password` | Save Teradata credentials to the OS keyring |

Common options on every command:

```
--td-host HOST       TD_HOST            Teradata host
--td-user USER       TD_USER            Username
--td-password PWD    TD_PASSWORD        Password (keyring preferred — see store-password)
--registry-db DB     TDP_REGISTRY_DB    Governance registry database
--lookback DAYS      (90)               Observability lookback window
```

See **[docs/configuration.md](docs/configuration.md)** for the full credential resolution order, registry conventions, and `.env` setup.

## Browser features (at a glance)

- **Operations dashboard** — trust, quality, freshness, lineage runs, agent outcomes.
- **Entity map (ERD)** — attribute-level boxes, layered layout, crow's-foot endpoints from the catalogued cardinality, hover-traced highlights, per-entity sub-graph SVG export, full-diagram SVG export.
- **Entity detail tabs** — Schema, Views, Relationships, **DDL** (lazy `SHOW TABLE` with syntax highlighting + Copy), Glossary, Decisions.
- **Cookbook** — every catalogued recipe with parameter notes, complexity, and a column ERD inline.
- **Uncatalogued tables** — physical tables in the data product's databases that lack `entity_metadata` rows are surfaced explicitly (banner + dashed placeholder boxes in the ERD). Nothing is silently hidden.
- **Collapsible modules** — the navigation tree opens compact; expand the modules you care about. Typing in the search box force-expands everything so matches stay visible.

The web UI is documented in detail in **[docs/browser-ui.md](docs/browser-ui.md)**. The internal layout (collector → service → renderers → server) is documented in **[docs/architecture.md](docs/architecture.md)**.

## Offline workflow

```bash
# On a machine with database access:
uv run data-product-browser dump CallCentre --output ./snapshots

# Anywhere else, no DB connection needed:
uv run data-product-browser render snapshots/CallCentre.json --output ./output
```

## Running tests

```bash
uv run pytest
```

## Project layout

```
src/data_product_browser/
├── cli.py                # serve / generate / dump / render / store-password
├── collector.py          # one query per module, plus DBC coverage check
├── config.py             # registry-db resolution
├── models.py             # pydantic v2 models for every catalogue table
├── server/
│   ├── app.py            # FastAPI routes (/api/products, /api/ddl, …)
│   ├── service.py        # cached DataProductService
│   └── static/           # browser UI (index.html, app.js, brand assets)
└── renderers/
    ├── cookbook.py       # Jinja2 cookbook generator
    ├── ops_dashboard.py  # operational health dashboard
    ├── erd.py            # column-level ERD SVG (Cookbook embed)
    ├── svg.py            # recipe entity-flow SVG
    └── sql_highlight.py  # Teradata SQL syntax highlighter
```

Further reading: **[docs/browser-ui.md](docs/browser-ui.md)**, **[docs/configuration.md](docs/configuration.md)**, **[docs/architecture.md](docs/architecture.md)**.
