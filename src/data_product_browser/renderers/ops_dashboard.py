"""Renders the Operational Dashboard HTML artefact.

Follows the window.__DATA__ injection pattern from the existing
MortgagePlatform_ops_dashboard.html: Python serialises the DataProduct to JSON,
the template injects it, and all rendering is done client-side in JavaScript.
This keeps the Python renderer thin and the template independently editable.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..models import DataProduct

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _build_data(dp: DataProduct) -> dict:
    """Build the window.__DATA__ JSON payload consumed by the dashboard JS."""

    # --- Trust score: prefer the trust engine, else quality pass-rate --------
    # is_threshold_met == 1 passes; 0 fails; None is unscored.
    passing = sum(1 for m in dp.quality_metrics if m.is_threshold_met)
    total_q = len(dp.quality_metrics) or 1
    quality_pct = round((passing / total_q) * 100)
    if dp.trust and dp.trust.data_product_trust_score is not None:
        trust_pct = round(dp.trust.data_product_trust_score)
    else:
        trust_pct = quality_pct

    # --- Lineage health: % of registered runs with SUCCESS status ------------
    runs = [r for r in dp.data_lineage if r.run_status]
    success_runs = sum(1 for r in runs if (r.run_status or "").upper() == "SUCCESS")
    total_runs = len(runs) or 1
    lineage_health_pct = round((success_runs / total_runs) * 100)

    # --- Quality failures per table ------------------------------------------
    failures_by_table: dict[str, list] = defaultdict(list)
    for m in dp.quality_metrics:
        if m.is_threshold_met == 0:
            failures_by_table[f"{m.database_name}.{m.table_name}"].append(
                {
                    "metric": m.metric_name,
                    "value": float(m.metric_value) if m.metric_value is not None else None,
                    "threshold": float(m.quality_threshold)
                    if m.quality_threshold is not None
                    else None,
                    "measured_dts": m.measured_dts.isoformat(),
                }
            )

    # --- Module status from Memory.Module_Registry ---------------------------
    modules_status = [
        {
            "name": m.module_name,
            "database": m.database_name,
            "status": "CURRENT" if m.is_current else "SUPERSEDED",
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
            "run_id": r.lineage_id,
            "lineage_id": r.lineage_id,
            "job": r.job_name or f"lineage_{r.lineage_id}",
            "status": r.run_status,
            "run_dts": r.run_dts.isoformat() if r.run_dts else None,
            "duration_ms": None,  # not tracked in data_lineage
            "records_read": r.records_read,
            "records_written": r.records_written,
            "records_rejected": None,  # not tracked in data_lineage
            "error": None,
        }
        for r in dp.data_lineage[:20]
    ]

    # --- Agent outcomes summary ----------------------------------------------
    outcomes_by_type: dict[str, int] = defaultdict(int)
    for o in dp.agent_outcomes:
        outcomes_by_type[o.outcome_status or "unknown"] += 1

    agent_summary = {
        "by_type": dict(outcomes_by_type),
        "avg_confidence": None,  # confidence not tracked in agent_outcome
        "total": len(dp.agent_outcomes),
    }

    # --- Recent change events (last 20) --------------------------------------
    recent_changes = [
        {
            "event_dts": e.change_dts.isoformat() if e.change_dts else None,
            "database": e.database_name,
            "table": e.table_name,
            "operation": e.change_type,
            "records_affected": e.records_affected,
            "changed_by": e.changed_by,
            "job": e.job_name,
            "successful": True,  # change_event has no success flag in the standard
        }
        for e in dp.change_events[:20]
    ]

    # --- Data Freshness (Panel 2) from lineage_runs --------------------------
    freshness_rows = []
    for r in dp.data_lineage:
        if not r.run_dts:
            continue
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
                "duration_ms": None,  # not tracked in data_lineage
                "records_written": r.records_written,
                "error": None,
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
        "quality_failures": len([m for m in dp.quality_metrics if m.is_threshold_met == 0]),
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
