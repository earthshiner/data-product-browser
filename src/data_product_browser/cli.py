"""CLI entry point.

Usage:
    data-product-browser store-password              # save credentials to system keyring
    data-product-browser generate MortgagePlatform --output ./output
    data-product-browser generate MortgagePlatform --artefact cookbook
    data-product-browser dump    MortgagePlatform --output ./output/data.json
    data-product-browser render  ./output/data.json  --output ./output

Teradata connection — every command that touches Teradata accepts the host and
user either as a command-line option or an environment variable (a .env file in
the working directory is loaded automatically):

    host      --td-host         or  TD_HOST
    user      --td-user         or  TD_USER
    password  --td-password     or  TD_PASSWORD   (see resolution order below)

Note: `serve --host` is the WEB bind address; the Teradata host is `--td-host`.

Password resolution order:
    1. --td-password command-line option (may be visible to other processes)
    2. TD_PASSWORD environment variable (session-only, never written to disk)
    3. System keyring  (stored via `data-product-browser store-password`)
    4. Interactive prompt (masked, not echoed)
"""

from __future__ import annotations

import getpass
import os
import re
import sys
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

# Teradata connection environment variables (single source of truth).
_ENV_HOST = "TD_HOST"
_ENV_USER = "TD_USER"
_ENV_PASSWORD = "TD_PASSWORD"

app = typer.Typer(
    help="Generate AI-Native Data Product artefacts from Teradata metadata.",
    add_completion=False,
)


def _abort(message: str) -> None:
    """Print a clean error message and exit without a traceback."""
    typer.echo(f"\n✘  {message}\n", err=True)
    raise typer.Exit(1)


def _env_var_examples(env_var: str, example: str) -> str:
    """Cross-shell snippet for setting an environment variable for the session."""
    return (
        "  Set the environment variable for this shell session:\n\n"
        f'    $env:{env_var} = "{example}"   # PowerShell\n'
        f"    set {env_var}={example}        # Windows cmd.exe\n"
        f'    export {env_var}="{example}"   # bash / zsh'
    )


def _credential_help(label: str, env_var: str, cli_option: str, example: str) -> str:
    """A consistent 'how to provide this' message listing both an arg and env var."""
    return (
        f"No Teradata {label} specified.\n\n"
        f"  Provide it in either of these ways:\n\n"
        f"    • Command-line option:   {cli_option} {example}\n"
        f"    • Environment variable:  {env_var}={example}\n"
        f"      (a '{env_var}={example}' line in a .env file in the current directory works too)\n\n"
        f"{_env_var_examples(env_var, example)}"
    )


def _password_help() -> str:
    return (
        "No Teradata password available, and there is no terminal to prompt on.\n\n"
        "  Provide it in one of these ways:\n\n"
        "    • Store it once (recommended):  data-product-browser store-password\n"
        f"    • Environment variable:         {_ENV_PASSWORD}=your-password\n"
        "    • Command-line option:          --td-password your-password\n"
        "      (a password on the command line may be visible to other processes)\n\n"
        f"{_env_var_examples(_ENV_PASSWORD, 'your-password')}"
    )


def _login_help() -> str:
    """Guidance shown when Teradata rejects the credentials (how to set user + password)."""
    return (
        "Login failed — the Teradata UserId, Password or Account is invalid.\n\n"
        "  Check the username (from --td-user or TD_USER):\n\n"
        "    • Command-line option:   --td-user your-username\n"
        "    • Environment variable:  TD_USER=your-username\n\n"
        "  Set or update the password:\n\n"
        "    • Store it once (recommended):  data-product-browser store-password\n"
        f"    • Environment variable:         {_ENV_PASSWORD}=your-password\n"
        "    • Command-line option:          --td-password your-password\n"
        "      (a password on the command line may be visible to other processes)\n\n"
        f"{_env_var_examples(_ENV_PASSWORD, 'your-password')}"
    )


def _handle_connection_error(exc: Exception, host: str) -> None:
    """Abort with friendly, actionable guidance based on the driver error."""
    msg = str(exc)
    low = msg.lower()
    # 8017 / 1017 / SQLState 28000 are Teradata's invalid-credential codes.
    if "8017" in msg or "1017" in msg or "28000" in msg or "invalid" in low:
        _abort(_login_help())
    if (
        "unable to connect" in low
        or "connection refused" in low
        or "could not be resolved" in low
        or "timed out" in low
        or "10054" in msg
    ):
        _abort(
            f"Cannot reach Teradata at '{host}'.\n\n"
            f"  Check the host (--td-host or TD_HOST) is correct and reachable."
        )
    _abort(f"Connection failed:\n\n  {msg.splitlines()[0]}")


def _resolve_host_user(td_host: str | None, td_user: str | None) -> tuple[str, str]:
    """Resolve Teradata host/user: explicit option > TD_HOST/TD_USER (or .env).

    Aborts with actionable guidance (CLI option *and* env var) if either is absent.
    """
    load_dotenv(override=True)
    host = td_host or os.environ.get(_ENV_HOST)
    user = td_user or os.environ.get(_ENV_USER)
    if not host:
        _abort(_credential_help("host", _ENV_HOST, "--td-host", "your-teradata-host"))
    if not user:
        _abort(_credential_help("username", _ENV_USER, "--td-user", "your-username"))
    return host, user


