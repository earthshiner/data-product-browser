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
    AgentOutcome,
    ChangeEvent,
    ColumnMetadata,
    DataLineage,
    DataProduct,
    DesignDecision,
    EntityMetadata,
    GlossaryTerm,
    ProductMap,
    QualityMetric,
    Recipe,
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
            EntityMetadata(
                entity_metadata_id=3,
                module_name="Domain",
                entity_name="Call Score",
                database_name=DOM,
                table_name="Call_Score_Current",
                entity_description="Behavioural scores per call.",
                natural_key_column="call_id",
            ),
            EntityMetadata(
                entity_metadata_id=4,
                module_name="Prediction",
                entity_name="Call Features",
                database_name="CallCentre_PRE_STD_V",
                table_name="v_call_features_current",
                entity_description="Feature store for ML scoring.",
                natural_key_column="call_id",
            ),
            EntityMetadata(
                entity_metadata_id=5,
                module_name="Prediction",
                entity_name="Model Prediction",
                database_name="CallCentre_PRE_STD_V",
                table_name="model_prediction",
                entity_description="Stored model predictions.",
                natural_key_column="prediction_id",
            ),
            EntityMetadata(
                entity_metadata_id=6,
                module_name="Domain",
                entity_name="Call Summary",
                database_name=DOM,
                table_name="Call_Summary_Current",
                entity_description="Per-call summary text.",
            ),
            EntityMetadata(
                entity_metadata_id=7,
                module_name="Domain",
                entity_name="Call Topic",
                database_name=DOM,
                table_name="Call_Topic_Current",
                entity_description="Call topic classification.",
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
            TableRelationship(
                relationship_id=2,
                source_database=DOM,
                source_table="Call_Score_Current",
                source_column="call_id",
                target_database=DOM,
                target_table="Call_Current",
                target_column="call_id",
                relationship_type="FK",
                cardinality="1:1",
                relationship_meaning="Each score row belongs to one call.",
            ),
            TableRelationship(
                relationship_id=3,
                source_database="CallCentre_PRE_STD_V",
                source_table="v_call_features_current",
                source_column="call_id",
                target_database=DOM,
                target_table="Call_Current",
                target_column="call_id",
                relationship_type="FK",
                cardinality="1:1",
                relationship_meaning="Features derived per call.",
            ),
            TableRelationship(
                relationship_id=4,
                source_database="CallCentre_PRE_STD_V",
                source_table="model_prediction",
                source_column="call_id",
                target_database="CallCentre_PRE_STD_V",
                target_table="v_call_features_current",
                target_column="call_id",
                relationship_type="FK",
                cardinality="N:1",
                relationship_meaning="Predictions reference feature rows.",
            ),
        ],
        recipes=[
            Recipe(
                recipe_key=1,
                recipe_id="QC-001",
                recipe_title="Calls handled per agent",
                recipe_description="Counts calls grouped by agent, busiest first.",
                use_case="How many calls did each agent handle?",
                target_module="Domain",
                sql_template=(
                    "-- Calls per agent (current view)\n"
                    "SELECT a.agent_name, COUNT(*) AS call_count\n"
                    "FROM CallCentre_DOM_STD_V.Call_Current AS c\n"
                    "INNER JOIN CallCentre_DOM_STD_V.Agent_Current AS a\n"
                    "  ON c.agent_id = a.agent_id\n"
                    "GROUP BY a.agent_name\n"
                    "QUALIFY RANK() OVER (ORDER BY call_count DESC) <= 10\n"
                    "ORDER BY call_count DESC;"
                ),
                parameter_descriptions="None.",
                performance_notes="Collect stats on Call_Current.agent_id for the join.",
                complexity="SIMPLE",
                source_module="Domain",
                valid_from=NOW.date(),
            ),
            Recipe(
                recipe_key=2,
                recipe_id="QC-002",
                recipe_title="Low-scoring calls in last 7 days",
                recipe_description="Calls whose composite score fell below 0.5 recently.",
                use_case="Which recent calls need quality review?",
                target_module="Prediction",
                sql_template=(
                    "SELECT c.call_id, f.composite_score\n"
                    "FROM CallCentre_PRE_STD_V.v_call_features_current AS f\n"
                    "JOIN CallCentre_DOM_STD_V.Call_Current AS c ON c.call_id = f.call_id\n"
                    "WHERE f.composite_score < 0.5\n"
                    "  AND c.start_ts >= CURRENT_DATE - INTERVAL '7' DAY\n"
                    "ORDER BY f.composite_score ASC;"
                ),
                complexity="COMPLEX",
                source_module="Prediction",
                valid_from=NOW.date(),
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
            *[
                QualityMetric(
                    quality_metric_id=100 + i,
                    database_name=DOM,
                    table_name="Call_Current",
                    metric_name="freshness",
                    metric_value=0.9 + (i % 5) * 0.02,
                    quality_threshold=0.95,
                    is_threshold_met=0 if i % 4 == 0 else 1,
                    measured_dts=NOW - timedelta(days=i),
                )
                for i in range(1, 14)
            ],
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
                change_event_id=i,
                database_name="CallCentre_DOM_STD_T",
                table_name="Call_H" if i % 2 else "Agent_H",
                change_type="INSERT" if i % 3 else "MERGE",
                change_dts=NOW - timedelta(days=i // 2, hours=i),
                records_affected=1200 - i * 30,
                changed_by="etl_svc",
                change_source="batch",
            )
            for i in range(1, 13)
        ],
        agent_outcomes=[
            AgentOutcome(
                outcome_id=i,
                action_type=["query", "summarise", "classify"][i % 3],
                action_dts=NOW - timedelta(days=i // 3, hours=i),
                outcome_status="SUCCESS" if i % 4 else "FAILED",
                execution_time_ms=200 + i * 40,
                records_processed=i * 17,
            )
            for i in range(1, 16)
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
