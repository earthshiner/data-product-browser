"""Smoke tests for models, renderers, SQL highlighter, and error handling.

These tests run without a Teradata connection by using a minimal fixture.
Run with:  uv run pytest
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest

from data_product_guide.models import (
    ColumnMetadata,
    DataLineage,
    DataProduct,
    EntityMetadata,
    GlossaryTerm,
    LineageGraphEdge,
    ModuleRegistryEntry,
    ProductMap,
    Recipe,
    TableRelationship,
)
from data_product_guide.renderers.sql_highlight import highlight_sql
from data_product_guide.renderers.svg import make_join_diagram


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

class TestLineageModels:
    def test_data_lineage_minimal(self):
        dl = DataLineage(
            lineage_id=1,
            target_table="fact_loan",
            job_name="load_fact_loan",
            source_database="MortgagePlatform_Staging",
            source_table="stg_loan",
            target_database="MortgagePlatform_Domain",
            transformation_type="FULL_LOAD",
        )
        assert dl.lineage_id == 1
        assert dl.is_active == 1
        assert dl.source_system is None

    def test_lineage_graph_edge(self):
        edge = LineageGraphEdge(
            src_object_name_fq="MortgagePlatform_Staging.stg_loan",
            src_container_name="MortgagePlatform_Staging",
            src_object_name="stg_loan",
            src_kind="Table",
            src_display_name="MortgagePlatform_Staging.stg_loan\n [Table]",
            edge_relationship="ETL_INPUT",
            transformation_type="FULL_LOAD",
            lineage_id=1,
            tgt_object_name_fq="load_fact_loan",
            tgt_container_name="",
            tgt_object_name="load_fact_loan",
            tgt_kind="Job",
            tgt_display_name="load_fact_loan\n [Job]",
        )
        assert edge.edge_relationship == "ETL_INPUT"
        assert edge.src_kind == "Table"

    def test_data_product_includes_lineage_fields(self):
        from datetime import datetime, timezone
        dp = DataProduct(
            product_name="X",
            generated_at=datetime.now(timezone.utc),
        )
        assert dp.data_lineage == []
        assert dp.lineage_graph == []


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
        # 3 table boxes + 2 legend colour-key boxes = 5 rects
        assert svg.count("<rect") == 5
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
        from data_product_guide.renderers.cookbook import render_cookbook
        dp = _minimal_product()
        html = render_cookbook(dp)
        assert "TestProduct" in html
        assert "QC-TEST-001" in html
        assert "Active Loan" in html
        assert "borrower_name" in html

    def test_ops_dashboard_renders(self):
        from data_product_guide.renderers.ops_dashboard import render_ops_dashboard
        dp = _minimal_product()
        html = render_ops_dashboard(dp)
        assert "TestProduct" in html
        assert "window.__DATA__" in html
        assert '"product_name": "TestProduct"' in html

    def test_ops_data_is_valid_json(self):
        import re
        from data_product_guide.renderers.ops_dashboard import render_ops_dashboard
        dp = _minimal_product()
        html = render_ops_dashboard(dp)
        match = re.search(r"window\.__DATA__\s*=\s*(\{.*?\});", html, re.DOTALL)
        assert match, "Could not find __DATA__ assignment"
        parsed = json.loads(match.group(1))
        assert parsed["product_name"] == "TestProduct"


# ---------------------------------------------------------------------------
# Exception / error-handling tests
# ---------------------------------------------------------------------------

class TestExceptions:
    def test_access_denied_message(self):
        from data_product_guide.exceptions import AccessDeniedError
        err = AccessDeniedError(
            "MortgagePlatform_Semantic.data_product_map", "pd185014", "MortgagePlatform"
        )
        msg = str(err)
        assert "No SELECT access" in msg
        assert "GRANT SELECT ON MortgagePlatform_Semantic TO pd185014" in msg
        assert "GRANT SELECT ON MortgagePlatform_Memory TO pd185014" in msg
        assert "GRANT SELECT ON MortgagePlatform_Observability TO pd185014" in msg

    def test_object_not_found_message(self):
        from data_product_guide.exceptions import ObjectNotFoundError
        err = ObjectNotFoundError("MortgagePlatform_Semantic.data_product_map", "MortgagePlatform")
        msg = str(err)
        assert "does not exist" in msg
        assert "MortgagePlatform_Semantic.data_product_map" in msg

    def test_login_error_message(self):
        from data_product_guide.exceptions import LoginError
        msg = str(LoginError())
        assert "Login failed" in msg
        assert "store-password" in msg

    def test_snapshot_not_found_message(self):
        from data_product_guide.exceptions import SnapshotNotFoundError
        msg = str(SnapshotNotFoundError("./snapshots/test.json"))
        assert "not found" in msg
        assert "dump" in msg

    def test_invalid_artefact_message(self):
        from data_product_guide.exceptions import InvalidArtefactError
        msg = str(InvalidArtefactError("badvalue"))
        assert "badvalue" in msg
        assert "all, cookbook, ops" in msg

    def test_parse_3523_returns_access_denied(self):
        from data_product_guide.exceptions import AccessDeniedError, parse_teradata_error

        class FakeOpError(Exception):
            pass
        FakeOpError.__module__ = "teradatasql"

        raw = FakeOpError(
            "[Error 3523] The user does not have SELECT access to "
            "'MortgagePlatform_Semantic.data_product_map'."
        )
        result = parse_teradata_error(raw, "MortgagePlatform", "pd185014", "tdhost")
        assert isinstance(result, AccessDeniedError)
        assert "MortgagePlatform_Semantic.data_product_map" in result.object_name

    def test_parse_3807_returns_object_not_found(self):
        from data_product_guide.exceptions import ObjectNotFoundError, parse_teradata_error

        class FakeOpError(Exception):
            pass
        FakeOpError.__module__ = "teradatasql"

        raw = FakeOpError("[Error 3807] Object 'MortgagePlatform_Semantic.foo' does not exist.")
        result = parse_teradata_error(raw, "MortgagePlatform", "pd185014", "tdhost")
        assert isinstance(result, ObjectNotFoundError)

    def test_parse_5315_includes_grant_instructions(self):
        from data_product_guide.exceptions import DataProductError, parse_teradata_error

        class FakeOpError(Exception):
            pass
        FakeOpError.__module__ = "teradatasql"

        raw = FakeOpError(
            "[Error 5315] An owner referenced by user does not have "
            "SELECT WITH GRANT OPTION access to DBC.TablesV.DataBaseName."
        )
        result = parse_teradata_error(
            raw, "MortgagePlatform", "pd185014", "tdhost",
            query_context="MortgagePlatform_Semantic.lineage_graph",
        )
        msg = str(result)
        assert "WITH GRANT OPTION" in msg
        assert "DBC.TablesV" in msg
        assert "DataBaseName" not in msg   # column name must be stripped
        assert "lineage_graph" in msg
        assert "GRANT SELECT ON DBC.TablesV TO <view_owner>" in msg

    def test_parse_5315_with_owner_uses_real_name(self):
        from data_product_guide.exceptions import parse_teradata_error

        class FakeOpError(Exception):
            pass
        FakeOpError.__module__ = "teradatasql"

        raw = FakeOpError(
            "[Error 5315] An owner referenced by user does not have "
            "SELECT WITH GRANT OPTION access to DBC.TablesV.DataBaseName."
        )
        result = parse_teradata_error(
            raw, "MortgagePlatform", "pd185014", "tdhost",
            query_context="MortgagePlatform_Semantic.lineage_graph",
            view_owner="MPC_Server_User",
        )
        msg = str(result)
        assert "GRANT SELECT ON DBC.TablesV TO MPC_Server_User WITH GRANT OPTION" in msg
        assert "<view_owner>" not in msg
        assert "View owner: MPC_Server_User" in msg

    def test_parse_unknown_error_includes_query_context(self):
        from data_product_guide.exceptions import parse_teradata_error

        class FakeOpError(Exception):
            pass
        FakeOpError.__module__ = "teradatasql"

        raw = FakeOpError("[Error 9999] Something unexpected.")
        result = parse_teradata_error(
            raw, "MortgagePlatform", "pd185014", "tdhost",
            query_context="MortgagePlatform_Semantic.some_table",
        )
        msg = str(result)
        assert "MortgagePlatform_Semantic.some_table" in msg
