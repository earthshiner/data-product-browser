"""Dev-only preview harness: serve the browser with in-memory sample data.

Not part of the package — lets us eyeball the UI without a Teradata connection.
Run via the 'browser-preview' launch config.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import uvicorn

from data_product_browser.models import (
    ChangeEvent,
    ColumnMetadata,
    DataProduct,
    DesignDecision,
    EntityMetadata,
    GlossaryTerm,
    LineageRun,
    QualityMetric,
    TableRelationship,
)
from data_product_browser.server.app import create_app

NOW = datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc)


def _sample() -> DataProduct:
    return DataProduct(
        product_name="MortgagePlatform",
        generated_dts=NOW,
        entities=[
            EntityMetadata(
                entity_metadata_key=1,
                module_name="Domain",
                entity_name="Loan",
                database_name="MortgagePlatform_Domain",
                table_name="loan",
                entity_description="A mortgage loan account.",
                entity_category="Fact",
                natural_key_column="loan_number",
                record_count_approx=1_250_000,
            ),
            EntityMetadata(
                entity_metadata_key=2,
                module_name="Domain",
                entity_name="Borrower",
                database_name="MortgagePlatform_Domain",
                table_name="borrower",
                entity_description="A person responsible for a loan.",
                entity_category="Dimension",
                natural_key_column="borrower_id",
                record_count_approx=900_000,
            ),
        ],
        columns=[
            ColumnMetadata(
                column_metadata_key=1,
                database_name="MortgagePlatform_Domain",
                table_name="loan",
                column_name="loan_id",
                data_type="BIGINT",
                is_required=1,
            ),
            ColumnMetadata(
                column_metadata_key=2,
                database_name="MortgagePlatform_Domain",
                table_name="loan",
                column_name="borrower_id",
                data_type="BIGINT",
                is_required=1,
            ),
            ColumnMetadata(
                column_metadata_key=3,
                database_name="MortgagePlatform_Domain",
                table_name="loan",
                column_name="principal_amount",
                data_type="DECIMAL(15,2)",
                business_description="Original principal.",
                sample_values="350000.00",
            ),
            ColumnMetadata(
                column_metadata_key=4,
                database_name="MortgagePlatform_Domain",
                table_name="borrower",
                column_name="borrower_id",
                data_type="BIGINT",
                is_required=1,
            ),
            ColumnMetadata(
                column_metadata_key=5,
                database_name="MortgagePlatform_Domain",
                table_name="borrower",
                column_name="tax_file_number",
                data_type="CHAR(9)",
                is_pii=1,
                is_sensitive=1,
                business_description="Borrower TFN.",
            ),
        ],
        relationships=[
            TableRelationship(
                relationship_key=1,
                from_database="MortgagePlatform_Domain",
                from_table="loan",
                from_column="borrower_id",
                to_database="MortgagePlatform_Domain",
                to_table="borrower",
                to_column="borrower_id",
                relationship_type="FK",
                join_type="INNER",
                cardinality="N:1",
                is_mandatory=1,
                relationship_desc="Each loan has one borrower.",
            ),
        ],
        glossary=[
            GlossaryTerm(
                glossary_key=1,
                term="Principal",
                term_category="Finance",
                definition="The amount borrowed, excluding interest.",
                business_context="Drives amortisation schedules.",
                related_table="loan",
                related_column="principal_amount",
                source_module="Domain",
                valid_from=NOW.date(),
            ),
        ],
        decisions=[
            DesignDecision(
                decision_key=1,
                decision_id="ADR-001",
                decision_title="Surrogate keys on all facts",
                decision_description="Use BIGINT surrogate keys.",
                rationale="Stable joins.",
                consequences="ETL must assign keys.",
                decision_status="ACCEPTED",
                decision_category="Modelling",
                source_module="Domain",
                affects_table="loan",
                valid_from=NOW.date(),
            ),
        ],
        quality_metrics=[
            QualityMetric(
                quality_metric_key=1,
                database_name="MortgagePlatform_Domain",
                table_name="loan",
                metric_name="null_rate(principal_amount)",
                metric_value=0.001,
                threshold_value=0.01,
                is_below_threshold=0,
                measured_dts=NOW - timedelta(hours=3),
            ),
            QualityMetric(
                quality_metric_key=2,
                database_name="MortgagePlatform_Domain",
                table_name="borrower",
                metric_name="completeness(tax_file_number)",
                metric_value=0.82,
                threshold_value=0.95,
                is_below_threshold=1,
                measured_dts=NOW - timedelta(hours=3),
            ),
        ],
        lineage_runs=[
            LineageRun(
                lineage_run_id=1,
                lineage_id=10,
                run_dts=NOW - timedelta(hours=2),
                run_status="SUCCESS",
                run_duration_ms=42000,
                records_read=1_250_000,
                records_written=1_250_000,
                records_rejected=0,
                job_name="load_loan",
            ),
            LineageRun(
                lineage_run_id=2,
                lineage_id=11,
                run_dts=NOW - timedelta(hours=26),
                run_status="FAILED",
                run_duration_ms=8000,
                records_read=900_000,
                records_written=0,
                records_rejected=900_000,
                job_name="load_borrower",
                error_message="2801: duplicate row",
            ),
        ],
        change_events=[
            ChangeEvent(
                change_event_key=1,
                event_dts=NOW - timedelta(hours=2),
                database_name="MortgagePlatform_Domain",
                table_name="loan",
                operation_type="INSERT",
                records_affected=12000,
                changed_by="etl_svc",
                is_successful=1,
            ),
            ChangeEvent(
                change_event_key=2,
                event_dts=NOW - timedelta(hours=26),
                database_name="MortgagePlatform_Domain",
                table_name="borrower",
                operation_type="MERGE",
                records_affected=0,
                changed_by="etl_svc",
                is_successful=0,
            ),
        ],
    )


class _StubService:
    def list_products(self):
        return ["MortgagePlatform"]

    def get(self, name, lookback_days=90, refresh=False):
        return _sample(), [
            "⚠  Skipped MortgagePlatform_Semantic.lineage_graph: missing DBC grant (demo)"
        ]


if __name__ == "__main__":
    uvicorn.run(create_app(_StubService()), host="127.0.0.1", port=8137, log_level="warning")
