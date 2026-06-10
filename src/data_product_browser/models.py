"""Pydantic v2 models for the deployed AI-Native Data Product standard.

Each model maps to a Teradata table/view as actually deployed (verified against
a live product). Discovery is registry-driven: the top-level governance registry
names each module's view database, and the Semantic ``data_product_map`` confirms
them. The top-level DataProduct aggregates all modules into one serialisable
snapshot consumed by the server and renderers.

Fields are deliberately permissive (most Optional) so that minor version drift in
a deployment degrades to missing values rather than a hard validation error.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class _Base(BaseModel):
    # Ignore unmodelled columns so deployments with extra columns still parse.
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


# ---------------------------------------------------------------------------
# Governance registry (top-level discovery)
# ---------------------------------------------------------------------------


class RegistryEntry(_Base):
    """<registry_db>.active_data_product_registry — one row per data product."""

    product_id: Optional[str] = None
    product_name: str
    product_version: Optional[str] = None
    product_description: Optional[str] = None
    product_status: Optional[str] = None
    owner_team: Optional[str] = None

    # Base-table databases
    domain_database: Optional[str] = None
    semantic_database: Optional[str] = None
    memory_database: Optional[str] = None
    observability_database: Optional[str] = None
    search_database: Optional[str] = None
    prediction_database: Optional[str] = None

    # View databases (preferred read layer)
    domain_view_database: Optional[str] = None
    semantic_view_database: Optional[str] = None
    memory_view_database: Optional[str] = None
    observability_view_database: Optional[str] = None
    search_view_database: Optional[str] = None
    prediction_view_database: Optional[str] = None

    approved_entrypoint: Optional[str] = None
    approved_access_mode: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Semantic module
# ---------------------------------------------------------------------------


class ProductMap(_Base):
    """<semantic>.data_product_map"""

    module_id: int
    module_name: str
    database_name: str
    module_description: Optional[str] = None
    module_purpose: Optional[str] = None
    naming_pattern: Optional[str] = None
    table_prefix: Optional[str] = None
    primary_tables: Optional[str] = None
    primary_views: Optional[str] = None
    module_version: Optional[str] = None
    deployment_status: Optional[str] = None
    deployed_dts: Optional[datetime] = None
    is_active: int = 1


class EntityMetadata(_Base):
    """<semantic>.entity_metadata"""

    entity_metadata_id: int
    module_name: str
    entity_name: str
    database_name: str
    table_name: str
    view_name: Optional[str] = None
    entity_description: Optional[str] = None
    natural_key_column: Optional[str] = None
    surrogate_key_column: Optional[str] = None
    temporal_pattern: Optional[str] = None
    current_flag_column: Optional[str] = None
    deleted_flag_column: Optional[str] = None
    industry_standard: Optional[str] = None
    is_active: int = 1


class ColumnMetadata(_Base):
    """<semantic>.column_metadata"""

    column_metadata_id: int
    database_name: str
    table_name: str
    column_name: str
    business_description: Optional[str] = None
    data_type: Optional[str] = None
    data_classification: Optional[str] = None
    allowed_values_json: Optional[str] = None
    is_pii: int = 0
    is_sensitive: int = 0
    is_required: int = 1
    is_active: int = 1


class TableRelationship(_Base):
    """<semantic>.table_relationship"""

    relationship_id: int
    relationship_name: Optional[str] = None
    relationship_description: Optional[str] = None
    source_database: str
    source_table: str
    source_column: str
    target_database: str
    target_table: str
    target_column: str
    relationship_type: Optional[str] = None
    cardinality: Optional[str] = None
    relationship_meaning: Optional[str] = None
    is_mandatory: int = 0
    is_active: int = 1


class TrustReport(_Base):
    """<semantic>.trust_engine_latest — latest trust-engine run for the product."""

    product_prefix: Optional[str] = None
    run_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    trust_status: Optional[str] = None
    agent_use_allowed: Optional[int] = None
    total_checks: Optional[int] = None
    passed_count: Optional[int] = None
    failed_count: Optional[int] = None
    error_count: Optional[int] = None
    critical_failure_count: Optional[int] = None
    error_failure_count: Optional[int] = None
    data_product_trust_score: Optional[float] = None
    performance_readiness_score: Optional[float] = None
    operational_readiness_score: Optional[float] = None
    repair_candidate_count: Optional[int] = None
    failed_checks_json: Optional[str] = None
    repair_candidates_json: Optional[str] = None


# ---------------------------------------------------------------------------
# Memory module (matches deployed standard unchanged)
# ---------------------------------------------------------------------------


class Recipe(_Base):
    """<memory>.Query_Cookbook"""

    recipe_key: int
    recipe_id: str
    recipe_title: str
    recipe_description: str
    use_case: str
    target_module: str
    sql_template: str
    parameter_descriptions: Optional[str] = None
    performance_notes: Optional[str] = None
    complexity: str
    is_batch: Optional[int] = None
    source_module: str
    module_version: Optional[str] = None
    is_active: int = 1
    valid_from: date
    valid_to: Optional[date] = None
    created_timestamp: Optional[datetime] = None
    updated_timestamp: Optional[datetime] = None


class GlossaryTerm(_Base):
    """<memory>.Business_Glossary"""

    glossary_key: int
    term: str
    term_category: str
    definition: str
    business_context: Optional[str] = None
    synonyms: Optional[str] = None
    related_terms: Optional[str] = None
    related_table: Optional[str] = None
    related_column: Optional[str] = None
    source_module: str
    module_version: Optional[str] = None
    is_active: int = 1
    valid_from: date
    valid_to: Optional[date] = None


class DesignDecision(_Base):
    """<memory>.Design_Decision"""

    decision_key: int
    decision_id: str
    decision_version: int = 1
    decision_title: str
    decision_description: Optional[str] = None
    context: Optional[str] = None
    alternatives_considered: Optional[str] = None
    rationale: Optional[str] = None
    consequences: Optional[str] = None
    decision_status: str
    decision_category: str
    source_module: str
    module_version: Optional[str] = None
    affects_table: Optional[str] = None
    decided_by: Optional[str] = None
    decided_date: Optional[date] = None
    superseded_by: Optional[str] = None
    valid_from: date
    valid_to: Optional[date] = None
    is_current: int = 1
    created_timestamp: Optional[datetime] = None
    updated_timestamp: Optional[datetime] = None


class ModuleRegistryEntry(_Base):
    """<memory>.Module_Registry"""

    module_registry_key: int
    module_name: str
    database_name: str
    module_version: str
    module_purpose: str
    module_scope: Optional[str] = None
    key_entities: Optional[str] = None
    dependencies: Optional[str] = None
    dependents: Optional[str] = None
    data_owner: Optional[str] = None
    technical_owner: Optional[str] = None
    refresh_frequency: Optional[str] = None
    version_date: date
    is_current: int = 1
    valid_from: date
    valid_to: Optional[date] = None
    created_timestamp: Optional[datetime] = None
    updated_timestamp: Optional[datetime] = None


class ImplementationNote(_Base):
    """<memory>.Implementation_Note"""

    note_key: int
    note_id: str
    note_title: str
    note_content: str
    note_category: str
    severity: Optional[str] = None
    affects_table: Optional[str] = None
    resolution_status: Optional[str] = None
    resolution_notes: Optional[str] = None
    source_module: str
    module_version: Optional[str] = None
    is_active: int = 1
    valid_from: date
    valid_to: Optional[date] = None
    created_timestamp: Optional[datetime] = None
    updated_timestamp: Optional[datetime] = None


class ChangeLogEntry(_Base):
    """<memory>.Change_Log"""

    change_key: int
    change_id: str
    version_number: str
    change_title: str
    change_description: str
    change_type: str
    change_category: str
    source_module: str
    affects_table: Optional[str] = None
    migration_steps: Optional[str] = None
    rollback_steps: Optional[str] = None
    related_decision_id: Optional[str] = None
    deployed_date: Optional[date] = None
    deployed_by: Optional[str] = None
    deployment_status: str
    created_timestamp: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Observability module
# ---------------------------------------------------------------------------


class QualityMetric(_Base):
    """<observability>.data_quality_metric

    Note: ``is_threshold_met`` is 1 when the metric PASSES (the opposite polarity
    to the previous ``is_below_threshold``).
    """

    quality_metric_id: int
    database_name: str
    table_name: str
    column_name: Optional[str] = None
    metric_name: str
    metric_value: Optional[float] = None
    metric_category: Optional[str] = None
    quality_threshold: Optional[float] = None
    is_threshold_met: Optional[int] = None
    sample_size: Optional[int] = None
    measured_dts: datetime
    created_at: Optional[datetime] = None


class ChangeEvent(_Base):
    """<observability>.change_event"""

    change_event_id: int
    database_name: str
    table_name: str
    change_type: str
    change_dts: datetime
    changed_by: Optional[str] = None
    change_reason: Optional[str] = None
    change_source: Optional[str] = None
    records_affected: Optional[int] = None
    columns_changed: Optional[str] = None
    batch_key: Optional[str] = None
    job_name: Optional[str] = None
    created_at: Optional[datetime] = None


class DataLineage(_Base):
    """<semantic>.data_lineage — DEFINITIONAL lineage (one row per flow).

    Relocated to the Semantic (catalog) module; executions live in LineageRun.
    """

    lineage_id: int
    source_database: Optional[str] = None
    source_table: Optional[str] = None
    source_system: Optional[str] = None
    target_database: Optional[str] = None
    target_table: str
    transformation_type: Optional[str] = None
    transformation_logic: Optional[str] = None
    job_name: Optional[str] = None
    openlineage_job_name: Optional[str] = None
    openlineage_namespace: Optional[str] = None
    is_active: int = 1
    registered_dts: Optional[datetime] = None
    retired_dts: Optional[datetime] = None
    created_at: Optional[datetime] = None


class LineageRun(_Base):
    """<observability>.lineage_run — OPERATIONAL execution log (FK -> data_lineage)."""

    lineage_run_id: int
    lineage_id: int
    run_dts: datetime
    run_status: str
    run_duration_ms: Optional[int] = None
    records_read: Optional[int] = None
    records_written: Optional[int] = None
    records_rejected: Optional[int] = None
    batch_key: Optional[str] = None
    job_name: Optional[str] = None
    openlineage_run_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None


class ViewMetadata(_Base):
    """<semantic>.view_metadata — catalogues the views exposing each base table (1:M)."""

    view_metadata_id: int
    base_database: str
    base_table: str
    view_database: str
    view_name: str
    view_type: Optional[str] = None  # LOCKING | BUSINESS | CURRENT | ENRICHED | PIT | DERIVED
    view_purpose: Optional[str] = None
    is_primary: int = 0
    is_active: int = 1


class AgentOutcome(_Base):
    """<observability>.agent_outcome"""

    outcome_id: int
    agent_key: Optional[str] = None
    session_key: Optional[str] = None
    action_type: Optional[str] = None
    action_dts: datetime
    tables_accessed: Optional[str] = None
    outcome_status: Optional[str] = None
    user_feedback: Optional[str] = None
    execution_time_ms: Optional[int] = None
    records_processed: Optional[int] = None
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Top-level aggregate
# ---------------------------------------------------------------------------


class DataProduct(_Base):
    """Complete snapshot of one AI-Native Data Product, ready for rendering."""

    product_name: str
    generated_dts: datetime
    registry: Optional[RegistryEntry] = None
    trust: Optional[TrustReport] = None

    # Semantic
    modules: list[ProductMap] = []
    entities: list[EntityMetadata] = []
    columns: list[ColumnMetadata] = []
    relationships: list[TableRelationship] = []
    view_metadata: list[ViewMetadata] = []
    data_lineage: list[DataLineage] = []  # definitional lineage now lives in Semantic

    # Memory
    recipes: list[Recipe] = []
    glossary: list[GlossaryTerm] = []
    decisions: list[DesignDecision] = []
    module_registry: list[ModuleRegistryEntry] = []
    implementation_notes: list[ImplementationNote] = []
    change_log: list[ChangeLogEntry] = []

    # Observability
    quality_metrics: list[QualityMetric] = []
    change_events: list[ChangeEvent] = []
    lineage_run: list[LineageRun] = []
    agent_outcomes: list[AgentOutcome] = []