def _get_password(host: str, user: str, explicit: str | None = None) -> str:
    """Resolve password: explicit option > TD_PASSWORD > keyring > interactive prompt."""
    if explicit:
        return explicit

    pwd = os.environ.get(_ENV_PASSWORD)
    if pwd:
        return pwd

    try:
        import keyring

        pwd = keyring.get_password(_KEYRING_SERVICE, f"{user}@{host}")
        if pwd:
            return pwd
    except Exception:
        pass

    # Nothing stored or supplied — we can only prompt interactively. With no TTY
    # (e.g. a service tab piping output), fail fast with guidance instead of
    # raising an opaque error or blocking forever.
    if not sys.stdin.isatty():
        _abort(_password_help())

    return getpass.getpass(f"Teradata password for {user}@{host}: ")


def _connect(
    td_host: str | None = None,
    td_user: str | None = None,
    td_password: str | None = None,
):
    """Return an open teradatasql connection with friendly error handling."""
    host, user = _resolve_host_user(td_host, td_user)
    password = _get_password(host, user, td_password)

    import teradatasql

    try:
        return teradatasql.connect(host=host, user=user, password=password)
    except Exception as exc:
        _handle_connection_error(exc, host)


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

    load_dotenv(override=True)
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
    product: str = typer.Argument(
        ..., help="Registry product name, e.g. 'CallCentre Data Product'"
    ),
    output: Path = typer.Option(Path("."), "--output", "-o", help="Output directory"),
    artefact: str = typer.Option(
        "all", "--artefact", "-a", help="Which artefact(s): all | cookbook | ops"
    ),
    lookback: int = typer.Option(90, "--lookback", help="Observability lookback in days"),
    td_host: str = typer.Option(None, "--td-host", help="Teradata host (overrides TD_HOST)"),
    td_user: str = typer.Option(None, "--td-user", help="Teradata username (overrides TD_USER)"),
    td_password: str = typer.Option(
        None,
        "--td-password",
        help="Teradata password (overrides TD_PASSWORD; may be visible to other processes)",
    ),
):
    """Extract metadata from Teradata and render HTML artefacts."""
    _validate_artefact(artefact)

    try:
        output.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _abort(f"Cannot create output directory '{output}':\n\n  {exc}")

    typer.echo(f"\ndata-product-browser {__version__} — connecting to Teradata…")
    conn = _connect(td_host, td_user, td_password)

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
    product: str = typer.Argument(..., help="Registry product name"),
    output: Path = typer.Option(
        Path("data.json"),
        "--output",
        "-o",
        help=(
            "Path to write the JSON snapshot. Pass a file (e.g. snap.json) or "
            "a directory — when a directory, '<product>.json' is written inside."
        ),
    ),
    lookback: int = typer.Option(90, "--lookback", help="Observability lookback in days"),
    td_host: str = typer.Option(None, "--td-host", help="Teradata host (overrides TD_HOST)"),
    td_user: str = typer.Option(None, "--td-user", help="Teradata username (overrides TD_USER)"),
    td_password: str = typer.Option(
        None,
        "--td-password",
        help="Teradata password (overrides TD_PASSWORD; may be visible to other processes)",
    ),
):
    """Dump the raw DataProduct snapshot to JSON (useful for offline rendering/debugging)."""
    typer.echo("\nConnecting to Teradata…")
    conn = _connect(td_host, td_user, td_password)

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

    # Treat an existing directory (or a path ending in a separator) as a
    # folder to drop '<product>.json' into. This matches `generate`'s
    # --output behaviour so 'serve / dump / generate' stay consistent.
    if output.is_dir() or str(output).endswith(("/", "\\")):
        safe = re.sub(r"[^\w.-]+", "_", product).strip("_") or "data"
        output = output / f"{safe}.json"

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


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Address to bind the web server to"),
    port: int = typer.Option(8080, "--port", "-p", help="Port to listen on"),
    ttl: int = typer.Option(300, "--ttl", help="Metadata cache lifetime in seconds"),
    registry_db: str = typer.Option(
        None,
        "--registry-db",
        help=(
            "Governance registry location (overrides TDP_REGISTRY_DB). "
            "Bare database name uses the default table; pass 'db.table' to "
            "override the table too (e.g. MyDb.another_data_product_registry)."
        ),
    ),
    td_host: str = typer.Option(None, "--td-host", help="Teradata host (overrides TD_HOST)"),
    td_user: str = typer.Option(None, "--td-user", help="Teradata username (overrides TD_USER)"),
    td_password: str = typer.Option(
        None,
        "--td-password",
        help="Teradata password (overrides TD_PASSWORD; may be visible to other processes)",
    ),
):
    """Run the interactive Data Product Browser web server.

    Resolves Teradata credentials once at startup, then serves a browsable UI
    that reads metadata live (cached) on each request. No AI client required.

    Note: --host/--port bind the web server; the Teradata connection is set with
    --td-host/--td-user/--td-password (or TD_HOST/TD_USER/TD_PASSWORD).
    """
    # Resolve credentials first so a missing host/user fails fast with clear
    # guidance, before importing the database driver or web server.
    td_host, td_user = _resolve_host_user(td_host, td_user)
    password = _get_password(td_host, td_user, td_password)

    import teradatasql
    import uvicorn

    from .server.app import create_app
    from .server.service import DataProductService

    typer.echo(f"Connecting as {td_user}@{td_host} (registry: {registry_db or 'default'})…")

    def connection_factory():
        return teradatasql.connect(host=td_host, user=td_user, password=password)

    # Fail fast: verify credentials before starting the server.
    try:
        connection_factory().close()
    except Exception as exc:
        _handle_connection_error(exc, td_host)

    service = DataProductService(connection_factory, registry_db=registry_db, ttl_seconds=ttl)
    typer.echo(f"\nData Product Browser → http://{host}:{port}  (Ctrl+C to stop)\n")
    uvicorn.run(create_app(service), host=host, port=port, log_level="warning")


def main() -> None:
    app()
