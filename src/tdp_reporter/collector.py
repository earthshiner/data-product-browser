"""Extracts all metadata for one AI-Native Data Product from Teradata.

Each query targets the live Semantic, Memory, and Observability databases.
The 90-day window on Observability tables keeps result sets practical;
adjust via the ``lookback_days`` parameter if needed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

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

    with connection.cursor() as cur:
        # --- Semantic -------------------------------------------------------

        cur.execute(f"SELECT * FROM {sem}.data_product_map WHERE is_active = 1")
        modules = _rows(cur, ProductMap)

        cur.execute(f"SELECT * FROM {sem}.entity_metadata WHERE is_active = 1")
        entities = _rows(cur, EntityMetadata)

        cur.execute(f"SELECT * FROM {sem}.column_metadata WHERE is_active = 1")
        columns = _rows(cur, ColumnMetadata)

        cur.execute(f"SELECT * FROM {sem}.table_relationship WHERE is_active = 1")
        relationships = _rows(cur, TableRelationship)

        cur.execute(
            f"SELECT * FROM {sem}.naming_standard WHERE is_active = 1 ORDER BY standard_type"
        )
        naming_standards = _rows(cur, NamingStandard)

        # --- Memory ---------------------------------------------------------

        cur.execute(f"""
            SELECT * FROM {mem}.Query_Cookbook
            WHERE is_active = 1
              AND valid_to >= CURRENT_DATE
            ORDER BY recipe_id
        """)
        recipes = _rows(cur, Recipe)

        cur.execute(f"""
            SELECT * FROM {mem}.Business_Glossary
            WHERE is_active = 1
              AND valid_to >= CURRENT_DATE
            ORDER BY term_category, term
        """)
        glossary = _rows(cur, GlossaryTerm)

        cur.execute(f"""
            SELECT * FROM {mem}.Design_Decision
            WHERE is_current = 1
              AND valid_to >= CURRENT_DATE
            ORDER BY decision_category, decision_id
        """)
        decisions = _rows(cur, DesignDecision)

        cur.execute(f"""
            SELECT * FROM {mem}.Module_Registry
            WHERE is_current = 1
              AND valid_to >= CURRENT_DATE
            ORDER BY module_name
        """)
        module_registry = _rows(cur, ModuleRegistryEntry)

        cur.execute(f"""
            SELECT * FROM {mem}.Implementation_Note
            WHERE is_active = 1
              AND valid_to >= CURRENT_DATE
            ORDER BY severity, note_id
        """)
        implementation_notes = _rows(cur, ImplementationNote)

        cur.execute(f"""
            SELECT * FROM {mem}.Change_Log
            ORDER BY created_timestamp DESC
        """)
        change_log = _rows(cur, ChangeLogEntry)

        # --- Observability (rolling window) ---------------------------------

        cur.execute(f"""
            SELECT * FROM {obs}.data_quality_metric
            WHERE measured_at >= CURRENT_TIMESTAMP - INTERVAL '{lookback_days}' DAY
            ORDER BY measured_at DESC
        """)
        quality_metrics = _rows(cur, QualityMetric)

        cur.execute(f"""
            SELECT * FROM {obs}.lineage_run
            WHERE run_dts >= CURRENT_TIMESTAMP - INTERVAL '{lookback_days}' DAY
            ORDER BY run_dts DESC
        """)
        lineage_runs = _rows(cur, LineageRun)

        cur.execute(f"""
            SELECT * FROM {obs}.agent_outcome
            WHERE outcome_dts >= CURRENT_TIMESTAMP - INTERVAL '{lookback_days}' DAY
            ORDER BY outcome_dts DESC
        """)
        agent_outcomes = _rows(cur, AgentOutcome)

        cur.execute(f"""
            SELECT * FROM {obs}.change_event
            WHERE event_dts >= CURRENT_TIMESTAMP - INTERVAL '{lookback_days}' DAY
            ORDER BY event_dts DESC
        """)
        change_events = _rows(cur, ChangeEvent)

        cur.execute(f"""
            SELECT * FROM {obs}.data_lineage
            WHERE is_active = 1
            ORDER BY lineage_id
        """)
        data_lineage = _rows(cur, DataLineage)

        # lineage_graph is a Semantic view over Observability.data_lineage.
        # It expands each lineage row into two directed edges (ETL_INPUT + ETL_OUTPUT),
        # enabling graph traversal without joining the underlying table.
        cur.execute(f"""
            SELECT * FROM {sem}.lineage_graph
            ORDER BY lineage_id, edge_relationship
        """)
        lineage_graph = _rows(cur, LineageGraphEdge)

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
