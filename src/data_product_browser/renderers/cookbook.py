"""Renders the Data Product Cookbook HTML artefact.

All data is rendered server-side via Jinja2. The resulting file is fully
self-contained and requires no network access to display.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..models import DataProduct, EntityMetadata
from .erd import make_column_erd
from .jupyter import make_python_code, notebook_data_uri
from .sql_highlight import highlight_sql
from .svg import make_join_diagram

_TEMPLATES_DIR = Path(__file__).parent / "templates"

# Any '<db>.<table>' reference in SQL. Teradata identifiers are
# alphanumeric + underscore + $; no dots allowed inside a name.
_QUALIFIED_REF = re.compile(r"\b([A-Za-z_][A-Za-z0-9_$]*)\.([A-Za-z_][A-Za-z0-9_$]*)\b")


def _extract_sql_tables(sql: str) -> list[str]:
    """Return every qualified ``<db>.<table>`` short name in the SQL.

    Used for the Join Diagram so it can still render even when a recipe
    references a derived view that isn't catalogued in ``entity_metadata``.
    Order of first occurrence preserved; duplicates removed.
    """
    seen: list[str] = []
    seen_upper: set[str] = set()
    for m in _QUALIFIED_REF.finditer(sql):
        table = m.group(2)
        up = table.upper()
        if up not in seen_upper:
            seen_upper.add(up)
            seen.append(table)
    return seen


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
        all_tables = _extract_sql_tables(r.sql_template)
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
                    dp.relationships,
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
