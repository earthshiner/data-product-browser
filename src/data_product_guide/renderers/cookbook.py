"""Renders the Data Product Cookbook HTML artefact.

All data is rendered server-side via Jinja2. The resulting file is fully
self-contained and requires no network access to display.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..models import DataProduct
from .erd import make_column_erd
from .jupyter import make_python_code, notebook_data_uri
from .sql_highlight import highlight_sql
from .svg import make_join_diagram

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _extract_table_names(sql: str, product_name: str) -> list[str]:
    """Return unique short table names referenced in the SQL."""
    pattern = re.compile(rf"{re.escape(product_name)}_\w+\.(\w+)", re.IGNORECASE)
    seen: list[str] = []
    for m in pattern.finditer(sql):
        name = m.group(1)
        if name not in seen:
            seen.append(name)
    return seen


def _build_context(dp: DataProduct) -> dict:
    """Transform the DataProduct into template-friendly dicts."""

    # Group columns by database.table for the Data Dictionary tab
    cols_by_table: dict[str, list] = defaultdict(list)
    for col in dp.columns:
        key = f"{col.database_name}.{col.table_name}"
        cols_by_table[key].append(col)

    # Enrich each recipe with SQL, Jupyter, join diagram, and column ERD
    enriched_recipes = []
    for r in dp.recipes:
        tables_in_sql = _extract_table_names(r.sql_template, dp.product_name)
        enriched_recipes.append({
            "recipe": r,
            "sql_html": highlight_sql(r.sql_template),
            "join_diagram": make_join_diagram(tables_in_sql),
            "column_erd": make_column_erd(
                tables_in_sql,
                dp.columns,
                dp.relationships,
                dp.entities,
            ),
            "jupyter_code": make_python_code(r),
            "notebook_uri": notebook_data_uri(r, dp.product_name),
            "notebook_filename": f"{r.recipe_id}.ipynb",
        })

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
        "generated_at": dp.generated_at.strftime("%Y-%m-%d %H:%M UTC"),
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
        "naming_standards": dp.naming_standards,
        "implementation_notes": dp.implementation_notes,
        "change_log": dp.change_log,
    }


def render_cookbook(dp: DataProduct) -> str:
    """Return the complete Cookbook HTML string for the given DataProduct."""
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=False,
    )
    env.filters["highlight_sql"] = highlight_sql
    template = env.get_template("cookbook.html.j2")
    return template.render(**_build_context(dp))
