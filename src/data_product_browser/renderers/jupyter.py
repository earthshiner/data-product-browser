"""Jupyter notebook artefact generator.

Produces both:
  - Python code block (for inline display in the cookbook HTML)
  - A downloadable .ipynb JSON (embedded as a base64 data URI)

Format follows the spec in cookbook-html-format.md and query-patterns.md:
  - teradatasql cursor pattern (not pd.read_sql) for bind parameter support
  - logmech='LDAP' in connection
  - run_query() helper in Cell 1
  - Bind parameters detected and documented
"""

from __future__ import annotations

import base64
import json
import re

from ..models import Recipe


_BIND_RE = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")


def _detect_params(sql: str) -> list[str]:
    """Return unique bind parameter names found in the SQL."""
    seen: list[str] = []
    for m in _BIND_RE.finditer(sql):
        name = m.group(1)
        if name not in seen:
            seen.append(name)
    return seen


_CONN_CELL = """\
import teradatasql
import pandas as pd

# ─── Connection ──────────────────────────────────────────────────────────────
# Replace placeholders with your environment values
conn = teradatasql.connect(
    host='<your_host>',
    user='<your_user>',
    password='<your_password>',
    logmech='LDAP',
)

def run_query(sql, params=None):
    \"\"\"Execute a Teradata SQL query and return a DataFrame.\"\"\"
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
    return pd.DataFrame(rows, columns=cols)
"""


def make_python_code(recipe: Recipe) -> str:
    """Return the Python source to display in the cookbook HTML code block."""
    sep = "─" * max(0, 72 - len(recipe.recipe_id) - len(recipe.recipe_title) - 4)
    header = (
        f"# ─── {recipe.recipe_id}: {recipe.recipe_title} {sep}\n"
        f"# Use case  : {recipe.use_case}\n"
        f"# Complexity: {recipe.complexity}  ·  Module: {recipe.source_module}\n"
    )
    if recipe.performance_notes:
        header += f"# Performance: {recipe.performance_notes}\n"

    params = _detect_params(recipe.sql_template)
    param_block = ""
    if params:
        lines = ["params = {\n"]
        for p in params:
            lines.append(f"    '{p}': '<value>',  # Replace with actual value\n")
        lines.append("}\n")
        param_block = "\n" + "".join(lines)

    run_call = "df = run_query(sql, params)" if params else "df = run_query(sql)"

    body = (
        f"\n{_CONN_CELL}\n\n"
        f"# ─── Query ──────────────────────────────────────────────────────────────────\n"
        f"sql = '''\n{recipe.sql_template.strip()}\n'''\n"
        f"{param_block}\n"
        f"{run_call}\n"
        f"df\n"
    )
    return header + body


def make_notebook(recipe: Recipe, product_name: str) -> dict:
    """Return a .ipynb-compatible dict for the recipe."""

    def md_cell(source: str) -> dict:
        return {
            "cell_type": "markdown",
            "metadata": {},
            "source": source.splitlines(keepends=True),
        }

    def code_cell(source: str) -> dict:
        return {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": source.splitlines(keepends=True),
        }

    params = _detect_params(recipe.sql_template)

    title_md = (
        f"# {recipe.recipe_title}\n\n"
        f"**Product:** {product_name}  \n"
        f"**Recipe ID:** `{recipe.recipe_id}`  \n"
        f"**Module:** {recipe.source_module}  \n"
        f"**Complexity:** {recipe.complexity}\n\n"
        f"---\n\n"
        f"**Business question:** {recipe.use_case}\n"
    )
    if recipe.recipe_description:
        title_md += f"\n**Context:** {recipe.recipe_description}\n"
    if recipe.performance_notes:
        title_md += f"\n> **Performance note:** {recipe.performance_notes}\n"

    query_lines = [
        f"# ─── {recipe.recipe_id}: {recipe.recipe_title}\n",
        f"# Source: {product_name}_Memory.Query_Cookbook\n\n",
        f"sql = '''\n{recipe.sql_template.strip()}\n'''\n",
    ]
    if params:
        query_lines.append("\nparams = {\n")
        for p in params:
            query_lines.append(f"    '{p}': '<value>',  # Replace with actual value\n")
        query_lines.append("}\n")
        query_lines.append("\ndf = run_query(sql, params)\n")
    else:
        query_lines.append("\ndf = run_query(sql)\n")
    query_lines.append("df\n")

    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.11.0"},
        },
        "cells": [
            md_cell(title_md),
            code_cell(_CONN_CELL),
            code_cell("".join(query_lines)),
        ],
    }


def notebook_data_uri(recipe: Recipe, product_name: str) -> str:
    """Return a base64 data URI for the .ipynb download link."""
    nb_json = json.dumps(make_notebook(recipe, product_name), indent=2)
    encoded = base64.b64encode(nb_json.encode("utf-8")).decode("ascii")
    return f"data:application/json;base64,{encoded}"
