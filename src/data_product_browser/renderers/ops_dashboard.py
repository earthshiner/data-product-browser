"""Renders the Operational Dashboard HTML artefact.

Follows the window.__DATA__ injection pattern from the existing
MortgagePlatform_ops_dashboard.html: Python serialises the DataProduct to JSON,
the template injects it, and all rendering is done client-side in JavaScript.
This keeps the Python renderer thin and the template independently editable.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..models import DataProduct

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _build_data(dp: DataProduct) -> dict:
    """Build the window.__DATA__ JSON payload consumed by the dashboard JS."""

    # --- Trust score: percentage of quality metrics above threshold ----------
    passing = sum(1 for m in dp.quality_metrics if not m.is_below_threshold)
    total_q = len(dp.quality_metrics) or 1
    trust_pct = round((passing / total_q) * 100)

    # --- Lineage health: % of runs with SUCCESS status -----------------------
    success_runs = sum(1 for r in dp.lineage_runs if r.run_status.upper() == "SUCCESS")
    total_runs = len(dp.lineage_runs) or 1
    lineage_health_pct = round((success_runs / total_runs) * 100)

    # --- Quality failures per table ------------------------------------------
    failures_by_table: dict[str, list] = defaultdict(list)
    for m in dp.quality_metrics:
        if m.is_below_threshold:
            failures_by_table[f"{m.database_name}.{m.table_name}"].append(
                {
                    "metric": m.metric_name,
                    "value": float(m.metric_value) if m.metric_value is not None else None,
                    "threshold": float(m.threshold_value)
                    if m.threshold_value is not None
                    else None,
                    "measured_dts": m.measured_dts.isoformat(),
                }
            )

    # --- Module status from Memory.Module_Registry ---------------------------
    modules_status = [
        {
            "name": m.module_name,
            "database": m.database_name,
            "status": m.deployment_status,
            "version": m.module_version,
            "purpose": m.module_purpose,
            "data_owner": m.data_owner,
            "technical_owner": m.technical_owner,
            "version_date": m.version_date.isoformat(),
        }
        for m in dp.module_registry
    ]

    # --- Recent lineage runs (last 20) ---------------------------------------
    recent_runs = [
        {
            "run_id": r.lineage_run_id,
            "lineage_id": r.lineage_id,
            "job": r.job_name or f"lineage_{r.lineage_id}",
            "status": r.run_status,
            "run_dts": r.run_dts.isoformat(),
            "duration_ms": r.run_duration_ms,
            "records_read": r.records_read,
            "records_written": r.records_written,
            "records_rejected": r.records_rejected,
            "error": r.error_message,
        }
        for r in dp.lineage_runs[:20]
    ]

    # --- Agent outcomes summary ----------------------------------------------
    outcomes_by_type: dict[str, int] = defaultdict(int)
    avg_confidence = 0.0
    conf_count = 0
    for o in dp.agent_outcomes:
        outcomes_by_type[o.outcome_type] += 1
        if o.confidence_score is not None:
            avg_confidence += float(o.confidence_score)
            conf_count += 1

    agent_summary = {
        "by_type": dict(outcomes_by_type),
        "avg_confidence": round(avg_confidence / conf_count, 3) if conf_count else None,
        "total": len(dp.agent_outcomes),
    }

    # --- Recent change events (last 20) --------------------------------------
    recent_changes = [
        {
            "event_dts": e.event_dts.isoformat(),
            "database": e.database_name,
            "table": e.table_name,
            "operation": e.operation_type,
            "records_affected": e.records_affected,
            "changed_by": e.changed_by,
            "job": e.job_name,
            "successful": bool(e.is_successful),
        }
        for e in dp.change_events[:20]
    ]

    # --- Data Freshness (Panel 2) from lineage_runs --------------------------
    freshness_rows = []
    for r in dp.lineage_runs:
        age_h = (
            dp.generated_dts
            - r.run_dts.replace(
                tzinfo=dp.generated_dts.tzinfo if r.run_dts.tzinfo is None else r.run_dts.tzinfo
            )
        ).total_seconds() / 3600
        if age_h <= 24:
            status = "FRESH"
        elif age_h <= 48:
            status = "STALE"
        else:
            status = "CRITICAL"
        freshness_rows.append(
            {
                "job": r.job_name or f"lineage_{r.lineage_id}",
                "run_dts": r.run_dts.isoformat(),
                "run_status": r.run_status,
                "freshness_status": status,
                "freshness_hours": round(age_h, 1),
                "duration_ms": r.run_duration_ms,
                "records_written": r.records_written,
                "error": r.error_message,
            }
        )

    fresh_count = sum(1 for r in freshness_rows if r["freshness_status"] == "FRESH")
    stale_count = sum(1 for r in freshness_rows if r["freshness_status"] == "STALE")
    critical_count = sum(1 for r in freshness_rows if r["freshness_status"] == "CRITICAL")

    # --- Changes & Decisions (Panel 8) from Memory ---------------------------
    change_log_rows = [
        {
            "change_id": c.change_id,
            "version": c.version_number,
            "title": c.change_title,
            "type": c.change_type,
            "category": c.change_category,
            "module": c.source_module,
            "deployed_date": c.deployed_date.isoformat() if c.deployed_date else None,
            "status": c.deployment_status,
        }
        for c in dp.change_log[:20]
    ]
    design_decision_rows = [
        {
            "decision_id": d.decision_id,
            "title": d.decision_title,
            "category": d.decision_category,
            "status": d.decision_status,
            "module": d.source_module,
            "rationale": d.rationale,
            "decided_by": d.decided_by,
            "decided_date": d.decided_date.isoformat() if d.decided_date else None,
        }
        for d in dp.decisions[:20]
    ]

    # --- Glossary & Discovery (Panel 9) from Memory + Semantic ---------------
    glossary_rows = [
        {
            "term": g.term,
            "category": g.term_category,
            "definition": g.definition,
            "context": g.business_context,
            "related_table": g.related_table,
            "module": g.source_module,
        }
        for g in dp.glossary
    ]
    entity_rows = [
        {
            "name": e.entity_name,
            "module": e.module_name,
            "database": e.database_name,
            "table": e.table_name,
            "description": e.entity_description,
            "natural_key": e.natural_key_column,
        }
        for e in dp.entities
    ]

    return {
        "product_name": dp.product_name,
        "generated_dts": dp.generated_dts.isoformat(),
        "trust_score": trust_pct,
        "lineage_health_pct": lineage_health_pct,
        "total_quality_checks": len(dp.quality_metrics),
        "quality_failures": len([m for m in dp.quality_metrics if m.is_below_threshold]),
        "failures_by_table": dict(failures_by_table),
        "modules": modules_status,
        "recent_lineage_runs": recent_runs,
        "agent_summary": agent_summary,
        "recent_changes": recent_changes,
        "recipe_count": len(dp.recipes),
        "entity_count": len(dp.entities),
        # Panel 2
        "freshness_rows": freshness_rows,
        "freshness_summary": {
            "fresh": fresh_count,
            "stale": stale_count,
            "critical": critical_count,
            "total": len(freshness_rows),
        },
        # Panel 8
        "change_log": change_log_rows,
        "design_decisions": design_decision_rows,
        # Panel 9
        "glossary": glossary_rows,
        "entities": entity_rows,
    }


def render_ops_dashboard(dp: DataProduct) -> str:
    """Return the complete Ops Dashboard HTML string for the given DataProduct."""
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=False,
    )
    template = env.get_template("ops_dashboard.html.j2")
    data_json = json.dumps(_build_data(dp), default=str, indent=2)
    return template.render(
        product_name=dp.product_name,
        generated_dts=dp.generated_dts.strftime("%Y-%m-%d %H:%M UTC"),
        data_json=data_json,
    )
