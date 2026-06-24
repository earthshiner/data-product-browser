"""Renders the Data Product Cookbook HTML artefact.

All data is rendered server-side via Jinja2. The resulting file is fully
self-contained and requires no network access to display.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..models import DataProduct, EntityMetadata, TableRelationship
from .erd import make_column_erd
from .jupyter import make_python_code, notebook_data_uri
from .sql_highlight import highlight_sql
from .svg import make_join_diagram

_TEMPLATES_DIR = Path(__file__).parent / "templates"

# FROM / JOIN target — captures '<db>.<tbl>' or '<tbl>' followed by an
# optional 'AS alias' / 'alias' token. Stops at a keyword that ends the alias.
_FROM_JOIN = re.compile(
    r"\b(?:FROM|JOIN)\s+"
    r"(?P<ref>(?:[A-Za-z_][A-Za-z0-9_$]*\.)?[A-Za-z_][A-Za-z0-9_$]*)"
    r"(?:\s+(?:AS\s+)?(?P<alias>[A-Za-z_][A-Za-z0-9_$]*))?",
    re.IGNORECASE,
)

# ON or AND predicate that equates two qualified column refs.
_EQ_JOIN = re.compile(
    r"([A-Za-z_][A-Za-z0-9_$]*)\.([A-Za-z_][A-Za-z0-9_$]*)"
    r"\s*=\s*"
    r"([A-Za-z_][A-Za-z0-9_$]*)\.([A-Za-z_][A-Za-z0-9_$]*)"
)

# Tokens that follow 'JOIN <tbl>' but should NOT be consumed as the alias.
_ALIAS_STOPWORDS = frozenset(
    "ON USING WHERE GROUP ORDER HAVING QUALIFY LEFT RIGHT INNER OUTER FULL JOIN "
    "CROSS LATERAL UNION INTERSECT MINUS EXCEPT AND OR LIMIT OFFSET SAMPLE".split()
)

# Any '<db>.<table>' reference in SQL. Teradata identifiers are
# alphanumeric + underscore + $; no dots allowed inside a name.
_QUALIFIED_REF = re.compile(r"\b([A-Za-z_][A-Za-z0-9_$]*)\.([A-Za-z_][A-Za-z0-9_$]*)\b")


def _known_databases(entities: list[EntityMetadata]) -> set[str]:
    """Return the set of database names that legitimately appear in the
    product's SQL. Includes both the ``database_name`` field and the database
    portion of a qualified ``view_name`` (when present). Upper-cased.
    """
    dbs: set[str] = set()
    for e in entities:
        if e.database_name:
            dbs.add(e.database_name.upper())
        if e.view_name and "." in e.view_name:
            v_db, _, _ = e.view_name.partition(".")
            if v_db.strip():
                dbs.add(v_db.strip().upper())
    return dbs


def _extract_sql_tables(sql: str, entities: list[EntityMetadata]) -> list[str]:
    """Return every ``<db>.<table>`` short name from the SQL whose ``db`` part
    is a known product database.

    The DB-prefix filter is essential — without it, ``model_pred.call_id``
    (alias.column) would be matched as if it were a table reference. We learn
    the legitimate prefixes from ``entity_metadata`` (both base and view
    database names). Used by the Join Diagram so derived views that aren't
    catalogued in their own right still render — provided they live in a
    known database.

    Names that map to a catalogued entity (via either ``table_name`` or
    ``view_name``) are returned in their canonical base-table form, so the
    Join Diagram dedupes against ``_extract_table_names`` output cleanly.
    """
    known_dbs = _known_databases(entities)

    # (db_upper, name_upper) -> canonical base-table short name.
    canonical: dict[tuple[str, str], str] = {}
    for e in entities:
        base_db = (e.database_name or "").upper()
        if base_db and e.table_name:
            canonical[(base_db, e.table_name.upper())] = e.table_name
        if e.view_name:
            view_raw = e.view_name.strip()
            if "." in view_raw:
                v_db, _, v_tbl = view_raw.partition(".")
                if v_db.strip() and v_tbl.strip():
                    canonical[(v_db.strip().upper(), v_tbl.strip().upper())] = e.table_name
            elif base_db:
                canonical[(base_db, view_raw.upper())] = e.table_name

    seen: list[str] = []
    seen_upper: set[str] = set()
    for m in _QUALIFIED_REF.finditer(sql):
        db, table = m.group(1), m.group(2)
        if db.upper() not in known_dbs:
            continue
        # Prefer the canonical base-table name when known; otherwise emit the
        # raw name from the SQL (an uncatalogued derived view).
        name = canonical.get((db.upper(), table.upper()), table)
        up = name.upper()
        if up not in seen_upper:
            seen_upper.add(up)
            seen.append(name)
    return seen


def _infer_relationships_from_sql(
    sql: str, entities: list[EntityMetadata]
) -> list[TableRelationship]:
    """Synthesise ``TableRelationship`` rows from a recipe's JOIN ON clauses.

    Only used for the per-recipe Column ERD — gives the user the relationship
    lines for the joins actually performed even when those joins are not
    catalogued in ``table_relationship`` (e.g. recipe joins two facts directly
    that the catalogue records only via a shared dimension).

    Both ends must resolve to catalogued entities (otherwise no columns exist
    to anchor an edge to). The synthesised row is marked ``relationship_type
    = 'INFERRED'`` so the ERD's hard/soft styling treats it as a soft line.
    """
    known_dbs = _known_databases(entities)

    # Resolve (db, name) -> canonical (db, base-table). Same lookup the join
    # extractor uses; needed to map alias-bound view references back to entity
    # rows we have columns for.
    canonical_pair: dict[tuple[str, str], tuple[str, str]] = {}
    for e in entities:
        base_db = (e.database_name or "").upper()
        if base_db and e.table_name:
            canonical_pair[(base_db, e.table_name.upper())] = (e.database_name, e.table_name)
        if e.view_name:
            v = e.view_name.strip()
            if "." in v:
                vdb, _, vtbl = v.partition(".")
                if vdb.strip() and vtbl.strip():
                    canonical_pair[(vdb.strip().upper(), vtbl.strip().upper())] = (
                        e.database_name,
                        e.table_name,
                    )
            elif base_db:
                canonical_pair[(base_db, v.upper())] = (e.database_name, e.table_name)

    # alias_upper -> (canonical_db, canonical_table). Also covers the
    # 'no-alias' case (alias == table name).
    alias_map: dict[str, tuple[str, str]] = {}
    for m in _FROM_JOIN.finditer(sql):
        ref = m.group("ref")
        alias_raw = m.group("alias")
        # If the captured 'alias' is actually a SQL keyword (ON / WHERE / …),
        # the FROM/JOIN target had no alias.
        alias = alias_raw if alias_raw and alias_raw.upper() not in _ALIAS_STOPWORDS else None
        if "." in ref:
            db, _, tbl = ref.partition(".")
        else:
            db, tbl = None, ref
        # Only proceed when the db prefix is recognised (or absent and we can
        # find the bare table in the catalogue).
        canonical = None
        if db and db.upper() in known_dbs:
            canonical = canonical_pair.get((db.upper(), tbl.upper()))
        if not canonical:
            # Unqualified — pick the first catalogued match for the bare name.
            for (_d, n), pair in canonical_pair.items():
                if n == tbl.upper():
                    canonical = pair
                    break
        if not canonical:
            continue
        # Default alias = the table token from the SQL itself (Teradata SQL
        # treats 'FROM t' as binding 't' as the implicit alias).
        bound = alias or tbl
        alias_map[bound.upper()] = canonical

    inferred: list[TableRelationship] = []
    seen: set[tuple] = set()
    next_id = -1  # synthetic ids stay out of the way of real relationships
    for m in _EQ_JOIN.finditer(sql):
        a, ac, b, bc = (g.upper() for g in m.groups())
        src = alias_map.get(a)
        tgt = alias_map.get(b)
        if not src or not tgt or src == tgt:
            continue
        # Edge key keeps the column names so multi-column joins survive.
        key = (min(src, tgt), max(src, tgt), ac, bc)
        if key in seen:
            continue
        seen.add(key)
        inferred.append(
            TableRelationship(
                relationship_id=next_id,
                relationship_name=f"{src[1]}_{ac.lower()}__{tgt[1]}_{bc.lower()}",
                source_database=src[0],
                source_table=src[1],
                source_column=m.group(2),
                target_database=tgt[0],
                target_table=tgt[1],
                target_column=m.group(4),
                relationship_type="INFERRED",
                cardinality=None,
                relationship_meaning="Inferred from recipe JOIN clause",
                is_mandatory=0,
                is_active=1,
            )
        )
        next_id -= 1
    return inferred


def _extract_table_names(sql: str, entities: list[EntityMetadata]) -> list[str]:
    """Return unique short table names from the SQL that map to catalogued entities.

    Matches both the ``table_name`` and ``view_name`` columns from
    ``entity_metadata`` (case-insensitive), since recipes routinely reference
    the business view rather than the base table. Two passes:

    - Pass 1: every qualified ``<db>.<name>`` in the SQL.
    - Pass 2: bare ``<name>`` tokens. Ambiguous short names (same name in
      multiple databases) are still accepted on a first-occurrence basis —
      under-matching produces empty diagrams, which is worse than rendering
      a slightly-superset ERD.

    Order of first occurrence in the SQL is preserved so the diagram lays
    out in reading order.
    """
    # Build (db_upper, name_upper) -> canonical short name, mapping both base
    # table and view forms back to the same canonical short name. view_name in
    # entity_metadata is commonly stored fully-qualified ('db.table'), so split
    # on a dot when present and index BOTH parts.
    catalogued_pairs: dict[tuple[str, str], str] = {}
    catalogued_short: dict[str, str] = {}

    def _index(db: str, name: str, canonical: str) -> None:
        catalogued_pairs.setdefault((db.upper(), name.upper()), canonical)
        catalogued_short.setdefault(name.upper(), canonical)

    for e in entities:
        base_db = (e.database_name or "").strip()
        table = (e.table_name or "").strip()
        if base_db and table:
            _index(base_db, table, e.table_name)
        if e.view_name:
            view_raw = e.view_name.strip()
            if "." in view_raw:
                v_db, _, v_tbl = view_raw.partition(".")
                v_db, v_tbl = v_db.strip(), v_tbl.strip()
                if v_db and v_tbl:
                    _index(v_db, v_tbl, e.table_name)
            elif base_db:
                _index(base_db, view_raw, e.table_name)

    seen: list[str] = []
    matched_upper: set[str] = set()

    def _add(short_name: str) -> None:
        up = short_name.upper()
        if up in matched_upper:
            return
        matched_upper.add(up)
        seen.append(short_name)

    # Pass 1: qualified <db>.<name> matches anywhere in the SQL.
    for m in _QUALIFIED_REF.finditer(sql):
        db, name = m.group(1).upper(), m.group(2).upper()
        canonical = catalogued_pairs.get((db, name))
        if canonical:
            _add(canonical)

    # Pass 2: bare names. The lookup map covers both table_name and view_name,
    # so a SQL that uses business-view names still resolves to the underlying
    # base-table short name (which is what erd.py / svg.py expect).
    for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_$]*)\b", sql):
        token = m.group(1).upper()
        canonical = catalogued_short.get(token)
        if canonical:
            _add(canonical)

    return seen


def _build_context(dp: DataProduct, theme: str = "light") -> dict:
    """Transform the DataProduct into template-friendly dicts."""

    # Group columns by database.table for the Data Dictionary tab
    cols_by_table: dict[str, list] = defaultdict(list)
    for col in dp.columns:
        key = f"{col.database_name}.{col.table_name}"
        cols_by_table[key].append(col)

    # Enrich each recipe with SQL, Jupyter, join diagram, and column ERD
    enriched_recipes = []
    for r in dp.recipes:
        # Two views of the same SQL: every qualified table reference (for the
        # Join Diagram, so derived/uncatalogued views still render) and only
        # catalogued tables (for the Column ERD, which needs column metadata).
        all_tables = _extract_sql_tables(r.sql_template, dp.entities)
        catalogued_tables = _extract_table_names(r.sql_template, dp.entities)
        # Merge: union preserving order — catalogued first, then any additional
        # uncatalogued tables found in the raw SQL.
        seen = {t.upper() for t in catalogued_tables}
        join_tables = list(catalogued_tables)
        for t in all_tables:
            if t.upper() not in seen:
                seen.add(t.upper())
                join_tables.append(t)
        # Filter relationships to only those between tables in this recipe.
        recipe_tables_upper = {t.upper() for t in join_tables}
        recipe_rels = [
            rel
            for rel in dp.relationships
            if rel.source_table.upper() in recipe_tables_upper
            and rel.target_table.upper() in recipe_tables_upper
        ]
        enriched_recipes.append(
            {
                "recipe": r,
                "sql_html": highlight_sql(r.sql_template),
                "join_diagram": make_join_diagram(
                    join_tables,
                    relationships=recipe_rels,
                    entities=dp.entities,
                ),
                "column_erd": make_column_erd(
                    catalogued_tables,
                    dp.columns,
                    # Catalogued relationships + ones inferred from this
                    # recipe's JOIN ON clauses, so the diagram reflects what
                    # the recipe actually joins even when the catalogue lacks
                    # a direct edge between two of its tables.
                    list(dp.relationships)
                    + _infer_relationships_from_sql(r.sql_template, dp.entities),
                    dp.entities,
                    theme=theme,
                ),
                "jupyter_code": make_python_code(r),
                "notebook_uri": notebook_data_uri(r, dp.product_name),
                "notebook_filename": f"{r.recipe_id}.ipynb",
            }
        )

    # Group glossary by category
    glossary_by_cat: dict[str, list] = defaultdict(list)
    for term in dp.glossary:
        glossary_by_cat[term.term_category].append(term)

    # Group decisions by category
    decisions_by_cat: dict[str, list] = defaultdict(list)
    for d in dp.decisions:
        decisions_by_cat[d.decision_category].append(d)

    version = "—"
    if dp.module_registry:
        latest = max(dp.module_registry, key=lambda m: m.version_date)
        version = f"v{latest.module_version}"

    return {
        "product_name": dp.product_name,
        "generated_dts": dp.generated_dts.strftime("%Y-%m-%d %H:%M UTC"),
        "version": version,
        "recipe_count": len(dp.recipes),
        "module_count": len(dp.modules),
        "enriched_recipes": enriched_recipes,
        "cols_by_table": dict(cols_by_table),
        "glossary_by_cat": dict(glossary_by_cat),
        "decisions_by_cat": dict(decisions_by_cat),
        "entities": dp.entities,
        "modules": dp.modules,
        "relationships": dp.relationships,
        "module_registry": dp.module_registry,
        "implementation_notes": dp.implementation_notes,
        "change_log": dp.change_log,
    }


def render_cookbook(dp: DataProduct, theme: str = "light") -> str:
    """Return the complete Cookbook HTML string for the given DataProduct.

    ``theme`` selects the embedded column-ERD palette: ``light`` (default,
    matches the Cookbook page), ``navy`` or ``black``.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=False,
    )
    env.filters["highlight_sql"] = highlight_sql
    template = env.get_template("cookbook.html.j2")
    return template.render(**_build_context(dp, theme=theme))
