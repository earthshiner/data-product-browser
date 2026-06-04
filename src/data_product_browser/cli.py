"""CLI entry point.

Usage:
    data-product-browser store-password              # save credentials to system keyring
    data-product-browser generate MortgagePlatform --output ./output
    data-product-browser generate MortgagePlatform --artefact cookbook
    data-product-browser dump    MortgagePlatform --output ./output/data.json
    data-product-browser render  ./output/data.json  --output ./output

Password resolution order:
    1. TD_PASSWORD environment variable (session-only, never written to disk)
    2. System keyring  (stored via `data-product-browser store-password`)
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
from .exceptions import (
    DataProductError,
    InvalidArtefactError,
    InvalidSnapshotError,
    SnapshotNotFoundError,
)
from .renderers.cookbook import render_cookbook
from .renderers.ops_dashboard import render_ops_dashboard

_KEYRING_SERVICE = "data-product-browser"
_VALID_ARTEFACTS = ("all", "cookbook", "ops")

app = typer.Typer(
    help="Generate AI-Native Data Product artefacts from Teradata metadata.",
    add_completion=False,
)


def _abort(message: str) -> None:
    """Print a clean error message and exit without a traceback."""
    typer.echo(f"\n✘  {message}\n", err=True)
    raise typer.Exit(1)


def _get_password(host: str, user: str) -> str:
    """Resolve password without ever reading from a file."""
    pwd = os.environ.get("TD_PASSWORD")
    if pwd:
        return pwd

    try:
        import keyring

        pwd = keyring.get_password(_KEYRING_SERVICE, f"{user}@{host}")
        if pwd:
            return pwd
    except Exception:
        pass

    return getpass.getpass(f"Teradata password for {user}@{host}: ")


def _connect():
    """Return an open teradatasql connection with friendly error handling."""
    import teradatasql

    load_dotenv()
    host = os.environ.get("TD_HOST")
    user = os.environ.get("TD_USER")

    if not host:
        _abort(
            "TD_HOST is not set.\n\n  Add it to your .env file:\n\n    TD_HOST=your-teradata-host"
        )
    if not user:
        _abort("TD_USER is not set.\n\n  Add it to your .env file:\n\n    TD_USER=your-username")

    password = _get_password(host, user)

    try:
        return teradatasql.connect(host=host, user=user, password=password)
    except Exception as exc:
        msg = str(exc)
        if "8017" in msg or "1017" in msg or "invalid" in msg.lower():
            _abort(
                "Login failed — the username or password is incorrect.\n\n"
                "  Re-store your password:\n\n"
                "    data-product-browser store-password"
            )
        if "unable to connect" in msg.lower() or "connection refused" in msg.lower():
            _abort(
                f"Cannot connect to Teradata at '{host}'.\n\n"
                f"  Check that TD_HOST in your .env is correct and the host is reachable."
            )
        _abort(f"Connection failed:\n\n  {msg.splitlines()[0]}")


def _validate_artefact(value: str) -> None:
    if value not in _VALID_ARTEFACTS:
        _abort(str(InvalidArtefactError(value)))


@app.command("store-password")
def store_password():
    """Save Teradata credentials to the system keyring (never written to disk)."""
    try:
        import keyring
    except ImportError:
        _abort("The 'keyring' package is not installed. Run: uv sync")

    load_dotenv()
    host = typer.prompt("Teradata host", default=os.environ.get("TD_HOST", ""))
    user = typer.prompt("Teradata user", default=os.environ.get("TD_USER", ""))
    if not host:
        _abort("Host is required.")
    if not user:
        _abort("User is required.")
    pwd = getpass.getpass(f"Password for {user}@{host}: ")

    try:
        keyring.set_password(_KEYRING_SERVICE, f"{user}@{host}", pwd)
    except Exception as exc:
        _abort(f"Could not save to system keyring:\n\n  {exc}")

    typer.echo(f"\n✔  Password stored for {user}@{host}.")
    typer.echo("   Run `data-product-browser generate <product>` — no password prompt needed.\n")


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
    _validate_artefact(artefact)

    try:
        output.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _abort(f"Cannot create output directory '{output}':\n\n  {exc}")

    typer.echo(f"\ndata-product-browser {__version__} — connecting to Teradata…")
    conn = _connect()

    try:
        typer.echo(f"Collecting metadata for '{product}'…")
        dp, warnings = collect(product, conn, lookback_days=lookback)
    except DataProductError as exc:
        _abort(str(exc))
    except Exception as exc:
        _abort(f"Unexpected error while collecting metadata:\n\n  {exc}")
    finally:
        conn.close()

    typer.echo(
        f"  {len(dp.recipes)} recipes  |  {len(dp.entities)} entities  |  "
        f"{len(dp.glossary)} glossary terms  |  {len(dp.quality_metrics)} quality metrics"
    )
    for w in warnings:
        typer.echo(f"\n{w}", err=True)

    try:
        if artefact in ("all", "cookbook"):
            path = output / f"{product}_Cookbook.html"
            path.write_text(render_cookbook(dp), encoding="utf-8")
            typer.echo(f"  Cookbook      → {path}")

        if artefact in ("all", "ops"):
            path = output / f"{product}_ops_dashboard.html"
            path.write_text(render_ops_dashboard(dp), encoding="utf-8")
            typer.echo(f"  Ops dashboard → {path}")
    except OSError as exc:
        _abort(f"Could not write output file:\n\n  {exc}")
    except Exception as exc:
        _abort(f"Rendering failed:\n\n  {exc}")

    typer.echo("")


@app.command()
def dump(
    product: str = typer.Argument(..., help="Data product name prefix"),
    output: Path = typer.Option(
        Path("data.json"), "--output", "-o", help="Path to write JSON snapshot"
    ),
    lookback: int = typer.Option(90, "--lookback", help="Observability lookback in days"),
):
    """Dump the raw DataProduct snapshot to JSON (useful for offline rendering/debugging)."""
    typer.echo(f"\nConnecting to Teradata…")
    conn = _connect()

    try:
        typer.echo(f"Collecting metadata for '{product}'…")
        dp, warnings = collect(product, conn, lookback_days=lookback)
    except DataProductError as exc:
        _abort(str(exc))
    except Exception as exc:
        _abort(f"Unexpected error while collecting metadata:\n\n  {exc}")
    finally:
        conn.close()

    for w in warnings:
        typer.echo(f"\n{w}", err=True)

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(dp.model_dump_json(indent=2), encoding="utf-8")
    except OSError as exc:
        _abort(f"Could not write snapshot to '{output}':\n\n  {exc}")

    typer.echo(f"  Snapshot written → {output}\n")


@app.command()
def render(
    snapshot: Path = typer.Argument(..., help="Path to a JSON snapshot from `dump`"),
    output: Path = typer.Option(Path("."), "--output", "-o"),
    artefact: str = typer.Option("all", "--artefact", "-a"),
):
    """Render artefacts from a previously saved JSON snapshot (no Teradata connection needed)."""
    from .models import DataProduct

    _validate_artefact(artefact)

    if not snapshot.exists():
        _abort(str(SnapshotNotFoundError(str(snapshot))))

    try:
        dp = DataProduct.model_validate_json(snapshot.read_text(encoding="utf-8"))
    except Exception as exc:
        _abort(str(InvalidSnapshotError(str(snapshot), str(exc))))

    try:
        output.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _abort(f"Cannot create output directory '{output}':\n\n  {exc}")

    try:
        if artefact in ("all", "cookbook"):
            path = output / f"{dp.product_name}_Cookbook.html"
            path.write_text(render_cookbook(dp), encoding="utf-8")
            typer.echo(f"  Cookbook      → {path}")

        if artefact in ("all", "ops"):
            path = output / f"{dp.product_name}_ops_dashboard.html"
            path.write_text(render_ops_dashboard(dp), encoding="utf-8")
            typer.echo(f"  Ops dashboard → {path}")
    except OSError as exc:
        _abort(f"Could not write output file:\n\n  {exc}")
    except Exception as exc:
        _abort(f"Rendering failed:\n\n  {exc}")

    typer.echo("")


def main() -> None:
    app()
