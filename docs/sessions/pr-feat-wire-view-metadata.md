# Wire view_metadata + lineage relocation into the browser

Targets `main`. Aligns the browser with the live CallCentre standard refactor
(definitional `data_lineage` relocated to Semantic; operational `lineage_run` in
Observability; new `view_metadata` catalogue).

## Changes

### Models
- `DataLineage` → definitional shape (drops run columns; adds `is_active`,
  `registered_dts`, `retired_dts`). Now sourced from Semantic.
- New `LineageRun` (Observability execution log) and `ViewMetadata` (Semantic
  1:M table→views catalogue).
- `DataProduct` gains `view_metadata` and `lineage_run`; `data_lineage` moves to
  the Semantic group.

### Collector
- `data_lineage` and `view_metadata` read from the **Semantic** view DB;
  `lineage_run` read from the **Observability** view DB (windowed).

### Frontend
- Entity detail: new **Views** tab listing every view exposing the entity's base
  table — view name, database, type (LOCKING/CURRENT/ENRICHED/…), purpose, and a
  PRIMARY flag.
- Operations dashboard: "failed lineage runs", "last lineage run", the lineage
  table, and the records-per-run chart now read `lineage_run` (joined to
  `data_lineage` for the target object).

### Legacy renderer
- `ops_dashboard.py` reads run telemetry from `lineage_run` (recent runs +
  freshness) instead of the now-definitional `data_lineage`.

## Verification
- `uv run pytest` — 19 passed; new code ruff/node-check clean.
- Preview (harness re-keyed to base tables to mirror real `entity_metadata`):
  the Views tab shows `Call_H` exposed by `Call_H` (LOCKING/PRIMARY),
  `Call_Current` (CURRENT), `Call_Enriched` (ENRICHED); Operations renders off
  `lineage_run`. No console errors.

## Note
`data_lineage`/`view_metadata` now resolve from the Semantic view database. The
collector keys the Views tab on `entity.database_name + table_name` ==
`view_metadata.base_database + base_table`, which matches how real
`entity_metadata` is keyed (base table, e.g. `CallCentre_DOM_STD_T.Call_H`).
