# PR: Prominent Trust banner + Schema-tab diagnostic for missing columns

## Summary
- **Trust engine is now a prominent banner**, not a quiet card. UNTRUSTED renders on a deep-red gradient with a glowing red badge and red-tinted score chips; TRUSTED renders on a deep-green gradient with a light-green glowing badge. Title bumped to 22px, status badge to 16px uppercase. Failed/critical counts use punchy red highlight. Agent allowed/blocked is a coloured pill on the right.
- **Schema tab — diagnostic for missing column_metadata**. The same logical-vs-deployed prefix drift that hit `Business_Glossary.related_table` almost certainly hits `column_metadata.table_name` too. When `columnsFor` returns zero rows, the Schema tab now shows the curated row counts for any near-miss tables (matching by shared token, e.g. `Call_Summary`), so you can see at a glance whether the rows exist under a different name or really aren't there.
- **`columnsFor` now uses the same qualified-name matcher** as `glossaryFor` — accepts bare `Call_Summary_H` or qualified `CallCentre_Domain.Call_Summary_H`.

## Why CallScore / CallScoreCount / CallSummary show "No column metadata"
Most likely the same root cause as the glossary issue: `column_metadata` rows were curated against the *logical* qualified name (e.g. `CallCentre_Domain.Call_Summary_H`) rather than the bare deployed table name. The Schema tab will now show this near-miss list and tell you exactly which logical prefix the curated rows are tagged with. If the list is empty, the rows really are absent and need to be authored.

## Test plan
- [ ] UNTRUSTED product: banner glows red with a clear red badge.
- [ ] TRUSTED product: banner glows light green with a clear green badge.
- [ ] CallSummary Schema tab shows either populated rows or a yellow diagnostic listing the table names the curated rows are tagged against.
