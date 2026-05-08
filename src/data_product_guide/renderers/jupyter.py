"""Jupyter notebook artefact generator.

Produces both:
  - Python code block (for inline display in the cookbook HTML)
  - A downloadable .ipynb JSON (embedded as a base64 data URI)
"""

from __future__ import annotations

import base64
import html
import json

from ..models import Recipe


_CONN_BOILERPLATE = """\
import pandas as pd
import teradatasql

# --- Connection (replace placeholders with your environment values) ---
conn = teradatasql.connect(
    host='<your_teradata_host>',
    user='<your_username>',
    password='<your_password>',
)
"""


def make_python_code(recipe: Recipe) -> str:
    """Return the Python source to display in the cookbook HTML code block."""
    bar = "=" * (60 - len(recipe.recipe_id) - 2)
    header = (
        f"# === {recipe.recipe_title} ({recipe.recipe_id}) {bar}\n"
        f"# Use case  : {recipe.use_case}\n"
        f"# Complexity: {recipe.complexity}  ·  Module: {recipe.source_module}\n"
    )
    if recipe.performance_notes:
        header += f"# Performance: {recipe.performance_notes}\n"

    sql_block = (
        f"\n{_CONN_BOILERPLATE}\n"
        f"# --- SQL ---\n"
        f"sql = '''\n{recipe.sql_template.strip()}\n'''\n\n"
        f"df = pd.read_sql(sql, conn)\n"
        f"df\n"
    )
    return header + sql_block


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

    conn_code = (
        "import pandas as pd\n"
        "import teradatasql\n"
        "\n"
        "# Replace placeholders with your environment values\n"
        "conn = teradatasql.connect(\n"
        "    host='<your_teradata_host>',\n"
        "    user='<your_username>',\n"
        "    password='<your_password>',\n"
        ")\n"
    )

    sql_code = (
        f"sql = '''\n{recipe.sql_template.strip()}\n'''\n"
        "\n"
        "df = pd.read_sql(sql, conn)\n"
        "df\n"
    )

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
            code_cell(conn_code),
            code_cell(sql_code),
        ],
    }


def notebook_data_uri(recipe: Recipe, product_name: str) -> str:
    """Return a base64 data URI for the .ipynb download link."""
    nb_json = json.dumps(make_notebook(recipe, product_name), indent=2)
    encoded = base64.b64encode(nb_json.encode("utf-8")).decode("ascii")
    return f"data:application/json;base64,{encoded}"
