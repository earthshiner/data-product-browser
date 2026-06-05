"""Extracts metadata for AI-Native Data Products from Teradata.

Discovery is registry-driven. A top-level governance registry
(``<registry_db>.active_data_product_registry``) names, per product, the view
database for each module. The collector reads from those view databases (the
business/standard view layer, never base tables) so it honours the object
placement standard and adapts to each system's database naming.

Every module query is best-effort: a missing table or a permission gap yields a
warning rather than aborting the whole collection.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from .config import resolve_registry_db
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
    LineageRun,
    ModuleRegistryEntry,
    ProductMap,
    QualityMetric,
    Recipe,
    RegistryEntry,
    TableRelationship,
    TrustReport,
    ViewMetadata,
)

_REGISTRY_TABLE = "active_data_product_registry"


def _fix(value: Any) -> Any:
    """Repair mojibake in string values (UTF-8 bytes stored in a LATIN column)."""
    if isinstance(value, str):
        import ftfy

        return ftfy.fix_text(value)
    return value


def _rows(cursor: Any, model_class: type) -> list:
    cols = [d[0].lower() for d in cursor.description]
    return [model_class(**{k: _fix(v) for k, v in zip(cols, row)}) for row in cursor.fetchall()]


def discover_products(connection: Any, registry_db: str | None = None) -> list[RegistryEntry]:
    """Return active products from the governance registry.

    Args:
        connection: Open teradatasql connection.
        registry_db: Database holding ``active_data_product_registry``. When None,
            resolved from the ``TDP_REGISTRY_DB`` env var or the standard default.
    """
    registry_db = resolve_registry_db(registry_db)
    with connection.cursor() as cur:
        cur.execute(
            f"SELECT * FROM {registry_db}.{_REGISTRY_TABLE} "
            f"WHERE product_status = 'ACTIVE' ORDER BY product_name"
        )
        return _rows(cur, RegistryEntry)


def _find_registry_entry(
    connection: Any, product_name: str, registry_db: str | None
) -> RegistryEntry | None:
    for entry in discover_products(connection, registry_db):
        if entry.product_name == product_name:
            return entry
    return None


def collect(
    product_name: str,
    connection: Any,
    registry_db: str | None = None,
    lookback_days: int = 90,
) -> tuple[DataProduct, list[str]]:
    """Query all modules for one product and return a DataProduct plus warnings.

    Args:
        product_name: The registry ``product_name`` (e.g. "CallCentre Data Product").
        connection: Open teradatasql connection.
        registry_db: Governance registry database. When None, resolved from env
            (``TDP_REGISTRY_DB``) or the standard default.
        lookback_days: Observability window for time-bounded tables.
    """
    registry_db = resolve_registry_db(registry_db)
    warnings: list[str] = []

    entry = _find_registry_entry(connection, product_name, registry_db)
    if entry is None:
        raise ValueError(f"Product '{product_name}' not found in {registry_db}.{_REGISTRY_TABLE}.")

    sem = entry.semantic_view_database or entry.semantic_database
    mem = entry.memory_view_database or entry.memory_database
    obs = entry.observability_view_database or entry.observability_database

    with connection.cursor() as cur:

        def q_opt(db: str | None, table: str, model_class: type, suffix: str = "") -> list:
            """Run one optional query; on failure append a warning and return []."""
            if not db:
                warnings.append(f"⚠  Skipped {table}: no database registered for its module.")
                return []
            ref = f"{db}.{table}"
            try:
                cur.execute(f"SELECT * FROM {ref}{(' ' + suffix) if suffix else ''}")
                return _rows(cur, model_class)
            except ValidationError as exc:
                # Surface field-level detail so the mismatch is actionable:
                # "<column>: <reason>" per error, pointing at the model to fix.
                details = "; ".join(
                    f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()[:8]
                )
                warnings.append(
                    f"⚠  Skipped {ref}: {exc.error_count()} validation error(s) "
                    f"in {model_class.__name__} — {details}"
                )
                return []
            except Exception as exc:
                warnings.append(f"⚠  Skipped {ref}:\n\n  {str(exc).splitlines()[0]}")
                return []

        window = f"CURRENT_TIMESTAMP - INTERVAL '{int(lookback_days)}' DAY"
        valid = "(valid_to IS NULL OR valid_to >= CURRENT_DATE)"

        # --- Semantic -------------------------------------------------------
        modules = q_opt(
            sem, "data_product_map", ProductMap, "WHERE is_active = 1 ORDER BY module_id"
        )
        entities = q_opt(
            sem,
            "entity_metadata",
            EntityMetadata,
            "WHERE is_active = 1 ORDER BY module_name, entity_name",
        )
        columns = q_opt(sem, "column_metadata", ColumnMetadata, "WHERE is_active = 1")
        relationships = q_opt(sem, "table_relationship", TableRelationship, "WHERE is_active = 1")
        trust_rows = q_opt(sem, "trust_engine_latest", TrustReport)
        view_metadata = q_opt(
            sem,
            "view_metadata",
            ViewMetadata,
            "WHERE is_active = 1 ORDER BY base_table, is_primary DESC, view_name",
        )
        # data_lineage (definitional) was relocated to the Semantic catalog module.
        data_lineage = q_opt(
            sem, "data_lineage", DataLineage, "WHERE is_active = 1 ORDER BY lineage_id"
        )

        # --- Memory ---------------------------------------------------------
        recipes = q_opt(
            mem, "Query_Cookbook", Recipe, f"WHERE is_active = 1 AND {valid} ORDER BY recipe_id"
        )
        glossary = q_opt(
            mem,
            "Business_Glossary",
            GlossaryTerm,
            f"WHERE is_active = 1 AND {valid} ORDER BY term_category, term",
        )
        decisions = q_opt(
            mem,
            "Design_Decision",
            DesignDecision,
            f"WHERE is_current = 1 AND {valid} ORDER BY decision_category, decision_id",
        )
        module_registry = q_opt(
            mem,
            "Module_Registry",
            ModuleRegistryEntry,
            f"WHERE is_current = 1 AND {valid} ORDER BY module_name",
        )
        implementation_notes = q_opt(
            mem,
            "Implementation_Note",
            ImplementationNote,
            f"WHERE is_active = 1 AND {valid} ORDER BY severity, note_id",
        )
        change_log = q_opt(mem, "Change_Log", ChangeLogEntry, "ORDER BY created_timestamp DESC")

        # --- Observability (rolling window) ---------------------------------
        quality_metrics = q_opt(
            obs,
            "data_quality_metric",
            QualityMetric,
            f"WHERE measured_dts >= {window} ORDER BY measured_dts DESC",
        )
        change_events = q_opt(
            obs,
            "change_event",
            ChangeEvent,
            f"WHERE change_dts >= {window} ORDER BY change_dts DESC",
        )
        lineage_run = q_opt(
            obs, "lineage_run", LineageRun, f"WHERE run_dts >= {window} ORDER BY run_dts DESC"
        )
        agent_outcomes = q_opt(
            obs,
            "agent_outcome",
            AgentOutcome,
            f"WHERE action_dts >= {window} ORDER BY action_dts DESC",
        )

    return DataProduct(
        product_name=product_name,
        generated_dts=datetime.now(timezone.utc),
        registry=entry,
        trust=trust_rows[0] if trust_rows else None,
        modules=modules,
        entities=entities,
        columns=columns,
        relationships=relationships,
        recipes=recipes,
        glossary=glossary,
        decisions=decisions,
        module_registry=module_registry,
        implementation_notes=implementation_notes,
        change_log=change_log,
        view_metadata=view_metadata,
        data_lineage=data_lineage,
        quality_metrics=quality_metrics,
        change_events=change_events,
        lineage_run=lineage_run,
        agent_outcomes=agent_outcomes,
    ), warnings
