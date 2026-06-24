"""Configuration for data product discovery.

The governance registry location varies per Teradata system, so it is
configurable. Both the database and the table can be overridden separately.

Resolution order (highest precedence first):

  Database:
    1. ``--registry-db`` CLI argument (bare or qualified ``db.table``)
    2. ``TDP_REGISTRY_DB`` env var or ``.env`` line (bare or qualified)
    3. :data:`DEFAULT_REGISTRY_DB`

  Table:
    1. ``--registry-db`` CLI argument, table part (when qualified ``db.table``)
    2. ``TDP_REGISTRY_TABLE`` env var or ``.env`` line
    3. ``TDP_REGISTRY_DB`` env var, table part (when qualified)
    4. :data:`DEFAULT_REGISTRY_TABLE`
"""

from __future__ import annotations

import os

# Standard governance registry location; override per system.
DEFAULT_REGISTRY_DB = "DataProductsMaster_GOV_BUS_V"
DEFAULT_REGISTRY_TABLE = "active_data_product_registry"

_ENV_REGISTRY_DB = "TDP_REGISTRY_DB"
_ENV_REGISTRY_TABLE = "TDP_REGISTRY_TABLE"


def _split(value: str | None) -> tuple[str | None, str | None]:
    """Split ``'db.table'`` into ``(db, table)``; bare returns ``(bare, None)``.

    Returns ``(None, None)`` for empty input. Teradata identifiers cannot
    contain a dot, so the split is unambiguous.
    """
    if not value:
        return None, None
    if "." in value:
        d, _, t = value.partition(".")
        return (d.strip() or None), (t.strip() or None)
    return (value.strip() or None), None


def resolve_registry_db(explicit: str | None = None) -> str:
    """Return the configured registry location string (possibly ``db.table``).

    Kept for backwards compatibility. Most callers should use
    :func:`resolve_registry_target` to get the database and table separately.
    """
    return explicit or os.environ.get(_ENV_REGISTRY_DB) or DEFAULT_REGISTRY_DB


def resolve_registry_target(explicit: str | None = None) -> tuple[str, str]:
    """Return ``(database, table)`` for the governance registry.

    Resolution order is documented at the top of this module. The CLI value
    wins for both parts; failing that, ``TDP_REGISTRY_TABLE`` is consulted
    before falling back to the ``.table`` part of ``TDP_REGISTRY_DB``.
    """
    cli_db, cli_table = _split(explicit)
    env_db, env_db_table = _split(os.environ.get(_ENV_REGISTRY_DB))
    env_table = os.environ.get(_ENV_REGISTRY_TABLE)
    env_table = env_table.strip() if env_table else None

    db = cli_db or env_db or DEFAULT_REGISTRY_DB
    table = cli_table or env_table or env_db_table or DEFAULT_REGISTRY_TABLE
    return db, table
