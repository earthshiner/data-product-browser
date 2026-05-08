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


def _table_from_sql(sql: str) -> str:
    """Extract the first fully-qualified table reference from a SQL string."""
    import re
    m = re.search(r"FROM\s+([A-Za-z0-9_]+\.[A-Za-z0-9_]+)", sql, re.IGNORECASE)
    return m.group(1) if m else sql.strip().splitlines()[0][:60]


def _run(cursor: Any, sql: str, model_class: type, product_name: str, user: str, host: str) -> list:
    """Execute one query and return typed rows, converting DB errors to friendly exceptions."""
    try:
        cursor.execute(sql)
        return _rows(cursor, model_class)
    except Exception as exc:
        if "teradatasql" in type(exc).__module__ or "OperationalError" in type(exc).__name__:
            raise parse_teradata_error(
                exc, product_name, user, host,
                query_context=_table_from_sql(sql),
            ) from None
        raise


def _lookup_view_owner(cursor: Any, database: str, view_name: str) -> str | None:
    """Return the CreatorName for a view, or None if the lookup itself fails."""
    try:
        cursor.execute(
            f"SELECT CreatorName FROM DBC.TablesV "
            f"WHERE DatabaseName = '{database}' AND TableName = '{view_name}'"
        )
        row = cursor.fetchone()
        return str(row[0]).strip() if row else None
    except Exception:
        return None


def _run_optional(
    cursor: Any,
    sql: str,
    model_class: type,
    product_name: str,
    user: str,
    host: str,
    warn_label: str,
) -> tuple[list, str | None]:
    """Like _run, but on failure returns ([], warning_message) instead of raising.

    Used for queries that depend on DBC system-table grants outside the
    data product's control (e.g. lineage_graph → DBC.TablesV).
    """
    try:
        cursor.execute(sql)
        return _rows(cursor, model_class), None
    except Exception as exc:
        if "teradatasql" in type(exc).__module__ or "OperationalError" in type(exc).__name__:
            # For 5315 errors, resolve the view owner so the GRANT statement
            # uses the real name rather than a placeholder.
            view_owner = None
            if "[Error 5315]" in str(exc):
                parts = warn_label.split(".")
                if len(parts) == 2:
                    view_owner = _lookup_view_owner(cursor, parts[0], parts[1])

            friendly = parse_teradata_error(
                exc, product_name, user, host,
                query_context=warn_label,
                view_owner=view_owner,
            )
            return [], f"⚠  Skipped {warn_label}:\n\n{str(friendly)}"
        raise


def collect(
    product_name: str,
    connection: Any,
    lookback_days: int = 90,
) -> tuple[DataProduct, list[str]]:
    """Query all modules and return a fully populated DataProduct plus any warnings.

    Returns:
        (DataProduct, warnings) where warnings is a list of non-fatal messages
        for queries that were skipped due to insufficient DBC grants.

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

    warnings: list[str] = []

    def q(sql: str, model_class: type) -> list:
        return _run(cur, sql, model_class, product_name, user, host)

    def q_opt(sql: str, model_class: type, label: str) -> list:
        rows, warn = _run_optional(cur, sql, model_class, product_name, user, host, label)
        if warn:
            warnings.append(warn)
        return rows

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

        # lineage_graph JOINs DBC.TablesV to resolve object kinds. This requires
        # the view owner to hold SELECT WITH GRANT OPTION on DBC.TablesV — a DBA
        # privilege that may not be present. Treated as optional: failure produces
        # a warning rather than aborting the whole collection run.
        lineage_graph = q_opt(
            f"SELECT * FROM {sem}.lineage_graph ORDER BY lineage_id, edge_relationship",
            LineageGraphEdge,
            label=f"{sem}.lineage_graph",
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
    ), warnings
