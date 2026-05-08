"""Extracts all metadata for one AI-Native Data Product from Teradata.

Each query targets the live Semantic, Memory, and Observability databases.
The 90-day window on Observability tables keeps result sets practical;
adjust via the ``lookback_days`` parameter if needed.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from .exceptions import parse_teradata_error
from .models import (
    AgentOutcome,
    ChangeEvent,
    ChangeLogEntry,
    ColumnMetadata,
    DataLineage,
    DataProduct,
    DesignDecision,
    EntityMetadata,
    GlossaryTerm,
    ImplementationNote,
    LineageGraphEdge,
    LineageRun,
    ModuleRegistryEntry,
    NamingStandard,
    ProductMap,
    QualityMetric,
    Recipe,
    TableRelationship,
)


def _rows(cursor: Any, model_class: type) -> list:
    cols = [d[0].lower() for d in cursor.description]
    return [model_class(**dict(zip(cols, row))) for row in cursor.fetchall()]


def _run(cursor: Any, sql: str, model_class: type, product_name: str, user: str, host: str) -> list:
    """Execute one query and return typed rows, converting DB errors to friendly exceptions."""
    try:
        cursor.execute(sql)
        return _rows(cursor, model_class)
    except Exception as exc:
        # Only re-wrap teradatasql errors; let unexpected exceptions propagate naturally
        if "teradatasql" in type(exc).__module__ or "OperationalError" in type(exc).__name__:
            raise parse_teradata_error(exc, product_name, user, host) from None
        raise


def collect(
    product_name: str,
    connection: Any,
    lookback_days: int = 90,
) -> DataProduct:
    """Query all modules and return a fully populated DataProduct.

    Args:
        product_name:  Prefix used for all module databases, e.g. ``MortgagePlatform``.
        connection:    Open teradatasql connection.
        lookback_days: How far back to fetch Observability data.
    """
    sem = f"{product_name}_Semantic"
    mem = f"{product_name}_Memory"
    obs = f"{product_name}_Observability"

    # Resolve user/host for error messages — best effort
    user = os.environ.get("TD_USER", "unknown_user")
    host = os.environ.get("TD_HOST", "unknown_host")

    def q(sql: str, model_class: type) -> list:
        return _run(cur, sql, model_class, product_name, user, host)

    with connection.cursor() as cur:

        # --- Semantic -------------------------------------------------------

        modules = q(
            f"SELECT * FROM {sem}.data_product_map WHERE is_active = 1",
            ProductMap,
        )
        entities = q(
            f"SELECT * FROM {sem}.entity_metadata WHERE is_active = 1",
            EntityMetadata,
        )
        columns = q(
            f"SELECT * FROM {sem}.column_metadata WHERE is_active = 1",
            ColumnMetadata,
        )
        relationships = q(
            f"SELECT * FROM {sem}.table_relationship WHERE is_active = 1",
            TableRelationship,
        )
        naming_standards = q(
            f"SELECT * FROM {sem}.naming_standard WHERE is_active = 1 ORDER BY standard_type",
            NamingStandard,
        )

        # --- Memory ---------------------------------------------------------

        recipes = q(
            f"""SELECT * FROM {mem}.Query_Cookbook
                WHERE is_active = 1 AND valid_to >= CURRENT_DATE
                ORDER BY recipe_id""",
            Recipe,
        )
        glossary = q(
            f"""SELECT * FROM {mem}.Business_Glossary
                WHERE is_active = 1 AND valid_to >= CURRENT_DATE
                ORDER BY term_category, term""",
            GlossaryTerm,
        )
        decisions = q(
            f"""SELECT * FROM {mem}.Design_Decision
                WHERE is_current = 1 AND valid_to >= CURRENT_DATE
                ORDER BY decision_category, decision_id""",
            DesignDecision,
        )
        module_registry = q(
            f"""SELECT * FROM {mem}.Module_Registry
                WHERE is_current = 1 AND valid_to >= CURRENT_DATE
                ORDER BY module_name""",
            ModuleRegistryEntry,
        )
        implementation_notes = q(
            f"""SELECT * FROM {mem}.Implementation_Note
                WHERE is_active = 1 AND valid_to >= CURRENT_DATE
                ORDER BY severity, note_id""",
            ImplementationNote,
        )
        change_log = q(
            f"SELECT * FROM {mem}.Change_Log ORDER BY created_timestamp DESC",
            ChangeLogEntry,
        )

        # --- Observability (rolling window) ---------------------------------

        quality_metrics = q(
            f"""SELECT * FROM {obs}.data_quality_metric
                WHERE measured_at >= CURRENT_TIMESTAMP - INTERVAL '{lookback_days}' DAY
                ORDER BY measured_at DESC""",
            QualityMetric,
        )
        lineage_runs = q(
            f"""SELECT * FROM {obs}.lineage_run
                WHERE run_dts >= CURRENT_TIMESTAMP - INTERVAL '{lookback_days}' DAY
                ORDER BY run_dts DESC""",
            LineageRun,
        )
        agent_outcomes = q(
            f"""SELECT * FROM {obs}.agent_outcome
                WHERE outcome_dts >= CURRENT_TIMESTAMP - INTERVAL '{lookback_days}' DAY
                ORDER BY outcome_dts DESC""",
            AgentOutcome,
        )
        change_events = q(
            f"""SELECT * FROM {obs}.change_event
                WHERE event_dts >= CURRENT_TIMESTAMP - INTERVAL '{lookback_days}' DAY
                ORDER BY event_dts DESC""",
            ChangeEvent,
        )
        data_lineage = q(
            f"SELECT * FROM {obs}.data_lineage WHERE is_active = 1 ORDER BY lineage_id",
            DataLineage,
        )

        # lineage_graph is a Semantic view over Observability.data_lineage.
        # It expands each lineage row into two directed edges (ETL_INPUT + ETL_OUTPUT),
        # enabling graph traversal without joining the underlying table.
        lineage_graph = q(
            f"SELECT * FROM {sem}.lineage_graph ORDER BY lineage_id, edge_relationship",
            LineageGraphEdge,
        )

    return DataProduct(
        product_name=product_name,
        generated_at=datetime.now(timezone.utc),
        modules=modules,
        entities=entities,
        columns=columns,
        relationships=relationships,
        naming_standards=naming_standards,
        recipes=recipes,
        glossary=glossary,
        decisions=decisions,
        module_registry=module_registry,
        implementation_notes=implementation_notes,
        change_log=change_log,
        quality_metrics=quality_metrics,
        lineage_runs=lineage_runs,
        agent_outcomes=agent_outcomes,
        change_events=change_events,
        data_lineage=data_lineage,
        lineage_graph=lineage_graph,
    )
