"""CLI entry point.

Usage:
    data-product-guide store-password              # save credentials to system keyring
    data-product-guide generate MortgagePlatform --output ./output
    data-product-guide generate MortgagePlatform --artefact cookbook
    data-product-guide dump    MortgagePlatform --output ./output/data.json
    data-product-guide render  ./output/data.json  --output ./output

Password resolution order:
    1. TD_PASSWORD environment variable (session-only, never written to disk)
    2. System keyring  (stored via `data-product-guide store-password`)
    3. Interactive prompt (masked, not echoed)
"""

from __future__ import annotations

import getpass
import os
from pathlib import Path

import typer
from dotenv import load_dotenv

from . import __version__
from .collector import collect
from .renderers.cookbook import render_cookbook
from .renderers.ops_dashboard import render_ops_dashboard

_KEYRING_SERVICE = "data-product-guide"

app = typer.Typer(
    help="Generate AI-Native Data Product artefacts from Teradata metadata.",
    add_completion=False,
)


def _get_password(host: str, user: str) -> str:
    """Resolve password without ever reading from a file."""
    # 1 — environment variable (caller's responsibility to keep it off disk)
    pwd = os.environ.get("TD_PASSWORD")
    if pwd:
        return pwd

    # 2 — system keyring
    try:
        import keyring

        pwd = keyring.get_password(_KEYRING_SERVICE, f"{user}@{host}")
        if pwd:
            return pwd
    except Exception:
        pass

    # 3 — interactive prompt (masked)
    return getpass.getpass(f"Teradata password for {user}@{host}: ")


def _connect():
    """Return an open teradatasql connection."""
    import teradatasql

    load_dotenv()
    host = os.environ.get("TD_HOST")
    user = os.environ.get("TD_USER")

    if not host or not user:
        typer.echo("ERROR: TD_HOST and TD_USER must be set in .env or environment.", err=True)
        raise typer.Exit(1)

    password = _get_password(host, user)
    return teradatasql.connect(host=host, user=user, password=password)


@app.command("store-password")
def store_password():
    """Save Teradata credentials to the system keyring (never written to disk)."""
    import keyring

    load_dotenv()
    host = os.environ.get("TD_HOST") or typer.prompt("Teradata host")
    user = os.environ.get("TD_USER") or typer.prompt("Teradata user")
    pwd = getpass.getpass(f"Password for {user}@{host}: ")

    keyring.set_password(_KEYRING_SERVICE, f"{user}@{host}", pwd)
    typer.echo(f"Password stored in system keyring for {user}@{host}.")
    typer.echo("Run `data-product-guide generate <product>` — no password prompt needed.")


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

    typer.echo(f"data-product-guide {__version__} — connecting to Teradata…")
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
        typer.echo(f"  Cookbook      → {path}")

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
    typer.echo("Connecting to Teradata…")
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
    """Render artefacts from a previously saved JSON snapshot (no Teradata connection needed)."""
    from .models import DataProduct

    dp = DataProduct.model_validate_json(snapshot.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)

    if artefact in ("all", "cookbook"):
        path = output / f"{dp.product_name}_Cookbook.html"
        path.write_text(render_cookbook(dp), encoding="utf-8")
        typer.echo(f"  Cookbook      → {path}")

    if artefact in ("all", "ops"):
        path = output / f"{dp.product_name}_ops_dashboard.html"
        path.write_text(render_ops_dashboard(dp), encoding="utf-8")
        typer.echo(f"  Ops dashboard → {path}")


def main() -> None:
    app()
