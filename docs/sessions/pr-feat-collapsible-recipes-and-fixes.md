# PR: Collapsible recipes + lenient entity-name matching

## Summary
- **Collapsible recipe cards** — each recipe is now a `<details>` card, collapsed by default. Summary shows the title and the Interactive/Batch + complexity + module pills; clicking expands the description, use case, SQL, parameters, and perf notes.
- **Expand all / Collapse all** controls added to the cookbook toolbar.
- **Lenient `columnsFor` / `glossaryFor` / `decisionsFor`** — investigation suggests the *CallSummary* / *CallScoreCount* etc. entities show "No column metadata" and zero Glossary mentions not because the data is missing, but because:
  - `column_metadata` rows are curated against either the base table (`Call_Summary_H`) or the companion view (`Call_Summary_Current`), and the previous match was case-sensitive on a single name.
  - `Business_Glossary.related_table` is typically tagged against the logical entity (`Call_Summary`), not the SCD2 history table (`Call_Summary_H`).
  
  Both lookups are now case-insensitive and accept the table name, view name, entity name, or the table/view stripped of the `_H` / `_Current` suffix. Same for `decisionsFor`.

## What to verify in deployment
If recipes still show "No column metadata" after this fix, the curated rows really are absent — confirm by querying `<semantic>.column_metadata` directly for the offending table. Same for `<memory>.Business_Glossary` `related_table` values.

## Test plan
- [ ] Cookbook recipes render collapsed by default; clicking the summary expands them.
- [ ] Expand all / Collapse all toggle every recipe in the current filter.
- [ ] CallSummary entity now shows column rows if curated against either `Call_Summary_H` or `Call_Summary_Current`.
- [ ] Glossary tab shows terms tagged `related_table = 'Call_Summary'`.
