# Trust engine rule observations (not actionable from this repo)

These belong in the trust engine rule definitions, not in the data product
itself. Captured here so we don't lose track of them.

## 1. `BUS_VIEW_SELECTS_TABLE_DIRECTLY` — false positive on `column_catalogue`

The view `CallCentre_SEM_BUS_V.column_catalogue` selects from `DBC.ColumnsV`
and `CallCentre_SEM_STD_V.column_metadata` / `view_column_type` — both are
either dictionary or `_STD_V` access views, never `_STD_T`. The rule still
flags it because its WHERE clause contains the literal pattern
`'CallCentre\_%\_STD\__'`, and the rule's text scan matches `_STD_T` inside
that LIKE pattern.

Suggested rule fix (in the trust engine, not here):

- Parse the actual referenced objects (DBC.ViewVRefs / DBC.TablesV by view
  text reference) rather than regex over view text.
- Or, exclude `_STD_T` matches that appear only inside string literals.

If the rule must stay text-based, a tactical workaround is to build the
literal at runtime with string concatenation
(`'CallCentre\_%\_STD\_' || 'T'`) — but that masks legitimate violations
elsewhere and is not recommended.

## 2. `ENTITY_DELETED_FLAG_MISSING` — redundant when `is_active` exists

The product convention already encodes logical deletion as
`is_active = 0`. Forcing an additional `is_deleted` column on every entity
duplicates the same fact in two places, invites drift, and breaks for
tables that are not delete-tracked at all (e.g. derived feature stores
like `call_behaviour_features` and `model_prediction`).

Recommended: drop the `ENTITY_DELETED_FLAG_MISSING` rule, or relax it to
accept `is_active` as the deletion flag when `is_deleted_column` is null
on the entity_metadata row.

## 3. Trust engine status not accounting for recipe `is_batch`

If the trust engine treats every recipe as a live agent query, batch
recipes (`is_batch = 1`) will fail "no parameters" / "no time bound"
checks they shouldn't be subject to. Recipe-level checks should branch
on `is_batch`: interactive recipes get the full agent-safety contract,
batch recipes get a relaxed set (scheduled, runs with operator-supplied
windows, etc.).
