"""Smoke tests for the realigned models, SQL highlighter, SVG, and exceptions.

These run without a Teradata connection using a minimal fixture shaped like the
deployed AI-Native Data Product standard.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from data_product_browser.models import (
    ColumnMetadata,
    DataLineage,
    DataProduct,
    EntityMetadata,
    GlossaryTerm,
    ProductMap,
    QualityMetric,
    Recipe,
    RegistryEntry,
    TableRelationship,
    TrustReport,
)
from data_product_browser.renderers.sql_highlight import highlight_sql
from data_product_browser.renderers.svg import make_join_diagram


def _minimal_product() -> DataProduct:
    today = date.today()
    return DataProduct(
        product_name="CallCentre Data Product",
        generated_dts=datetime.now(timezone.utc),
        registry=RegistryEntry(
            product_name="CallCentre Data Product",
            product_version="1.0.0",
            product_status="ACTIVE",
            semantic_view_database="CallCentre_SEM_BUS_V",
        ),
        trust=TrustReport(
            trust_status="TRUSTED", agent_use_allowed=1, data_product_trust_score=98.5
        ),
        modules=[
            ProductMap(
                module_id=1,
                module_name="Domain",
                database_name="CallCentre_DOM_STD_T",
                module_purpose="Core business entities",
            )
        ],
        entities=[
            EntityMetadata(
                entity_metadata_id=1,
                module_name="Domain",
                entity_name="Call",
                database_name="CallCentre_DOM_STD_V",
                table_name="Call_Current",
                natural_key_column="call_id",
                entity_description="A call handled by the centre",
            )
        ],
        columns=[
            ColumnMetadata(
                column_metadata_id=1,
                database_name="CallCentre_DOM_STD_V",
                table_name="Call_Current",
                column_name="call_id",
                data_type="BIGINT",
                is_pii=0,
            ),
            ColumnMetadata(
                column_metadata_id=2,
                database_name="CallCentre_DOM_STD_V",
                table_name="Call_Current",
                column_name="caller_name",
                data_type="VARCHAR(200)",
                data_classification="PII",
                is_pii=1,
                is_sensitive=1,
            ),
        ],
        relationships=[
            TableRelationship(
                relationship_id=1,
                source_database="CallCentre_DOM_STD_V",
                source_table="Call_Current",
                source_column="agent_id",
                target_database="CallCentre_DOM_STD_V",
                target_table="Agent_Current",
                target_column="agent_id",
                relationship_type="FK",
                cardinality="N:1",
                relationship_meaning="Each call is handled by one agent.",
            )
        ],
        recipes=[
            Recipe(
                recipe_key=1,
                recipe_id="QC-001",
                recipe_title="Calls per agent",
                recipe_description="Counts calls grouped by agent.",
                use_case="How many calls did each agent handle?",
                target_module="Domain",
                sql_template="SELECT agent_id, COUNT(*) FROM CallCentre_DOM_STD_V.Call_Current GROUP BY 1;",
                complexity="SIMPLE",
                source_module="Domain",
                valid_from=today,
            )
        ],
        glossary=[
            GlossaryTerm(
                glossary_key=1,
                term="Handle Time",
                term_category="Operations",
                definition="Total time an agent spends on a call.",
                related_table="Call_Current",
                source_module="Domain",
                valid_from=today,
            )
        ],
        quality_metrics=[
            QualityMetric(
                quality_metric_id=1,
                database_name="CallCentre_DOM_STD_V",
                table_name="Call_Current",
                metric_name="completeness(call_id)",
                metric_value=1.0,
                quality_threshold=0.99,
                is_threshold_met=1,
                measured_dts=datetime.now(timezone.utc),
            )
        ],
        data_lineage=[
            DataLineage(
                lineage_id=1,
                target_table="Call_H",
                target_database="CallCentre_DOM_STD_T",
                job_name="load_call",
                run_status="SUCCESS",
                records_read=95944,
                records_written=95944,
            )
        ],
    )


class TestDataProductModel:
    def test_round_trip_json(self):
        dp = _minimal_product()
        restored = DataProduct.model_validate_json(dp.model_dump_json())
        assert restored.product_name == dp.product_name
        assert len(restored.recipes) == len(dp.recipes)
        assert restored.trust.agent_use_allowed == 1
        assert restored.registry.semantic_view_database == "CallCentre_SEM_BUS_V"

    def test_pii_column_flagged(self):
        dp = _minimal_product()
        pii_cols = [c for c in dp.columns if c.is_pii]
        assert len(pii_cols) == 1
        assert pii_cols[0].column_name == "caller_name"

    def test_extra_columns_ignored(self):
        # Deployment may carry columns the model doesn't know; they must not error.
        entity = EntityMetadata(
            entity_metadata_id=9,
            module_name="Domain",
            entity_name="X",
            database_name="db",
            table_name="t",
            some_future_column="ignored",
        )
        assert entity.entity_name == "X"

    def test_relationship_uses_source_target(self):
        dp = _minimal_product()
        rel = dp.relationships[0]
        assert rel.source_table == "Call_Current"
        assert rel.target_table == "Agent_Current"


class TestSqlHighlight:
    def test_keywords_wrapped(self):
        out = highlight_sql("SELECT * FROM foo")
        assert 'class="sql-keyword"' in out

    def test_html_entities_escaped(self):
        out = highlight_sql("WHERE a < b AND c > d")
        assert "&lt;" in out and "&gt;" in out


class TestSvgDiagram:
    def test_empty_input(self):
        assert make_join_diagram([]) == ""

    def test_xss_escaped(self):
        svg = make_join_diagram(["<script>alert(1)</script>"])
        assert "<script>" not in svg
        assert "&lt;script&gt;" in svg


class TestRenderers:
    def test_cookbook_renders(self):
        from data_product_browser.renderers.cookbook import render_cookbook

        html = render_cookbook(_minimal_product())
        assert "CallCentre Data Product" in html
        assert "QC-001" in html
        assert "Handle Time" in html  # glossary term
        assert "Agent_Current" in html  # relationship target

    def test_ops_dashboard_renders(self):
        from data_product_browser.renderers.ops_dashboard import render_ops_dashboard

        html = render_ops_dashboard(_minimal_product())
        assert "window.__DATA__" in html
        assert '"product_name": "CallCentre Data Product"' in html

    def test_ops_data_is_valid_json(self):
        import json
        import re

        from data_product_browser.renderers.ops_dashboard import render_ops_dashboard

        html = render_ops_dashboard(_minimal_product())
        match = re.search(r"window\.__DATA__\s*=\s*(\{.*?\});", html, re.DOTALL)
        assert match, "Could not find __DATA__ assignment"
        parsed = json.loads(match.group(1))
        assert parsed["product_name"] == "CallCentre Data Product"


class TestExceptions:
    def test_login_error_message(self):
        from data_product_browser.exceptions import LoginError

        msg = str(LoginError())
        assert "Login failed" in msg

    def test_invalid_artefact_message(self):
        from data_product_browser.exceptions import InvalidArtefactError

        msg = str(InvalidArtefactError("badvalue"))
        assert "badvalue" in msg
