"""Pydantic v2 models derived directly from the AI-Native Data Product DDL.

Each model maps 1-to-1 to a Teradata table. The top-level DataProduct
aggregates all modules into a single serialisable snapshot used by renderers.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

_TD_DATE_9999 = date(9999, 12, 31)


class _Base(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Semantic module
# ---------------------------------------------------------------------------


class ProductMap(_Base):
    """MortgagePlatform_Semantic.data_product_map"""

    map_key: int
    module_name: str
    database_name: str
    module_purpose: Optional[str] = None
    primary_tables: Optional[str] = None
    agent_entry_view: Optional[str] = None
    is_active: int = 1


class EntityMetadata(_Base):
    """MortgagePlatform_Semantic.entity_metadata"""

    entity_metadata_key: int
    module_name: str
    entity_name: str
    database_name: str
    table_name: str
    view_name: Optional[str] = None
    natural_key_column: Optional[str] = None
    surrogate_key_column: Optional[str] = None
    entity_description: Optional[str] = None
    entity_category: Optional[str] = None
    record_count_approx: Optional[int] = None
    is_active: int = 1


class ColumnMetadata(_Base):
    """MortgagePlatform_Semantic.column_metadata"""

    column_metadata_key: int
    database_name: str
    table_name: str
    column_name: str
    business_description: Optional[str] = None
    data_type: Optional[str] = None
    is_pii: int = 0
    is_sensitive: int = 0
    is_required: int = 1
    is_active: int = 1
    sample_values: Optional[str] = None
    validation_rule: Optional[str] = None


class TableRelationship(_Base):
    """MortgagePlatform_Semantic.table_relationship"""

    relationship_key: int
    from_database: str
    from_table: str
    from_column: str
    to_database: str
    to_table: str
    to_column: str
    relationship_type: str
    join_type: str = "LEFT"
    cardinality: Optional[str] = None
    is_mandatory: int = 0
    is_active: int = 1
    relationship_desc: Optional[str] = None


class NamingStandard(_Base):
    """MortgagePlatform_Semantic.naming_standard"""

    naming_standard_key: int
    standard_type: str
    pattern: str
    meaning: str
    example: Optional[str] = None
    is_active: int = 1


# ---------------------------------------------------------------------------
# Memory module
# ---------------------------------------------------------------------------


class Recipe(_Base):
    """MortgagePlatform_Memory.Query_Cookbook"""

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
    source_module: str
    module_version: Optional[str] = None
    is_active: int = 1
    valid_from: date
    valid_to: Optional[date] = None
    created_timestamp: Optional[datetime] = None
    updated_timestamp: Optional[datetime] = None


class GlossaryTerm(_Base):
    """MortgagePlatform_Memory.Business_Glossary"""

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
    """MortgagePlatform_Memory.Design_Decision"""

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
    """MortgagePlatform_Memory.Module_Registry"""

    module_registry_key: int
    module_name: str
    database_name: str
    deployment_status: str = "DEPLOYED"
    module_version: str
    module_purpose: str
    module_scope: Optional[str] = None
    key_entities: Optional[str] = None
    dependencies: Optional[str] = None
    dependents: Optional[str] = None
    data_owner: Optional[str] = None
    technical_owner: Optional[str] = None
    version_date: date
    is_current: int = 1
    valid_from: date
    valid_to: Optional[date] = None
    created_timestamp: Optional[datetime] = None
    updated_timestamp: Optional[datetime] = None


class ImplementationNote(_Base):
    """MortgagePlatform_Memory.Implementation_Note"""

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
    """MortgagePlatform_Memory.Change_Log"""

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
    """MortgagePlatform_Observability.data_quality_metric"""

    quality_metric_key: int
    database_name: str
    table_name: str
    metric_name: str
    metric_value: Optional[float] = None
    threshold_value: Optional[float] = None
    is_below_threshold: int = 0
    measured_at: datetime
    quality_context: Optional[str] = None


class LineageRun(_Base):
    """MortgagePlatform_Observability.lineage_run"""

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


class AgentOutcome(_Base):
    """MortgagePlatform_Observability.agent_outcome"""

    outcome_key: int
    agent_type: str
    session_key: Optional[int] = None
    outcome_type: str
    outcome_dts: datetime
    confidence_score: Optional[float] = None
    user_feedback: Optional[str] = None
    source_system: Optional[str] = None
    columns_mapped: Optional[int] = None
    columns_unmapped: Optional[int] = None
    sql_generated: Optional[str] = None
    rows_returned: Optional[int] = None


class ChangeEvent(_Base):
    """MortgagePlatform_Observability.change_event"""

    change_event_key: int
    event_dts: datetime
    database_name: str
    table_name: str
    operation_type: str
    records_affected: Optional[int] = None
    changed_by: Optional[str] = None
    job_name: Optional[str] = None
    session_id: Optional[str] = None
    batch_key: Optional[str] = None
    is_successful: int = 1


class DataLineage(_Base):
    """MortgagePlatform_Observability.data_lineage — registered ETL lineage edges."""

    lineage_id: int
    source_database: Optional[str] = None
    source_table: Optional[str] = None
    source_system: Optional[str] = None
    target_database: Optional[str] = None
    target_table: str
    job_name: Optional[str] = None
    transformation_type: Optional[str] = None
    transformation_logic: Optional[str] = None
    openlineage_job_name: Optional[str] = None
    openlineage_namespace: Optional[str] = None
    is_active: int = 1
    registered_dts: Optional[datetime] = None
    retired_dts: Optional[datetime] = None
    created_at: Optional[datetime] = None


class LineageGraphEdge(_Base):
    """MortgagePlatform_Semantic.lineage_graph — flattened graph edges (view output).

    Each row is one directed edge: source object → job → target object.
    The view produces two rows per data_lineage entry (ETL_INPUT + ETL_OUTPUT),
    giving a complete source-job-target triple when read together by lineage_id.
    """

    src_object_name_fq: str
    src_container_name: str
    src_object_name: str
    src_kind: str
    src_display_name: str
    edge_relationship: str          # 'ETL_INPUT' | 'ETL_OUTPUT'
    transformation_type: Optional[str] = None
    transformation_logic: Optional[str] = None
    lineage_id: int
    tgt_object_name_fq: str
    tgt_container_name: str
    tgt_object_name: str
    tgt_kind: str
    tgt_display_name: str


# ---------------------------------------------------------------------------
# Top-level aggregate
# ---------------------------------------------------------------------------


class DataProduct(_Base):
    """Complete snapshot of one AI-Native Data Product, ready for rendering."""

    product_name: str
    generated_at: datetime

    # Semantic
    modules: list[ProductMap] = []
    entities: list[EntityMetadata] = []
    columns: list[ColumnMetadata] = []
    relationships: list[TableRelationship] = []
    naming_standards: list[NamingStandard] = []

    # Memory
    recipes: list[Recipe] = []
    glossary: list[GlossaryTerm] = []
    decisions: list[DesignDecision] = []
    module_registry: list[ModuleRegistryEntry] = []
    implementation_notes: list[ImplementationNote] = []
    change_log: list[ChangeLogEntry] = []

    # Observability
    quality_metrics: list[QualityMetric] = []
    lineage_runs: list[LineageRun] = []
    agent_outcomes: list[AgentOutcome] = []
    change_events: list[ChangeEvent] = []
    data_lineage: list[DataLineage] = []

    # Semantic (view over Observability)
    lineage_graph: list[LineageGraphEdge] = []
