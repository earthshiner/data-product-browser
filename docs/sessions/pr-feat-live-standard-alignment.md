# Align browser to the deployed registry-driven standard

**Stacked on `feat/local-server-browser`** — review/merge that first.

## Why

Testing against a live system revealed the browser's models (inherited from the
guide repo's `MortgagePlatform` *sample*) did not match the deployed AI-Native
Data Product standard. Both database naming and table schemas had drifted, so
the collector could not read a real product. Verified against the live
`CallCentre Data Product` via the connected MCP.

## Key changes

### Discovery — registry-driven (configurable)
- New `config.py`: resolves the governance registry database via
  `--registry-db` > `TDP_REGISTRY_DB` > default (`DataProductsMaster_GOV_BUS_V`).
  The registry DB name differs per system, so it must be configurable.
- `collector.discover_products()` reads `active_data_product_registry`;
  `collect()` resolves each module's `*_view_database` (business views preferred,
  e.g. `CallCentre_SEM_BUS_V`) instead of guessing `{product}_Semantic` suffixes.

### Models realigned to deployed columns
- Semantic: `module_id`, `entity_metadata_id`, `column_metadata_id`,
  `source_*/target_*` + `relationship_meaning` (no `join_type`),
  `data_classification`/`allowed_values_json`.
- Observability: `is_threshold_met` (inverted polarity), `quality_threshold`,
  `change_dts`/`change_type`, and `data_lineage` run telemetry
  (`run_status`/`run_dts`/`records_read/written`) which replaces the absent
  `lineage_run`.
- Added `RegistryEntry` and `TrustReport` (`trust_engine_latest`).
- Dropped non-existent `naming_standard`, `lineage_run`, `lineage_graph`.
- `extra="ignore"` so deployments with extra columns parse cleanly.

### Frontend
- Relationships use source/target + `relationship_meaning`.
- Schema shows a Classification column + PII/SENSITIVE/REQUIRED tags; entity meta
  grid shows View / Temporal pattern / Industry standard.
- Health rebuilt on `data_quality_metric` (`is_threshold_met`), `change_event`,
  and `data_lineage`; new **trust panel** from `trust_engine_latest`.
- Product picker reads the registry (name + version).

## Verification

- **Every collector query executed against the live views via MCP** — real
  counts: 10 entities, 18 columns, 11 relationships, 40 recipes, 23 decisions,
  12 glossary terms, 350 quality metrics, 270 change events, 7 lineage runs,
  58 agent outcomes.
- `uv run pytest` — 15 passed; new code `ruff`-clean.
- UI rendered end-to-end (preview harness, realigned-schema data): trust panel,
  source/target relationships with cross-jumps, classification/PII tags,
  quality OK/FAILED, lineage runs. No console errors.
- Full live `serve` not run: the browser's `.env` host was unreachable from the
  dev environment; the live data was reached via MCP, against which all queries
  and the schema were validated.

## Follow-up (not in this PR)

The legacy `cookbook` / `ops_dashboard` HTML renderers (CLI `generate`/`render`)
still reference pre-rework field names and need realignment. The server/browser
do not use them and are unaffected.
