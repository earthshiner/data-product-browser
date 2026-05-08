"""Smoke tests for models, renderers, and SQL highlighter.

These tests run without a Teradata connection by using a minimal fixture.
Run with:  uv run pytest
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest

from tdp_reporter.models import (
    ColumnMetadata,
    DataProduct,
    EntityMetadata,
    GlossaryTerm,
    ModuleRegistryEntry,
    ProductMap,
    Recipe,
    TableRelationship,
)
from tdp_reporter.renderers.sql_highlight import highlight_sql
from tdp_reporter.renderers.svg import make_join_diagram


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _minimal_product() -> DataProduct:
    today = date.today()
    return DataProduct(
        product_name="TestProduct",
        generated_at=datetime.now(timezone.utc),
        modules=[
            ProductMap(
                map_key=1,
                module_name="SEMANTIC",
                database_name="TestProduct_Semantic",
                module_purpose="Metadata layer",
                is_active=1,
            )
        ],
        entities=[
            EntityMetadata(
                entity_metadata_key=1,
                module_name="DOMAIN",
                entity_name="Loan",
                database_name="TestProduct_Domain",
                table_name="loan",
                natural_key_column="loan_id",
                entity_description="Core loan entity",
                is_active=1,
            )
        ],
        columns=[
            ColumnMetadata(
                column_metadata_key=1,
                database_name="TestProduct_Domain",
                table_name="loan",
                column_name="loan_id",
                business_description="Unique loan identifier",
                data_type="BIGINT",
                is_pii=0,
                is_sensitive=0,
                is_active=1,
            ),
            ColumnMetadata(
                column_metadata_key=2,
                database_name="TestProduct_Domain",
                table_name="loan",
                column_name="borrower_name",
                business_description="Full legal name of borrower",
                data_type="VARCHAR(200)",
                is_pii=1,
                is_sensitive=1,
                is_active=1,
            ),
        ],
        recipes=[
            Recipe(
                recipe_key=1,
                recipe_id="QC-TEST-001",
                recipe_title="Count active loans",
                recipe_description="Returns total active loans grouped by product type.",
                use_case="How many active loans are there by product type?",
                target_module="DOMAIN",
                sql_template=(
                    "SELECT product_type, COUNT(*) AS loan_count\n"
                    "FROM TestProduct_Domain.loan\n"
                    "WHERE loan_status = 'ACTIVE'\n"
                    "GROUP BY 1\n"
                    "ORDER BY 2 DESC;"
                ),
                complexity="SIMPLE",
                source_module="DOMAIN",
                valid_from=today,
                valid_to=date(9999, 12, 31),
            )
        ],
        glossary=[
            GlossaryTerm(
                glossary_key=1,
                term="Active Loan",
                term_category="LENDING",
                definition="A loan that is currently in repayment and not in arrears.",
                business_context="Regulatory reporting threshold: arrears > 90 days.",
                source_module="DOMAIN",
                valid_from=today,
                valid_to=date(9999, 12, 31),
            )
        ],
        module_registry=[
            ModuleRegistryEntry(
                module_registry_key=1,
                module_name="DOMAIN",
                database_name="TestProduct_Domain",
                deployment_status="DEPLOYED",
                module_version="1.0.0",
                module_purpose="Authoritative loan entity store",
                version_date=today,
                valid_from=today,
            )
        ],
        relationships=[
            TableRelationship(
                relationship_key=1,
                from_database="TestProduct_Domain",
                from_table="loan",
                from_column="borrower_id",
                to_database="TestProduct_Domain",
                to_table="borrower",
                to_column="borrower_id",
                relationship_type="FK",
                join_type="LEFT",
                cardinality="N:1",
                is_active=1,
            )
        ],
    )


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestDataProductModel:
    def test_round_trip_json(self):
        dp = _minimal_product()
        serialised = dp.model_dump_json()
        restored = DataProduct.model_validate_json(serialised)
        assert restored.product_name == dp.product_name
        assert len(restored.recipes) == len(dp.recipes)

    def test_pii_column_flagged(self):
        dp = _minimal_product()
        pii_cols = [c for c in dp.columns if c.is_pii]
        assert len(pii_cols) == 1
        assert pii_cols[0].column_name == "borrower_name"


# ---------------------------------------------------------------------------
# SQL highlighter tests
# ---------------------------------------------------------------------------

class TestSqlHighlight:
    def test_keywords_wrapped(self):
        out = highlight_sql("SELECT * FROM foo")
        assert 'class="sql-keyword"' in out
        assert "SELECT" in out

    def test_string_wrapped(self):
        out = highlight_sql("WHERE status = 'ACTIVE'")
        assert 'class="sql-string"' in out

    def test_number_wrapped(self):
        out = highlight_sql("WHERE loan_id = 42")
        assert 'class="sql-number"' in out

    def test_comment_wrapped(self):
        out = highlight_sql("-- this is a comment")
        assert 'class="sql-comment"' in out

    def test_html_entities_escaped(self):
        out = highlight_sql("WHERE a < b AND c > d")
        assert "&lt;" in out
        assert "&gt;" in out


# ---------------------------------------------------------------------------
# SVG diagram tests
# ---------------------------------------------------------------------------

class TestSvgDiagram:
    def test_empty_input(self):
        assert make_join_diagram([]) == ""

    def test_single_table(self):
        svg = make_join_diagram(["loan"])
        assert "<svg" in svg
        assert "loan" in svg

    def test_multiple_tables(self):
        svg = make_join_diagram(["loan", "borrower", "product"])
        assert svg.count("<rect") == 3
        assert "borrower" in svg

    def test_xss_escaped(self):
        svg = make_join_diagram(["<script>alert(1)</script>"])
        assert "<script>" not in svg
        assert "&lt;script&gt;" in svg


# ---------------------------------------------------------------------------
# Renderer smoke tests
# ---------------------------------------------------------------------------

class TestRenderers:
    def test_cookbook_renders(self):
        from tdp_reporter.renderers.cookbook import render_cookbook
        dp = _minimal_product()
        html = render_cookbook(dp)
        assert "TestProduct" in html
        assert "QC-TEST-001" in html
        assert "Active Loan" in html
        assert "borrower_name" in html

    def test_ops_dashboard_renders(self):
        from tdp_reporter.renderers.ops_dashboard import render_ops_dashboard
        dp = _minimal_product()
        html = render_ops_dashboard(dp)
        assert "TestProduct" in html
        assert "window.__DATA__" in html
        assert '"product_name": "TestProduct"' in html

    def test_ops_data_is_valid_json(self):
        import re
        from tdp_reporter.renderers.ops_dashboard import render_ops_dashboard
        dp = _minimal_product()
        html = render_ops_dashboard(dp)
        match = re.search(r"window\.__DATA__\s*=\s*(\{.*?\});", html, re.DOTALL)
        assert match, "Could not find __DATA__ assignment"
        parsed = json.loads(match.group(1))
        assert parsed["product_name"] == "TestProduct"
