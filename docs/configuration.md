# Configuration

Every command takes the same four pieces of configuration: Teradata host, user, password, and the governance registry database. Each can come from a command-line option, an environment variable, or a `.env` file in the current directory. The password additionally supports the OS keyring.

## Resolution order

For each setting, the first source that yields a value wins:

| Setting | Order |
|---|---|
| Host | `--td-host` → `TD_HOST` (env or `.env`) |
| User | `--td-user` → `TD_USER` (env or `.env`) |
| Password | `--td-password` → `TD_PASSWORD` (env or `.env`) → OS keyring → interactive prompt (TTY only) |
| Registry database | `--registry-db` (or `db` part if qualified) → `TDP_REGISTRY_DB` (or `db` part if qualified) → built-in default |
| Registry table | `--registry-db` `.table` part (if qualified) → `TDP_REGISTRY_TABLE` (env or `.env`) → `TDP_REGISTRY_DB` `.table` part (if qualified) → built-in default |

Missing host or user aborts immediately with a cross-shell snippet showing how to set the environment variable in PowerShell, cmd.exe, and bash/zsh. Missing password with no TTY (e.g. piped output, service) aborts with the same kind of guidance; with a TTY it prompts interactively via `getpass`.

## Setting credentials for one session

```powershell
# PowerShell
$env:TD_HOST = "your-system.teradata.com"
$env:TD_USER = "you"
$env:TD_PASSWORD = "your-password"
```

```cmd
:: Windows cmd.exe
set TD_HOST=your-system.teradata.com
set TD_USER=you
set TD_PASSWORD=your-password
```

```bash
# bash / zsh
export TD_HOST="your-system.teradata.com"
export TD_USER="you"
export TD_PASSWORD="your-password"
```

## Persisting via `.env`

The CLI calls `python-dotenv`'s `load_dotenv(override=True)` before resolving host/user, so a `.env` file in the working directory is read on every invocation. Copy `.env.example` and fill in the values you want to persist:

```
TD_HOST=your-system.teradata.com
TD_USER=you
TD_PASSWORD=your-password         # optional — keyring is preferred
TDP_REGISTRY_DB=GOV_REGISTRY      # optional — overrides the built-in default
```

`.env` is gitignored. **Do not commit it.**

## Persisting the password to the keyring

`data-product-browser store-password` prompts for host, user, and password and writes them via the `keyring` package — Windows Credential Manager, macOS Keychain, or freedesktop secret-service on Linux. This is the recommended way to persist a password because nothing lands on disk in plaintext.

```bash
uv run data-product-browser store-password
```

The keyring entry is keyed by `<user>@<host>` so multiple credentials can coexist. Use a session-only `$env:TD_PASSWORD` to override the keyring for one run.

A password on the command line (`--td-password`) is supported but visible to anything that can inspect process arguments — prefer the keyring or an environment variable.

## Governance registry

The collector starts from one well-known table listing every data product with its module databases. The location is resolved by `data_product_browser.config.resolve_registry_target()`:

1. Explicit `--registry-db` / function argument.
2. `TDP_REGISTRY_DB` env var (or `.env`).
3. Built-in default (`DataProductsMaster_GOV_BUS_V.active_data_product_registry`).

The configured value may be either a **bare database name** (uses the default table `active_data_product_registry`) or a **fully-qualified `database.table`** — split on the first dot (Teradata identifiers cannot contain a dot).

```powershell
# Just override the database; use the default table:
$env:TDP_REGISTRY_DB = "GOV_REGISTRY_NONPROD"

# Override both database AND table in one value:
$env:TDP_REGISTRY_DB = "MyDb.another_data_product_registry"

# Or keep them separate (TDP_REGISTRY_TABLE wins over the table-part
# of TDP_REGISTRY_DB):
$env:TDP_REGISTRY_DB    = "MyDb"
$env:TDP_REGISTRY_TABLE = "another_data_product_registry"
```

Equivalent `.env`:

```
TDP_REGISTRY_DB=MyDb
TDP_REGISTRY_TABLE=another_data_product_registry
```

Same syntax works on the CLI:

```bash
uv run data-product-browser serve --registry-db MyDb.another_data_product_registry
```

## Web-server-only options

`data-product-browser serve` adds three:

| Option | Default | Notes |
|---|---|---|
| `--host` | `127.0.0.1` | Address the FastAPI app binds to. Use `0.0.0.0` to expose on the LAN. |
| `--port` / `-p` | `8080` | TCP port. |
| `--ttl` | `300` | Seconds a `DataProduct` snapshot stays cached server-side. Lower for live development; higher for sharing. |

The browser UI passes `?refresh=true` to `/api/products/<name>` when the refresh checkbox is ticked, bypassing the cache for that one fetch.

## View-database vs base-table reads

Every `RegistryEntry` carries both forms — e.g. `semantic_database` and `semantic_view_database`. The collector prefers the view-database value when present (`sem = entry.semantic_view_database or entry.semantic_database`), honouring the standard object-placement convention that consumers read from the view layer.

The DDL tab and the uncatalogued-table check still hit the **base** database (via `SHOW TABLE <db>.<table>` and `DBC.TablesV` respectively), since both need physical structure. Make sure the connecting user has `SELECT` on `DBC.TablesV` if you want the coverage check to run.

## Permissions checklist

The connecting user needs:

- `SELECT` on `<registry_db>.active_data_product_registry`
- `SELECT` on every module catalogue table the registry points to (Semantic, Memory, Observability, …)
- `SELECT` on `DBC.TablesV` (for the uncatalogued-table coverage check — soft-degrades to a warning if missing)
- `SHOW` privilege on every table the user might open in the **DDL** tab

The browser will surface missing-table or permission errors as `⚠` warnings in the banner rather than aborting the whole collection.
