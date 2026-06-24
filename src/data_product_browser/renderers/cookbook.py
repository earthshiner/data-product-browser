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


def _extract_table_names(sql: str, entities: list[EntityMetadata]) -> list[str]:
    """Return unique short table names from the SQL that match catalogued entities.

    Resolves every ``<db>.<table>`` reference in the SQL against the product's
    ``entity_metadata`` rows (case-insensitive on both parts). Bare ``<table>``
    references with no database qualifier are also matched if the table name
    is unique across the catalogue. Order of first occurrence is preserved.
    """
    catalogued_pairs = {
        (e.database_name.upper(), e.table_name.upper()): e.table_name for e in entities
    }
    catalogued_short: dict[str, str] = {}
    short_counts: dict[str, int] = {}
    for e in entities:
        up = e.table_name.upper()
        catalogued_short[up] = e.table_name
        short_counts[up] = short_counts.get(up, 0) + 1

    seen: list[str] = []
    matched_upper: set[str] = set()

    def _add(short_name: str) -> None:
        up = short_name.upper()
        if up in matched_upper:
            return
        matched_upper.add(up)
        seen.append(short_name)

    # Pass 1: qualified <db>.<table> references — only those that map to a
    # catalogued entity row count.
    for m in _QUALIFIED_REF.finditer(sql):
        db, table = m.group(1).upper(), m.group(2).upper()
        canonical = catalogued_pairs.get((db, table))
        if canonical:
            _add(canonical)

    # Pass 2: bare table tokens. Only safe to claim when the short name is
    # unique across the catalogue (otherwise we'd guess the wrong database).
    bare = re.compile(r"\b([A-Za-z_][A-Za-z0-9_$]*)\b")
    for m in bare.finditer(sql):
        token = m.group(1).upper()
        if short_counts.get(token) == 1:
            _add(catalogued_short[token])

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
        tables_in_sql = _extract_table_names(r.sql_template, dp.entities)
        # Filter relationships to only those between tables in this recipe
        recipe_tables_upper = {t.upper() for t in tables_in_sql}
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
                    tables_in_sql,
                    relationships=recipe_rels,
                    entities=dp.entities,
                ),
                "column_erd": make_column_erd(
                    tables_in_sql,
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
