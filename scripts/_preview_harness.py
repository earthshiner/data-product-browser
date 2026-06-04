"""Dev-only preview harness: serve the browser with in-memory sample data.

Not part of the package — lets us eyeball the UI without a Teradata connection.
If TDP_SNAPSHOT points at a DataProduct JSON file (e.g. produced by `dump`),
that real snapshot is served instead of the built-in sample.
Run via the 'browser-preview' launch config.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import uvicorn

from data_product_browser.models import (
    ChangeEvent,
    ColumnMetadata,
    DataLineage,
    DataProduct,
    DesignDecision,
    EntityMetadata,
    GlossaryTerm,
    ProductMap,
    QualityMetric,
    RegistryEntry,
    TableRelationship,
    TrustReport,
)
from data_product_browser.server.app import create_app

NOW = datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc)
SEM = "CallCentre_SEM_BUS_V"
DOM = "CallCentre_DOM_STD_V"


def _sample() -> DataProduct:
    return DataProduct(
        product_name="CallCentre Data Product",
        generated_dts=NOW,
        registry=RegistryEntry(
            product_name="CallCentre Data Product",
            product_version="1.2.0",
            product_status="ACTIVE",
            semantic_view_database=SEM,
            approved_entrypoint="CallCentre_DOM_STD_V.Call_Current",
        ),
        trust=TrustReport(
            trust_status="TRUSTED",
            agent_use_allowed=1,
            total_checks=42,
            passed_count=40,
            failed_count=2,
            critical_failure_count=0,
            data_product_trust_score=95.2,
            performance_readiness_score=88.0,
            operational_readiness_score=91.5,
        ),
        modules=[
            ProductMap(
                module_id=1,
                module_name="Domain",
                database_name="CallCentre_DOM_STD_T",
                module_purpose="Core call centre business entities.",
            ),
        ],
        entities=[
            EntityMetadata(
                entity_metadata_id=1,
                module_name="Domain",
                entity_name="Call",
                database_name=DOM,
                table_name="Call_Current",
                entity_description="A call handled by the centre.",
                natural_key_column="call_id",
                temporal_pattern="CURRENT_VIEW",
            ),
            EntityMetadata(
                entity_metadata_id=2,
                module_name="Domain",
                entity_name="Agent",
                database_name=DOM,
                table_name="Agent_Current",
                entity_description="A call centre agent.",
                natural_key_column="agent_id",
            ),
        ],
        columns=[
            ColumnMetadata(
                column_metadata_id=1,
                database_name=DOM,
                table_name="Call_Current",
                column_name="call_id",
                data_type="BIGINT",
                is_required=1,
                business_description="Surrogate call key.",
            ),
            ColumnMetadata(
                column_metadata_id=2,
                database_name=DOM,
                table_name="Call_Current",
                column_name="agent_id",
                data_type="BIGINT",
                is_required=1,
                business_description="Handling agent.",
            ),
            ColumnMetadata(
                column_metadata_id=3,
                database_name=DOM,
                table_name="Agent_Current",
                column_name="agent_id",
                data_type="BIGINT",
                is_required=1,
            ),
            ColumnMetadata(
                column_metadata_id=4,
                database_name=DOM,
                table_name="Agent_Current",
                column_name="agent_name",
                data_type="VARCHAR(120)",
                is_pii=1,
                is_sensitive=1,
                data_classification="PII",
                business_description="Agent full name.",
            ),
        ],
        relationships=[
            TableRelationship(
                relationship_id=1,
                source_database=DOM,
                source_table="Call_Current",
                source_column="agent_id",
                target_database=DOM,
                target_table="Agent_Current",
                target_column="agent_id",
                relationship_type="FK",
                cardinality="N:1",
                is_mandatory=1,
                relationship_meaning="Each call is handled by one agent.",
            ),
        ],
        glossary=[
            GlossaryTerm(
                glossary_key=1,
                term="Handle Time",
                term_category="Operations",
                definition="Total time an agent spends on a call.",
                business_context="Key productivity KPI.",
                related_table="Call_Current",
                source_module="Domain",
                valid_from=NOW.date(),
            ),
        ],
        decisions=[
            DesignDecision(
                decision_key=1,
                decision_id="ADR-001",
                decision_title="TIME WITH TIME ZONE for start_ts",
                decision_description="Store call start with zone.",
                rationale="Multi-region centres.",
                consequences="ETL must localise.",
                decision_status="ACCEPTED",
                decision_category="Modelling",
                source_module="Domain",
                affects_table="Call_Current",
                valid_from=NOW.date(),
            ),
        ],
        quality_metrics=[
            QualityMetric(
                quality_metric_id=1,
                database_name=DOM,
                table_name="Call_Current",
                metric_name="completeness(call_id)",
                metric_value=1.0,
                quality_threshold=0.99,
                is_threshold_met=1,
                measured_dts=NOW - timedelta(hours=3),
            ),
            QualityMetric(
                quality_metric_id=2,
                database_name=DOM,
                table_name="Agent_Current",
                column_name="agent_name",
                metric_name="completeness",
                metric_value=0.82,
                quality_threshold=0.95,
                is_threshold_met=0,
                measured_dts=NOW - timedelta(hours=3),
            ),
        ],
        data_lineage=[
            DataLineage(
                lineage_id=1,
                target_database="CallCentre_DOM_STD_T",
                target_table="Call_H",
                job_name="load_call",
                run_status="SUCCESS",
                run_dts=NOW - timedelta(hours=2),
                records_read=95944,
                records_written=95944,
            ),
            DataLineage(
                lineage_id=2,
                target_database="CallCentre_DOM_STD_T",
                target_table="Agent_H",
                job_name="load_agent",
                run_status="FAILED",
                run_dts=NOW - timedelta(hours=26),
                records_read=12,
                records_written=0,
            ),
        ],
        change_events=[
            ChangeEvent(
                change_event_id=1,
                database_name="CallCentre_DOM_STD_T",
                table_name="Call_H",
                change_type="INSERT",
                change_dts=NOW - timedelta(hours=2),
                records_affected=1200,
                changed_by="etl_svc",
                change_source="batch",
            ),
        ],
    )


def _load() -> DataProduct:
    path = os.environ.get("TDP_SNAPSHOT")
    if path:
        return DataProduct.model_validate_json(open(path, encoding="utf-8").read())
    return _sample()


class _StubService:
    def __init__(self):
        self._dp = _load()

    def list_products(self):
        return [
            {
                "product_name": self._dp.product_name,
                "product_version": self._dp.registry.product_version if self._dp.registry else None,
                "product_status": "ACTIVE",
            }
        ]

    def get(self, name, lookback_days=90, refresh=False):
        return self._dp, ["⚠  Skipped CallCentre_OBS_STD_V.model_performance (demo warning)"]


if __name__ == "__main__":
    uvicorn.run(create_app(_StubService()), host="127.0.0.1", port=8137, log_level="warning")
