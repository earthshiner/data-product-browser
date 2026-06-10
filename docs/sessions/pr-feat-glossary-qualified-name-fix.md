# PR: Glossary fix — qualified-name matcher + SQL realign script

## Summary
Two-pronged fix for empty Glossary tabs on every entity.

### Root cause
`Business_Glossary.related_table` rows reference *logical* module names
(`CallCentre_Domain.Call_Score_H`) but the deployed databases are *physical*
(`CallCentre_DOM_STD_T.Call_Score_H`). SQL needs exact matches, so the join
from `entity_metadata` to `related_table` never lands.

### Fixes
1. **Browser**: `glossaryFor` and `decisionsFor` now accept either a bare
   table name or a qualified `<db>.<table>` value — splits on `.` and
   compares the table component to the entity-name variants.
2. **SQL realign script** (`docs/fixes/business-glossary-related-table-realign.sql`):
   rewrites the legacy logical prefix to the deployed database name for
   `Business_Glossary.related_table` and `Design_Decision.affects_table`.
   Idempotent — only matches rows that still hold the legacy prefix, and
   ships a SELECT preview + post-update verification query.

Mapping applied:

| Legacy prefix | Deployed database |
|---|---|
| `CallCentre_Domain` | `CallCentre_DOM_STD_T` |
| `CallCentre_Prediction` | `CallCentre_PRE_STD_T` |
| `CallCentre_Semantic` | `CallCentre_SEM_STD_T` |
| `CallCentre_Memory` | `CallCentre_MEM_STD_T` |
| `CallCentre_Search` | `CallCentre_SCH_STD_T` |
| `CallCentre_Observability` | `CallCentre_OBS_STD_T` |

## Test plan
- [ ] Preview SELECT (step 0 in the SQL script) lists the legacy prefixes.
- [ ] Run the UPDATEs; verification SELECT (step 8) returns zero rows.
- [ ] Reload the browser — Glossary tab populates for Call_Summary, Agent, etc.
- [ ] Even without the SQL run, the browser now surfaces glossary rows whose
      `related_table` already uses the correct deployed db name.
