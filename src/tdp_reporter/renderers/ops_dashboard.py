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
            failures_by_table[f"{m.database_name}.{m.table_name}"].append({
                "metric": m.metric_name,
                "value": float(m.metric_value) if m.metric_value is not None else None,
                "threshold": float(m.threshold_value) if m.threshold_value is not None else None,
                "measured_at": m.measured_at.isoformat(),
            })

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

    return {
        "product_name": dp.product_name,
        "generated_at": dp.generated_at.isoformat(),
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
        generated_at=dp.generated_at.strftime("%Y-%m-%d %H:%M UTC"),
        data_json=data_json,
    )
