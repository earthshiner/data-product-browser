# Realign legacy renderers to the deployed standard

Targets `main`.

## Why

The static HTML artefact generators (`cookbook.html`, `ops_dashboard.html`,
produced by CLI `generate`/`render`) still referenced the pre-alignment sample
schema, so they crashed at call-time after the live-standard rework. The live
browser/`serve` was unaffected; this restores the static artefacts.

## Changes

### ops_dashboard.py
- Quality on `is_threshold_met` (polarity flip) + `quality_threshold`.
- Lineage health, recent runs and freshness from `data_lineage`
  (`run_dts`/`run_status`/`records_read`/`records_written`); fields not in the
  standard (`run_duration_ms`, `records_rejected`, `error_message`) set null.
- Change events on `change_dts` / `change_type` (no success flag).
- Agent summary on `outcome_status` (confidence dropped — not in the standard).
- Module status from `is_current`; trust score prefers `trust_engine_latest`.
- **Output JSON keys kept stable**, so `ops_dashboard.html.j2` needs no change.

### cookbook.py / svg.py / erd.py
- Relationships use `source_*` / `target_*` + `relationship_meaning`.
- `join_type` removed → optional relationships render dashed based on
  `is_mandatory`.
- Dropped the removed `naming_standard` section.

### cookbook.html.j2
- Entity table: `temporal_pattern` / `industry_standard` (was category / approx
  rows). Column table: `data_classification` (was sample values). Relationship
  table: source/target + mandatory + `relationship_meaning`.

### CLI
- `generate` / `dump` `product` arg help now says "registry product name".

## Verification

- `uv run pytest` — 18 passed (restored 3 renderer smoke tests: cookbook renders,
  ops renders, ops `__DATA__` is valid JSON).
- New/edited code `ruff`-clean (pre-existing E501 long-lines in template strings
  left untouched).
