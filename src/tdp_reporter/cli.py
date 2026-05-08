"""CLI entry point.

Usage:
    tdp-reporter generate MortgagePlatform --output ./output
    tdp-reporter generate MortgagePlatform --artefact cookbook
    tdp-reporter generate MortgagePlatform --artefact ops
    tdp-reporter dump    MortgagePlatform --output ./output/data.json
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from dotenv import load_dotenv

from . import __version__
from .collector import collect
from .renderers.cookbook import render_cookbook
from .renderers.ops_dashboard import render_ops_dashboard

app = typer.Typer(
    help="Generate AI-Native Data Product artefacts from Teradata metadata.",
    add_completion=False,
)


def _connect():
    """Return an open teradatasql connection, reading credentials from .env."""
    import teradatasql  # imported here so the CLI is importable without the driver

    load_dotenv()
    host = os.environ.get("TD_HOST")
    user = os.environ.get("TD_USER")
    password = os.environ.get("TD_PASSWORD")

    if not all([host, user, password]):
        typer.echo(
            "ERROR: TD_HOST, TD_USER, TD_PASSWORD must be set (copy .env.example → .env)",
            err=True,
        )
        raise typer.Exit(1)

    return teradatasql.connect(host=host, user=user, password=password, charset="UTF8")


@app.command()
def generate(
    product: str = typer.Argument(..., help="Data product name prefix, e.g. MortgagePlatform"),
    output: Path = typer.Option(Path("."), "--output", "-o", help="Output directory"),
    artefact: str = typer.Option(
        "all", "--artefact", "-a", help="Which artefact(s): all | cookbook | ops"
    ),
    lookback: int = typer.Option(90, "--lookback", help="Observability lookback in days"),
):
    """Extract metadata from Teradata and render HTML artefacts."""
    output.mkdir(parents=True, exist_ok=True)

    typer.echo(f"tdp-reporter {__version__} — connecting to Teradata…")
    conn = _connect()
    try:
        typer.echo(f"Collecting metadata for {product}…")
        dp = collect(product, conn, lookback_days=lookback)
    finally:
        conn.close()

    typer.echo(
        f"  {len(dp.recipes)} recipes  |  {len(dp.entities)} entities  |  "
        f"{len(dp.glossary)} glossary terms  |  {len(dp.quality_metrics)} quality metrics"
    )

    if artefact in ("all", "cookbook"):
        path = output / f"{product}_Cookbook.html"
        path.write_text(render_cookbook(dp), encoding="utf-8")
        typer.echo(f"  Cookbook     → {path}")

    if artefact in ("all", "ops"):
        path = output / f"{product}_ops_dashboard.html"
        path.write_text(render_ops_dashboard(dp), encoding="utf-8")
        typer.echo(f"  Ops dashboard → {path}")


@app.command()
def dump(
    product: str = typer.Argument(..., help="Data product name prefix"),
    output: Path = typer.Option(
        Path("data.json"), "--output", "-o", help="Path to write JSON snapshot"
    ),
    lookback: int = typer.Option(90, "--lookback", help="Observability lookback in days"),
):
    """Dump the raw DataProduct snapshot to JSON (useful for offline rendering/debugging)."""
    typer.echo(f"Connecting to Teradata…")
    conn = _connect()
    try:
        dp = collect(product, conn, lookback_days=lookback)
    finally:
        conn.close()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dp.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"Snapshot written → {output}")


@app.command()
def render(
    snapshot: Path = typer.Argument(..., help="Path to a JSON snapshot from `dump`"),
    output: Path = typer.Option(Path("."), "--output", "-o"),
    artefact: str = typer.Option("all", "--artefact", "-a"),
):
    """Render artefacts from a previously dumped JSON snapshot (no Teradata connection needed)."""
    from .models import DataProduct

    dp = DataProduct.model_validate_json(snapshot.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)

    if artefact in ("all", "cookbook"):
        path = output / f"{dp.product_name}_Cookbook.html"
        path.write_text(render_cookbook(dp), encoding="utf-8")
        typer.echo(f"  Cookbook     → {path}")

    if artefact in ("all", "ops"):
        path = output / f"{dp.product_name}_ops_dashboard.html"
        path.write_text(render_ops_dashboard(dp), encoding="utf-8")
        typer.echo(f"  Ops dashboard → {path}")


def main() -> None:
    app()
