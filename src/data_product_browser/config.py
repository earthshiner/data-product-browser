"""Configuration for data product discovery.

The governance registry location varies per Teradata system, so it is
configurable. Resolution order: explicit argument > ``TDP_REGISTRY_DB`` env var
> the standard default.

The configured value may be either a bare database name (in which case the
table defaults to ``active_data_product_registry``) or a fully-qualified
``database.table`` such as ``MyDb.another_data_product_registry`` — the
collector splits on the dot.
"""

from __future__ import annotations

import os

# Standard governance registry location; override per system.
DEFAULT_REGISTRY_DB = "DataProductsMaster_GOV_BUS_V"
DEFAULT_REGISTRY_TABLE = "active_data_product_registry"

_ENV_REGISTRY_DB = "TDP_REGISTRY_DB"


def resolve_registry_db(explicit: str | None = None) -> str:
    """Return the configured registry location string (possibly ``db.table``).

    Use :func:`resolve_registry_target` when you need the database and table
    parts separately.
    """
    return explicit or os.environ.get(_ENV_REGISTRY_DB) or DEFAULT_REGISTRY_DB


def resolve_registry_target(explicit: str | None = None) -> tuple[str, str]:
    """Return ``(database, table)`` for the governance registry.

    Accepts a bare database name (uses :data:`DEFAULT_REGISTRY_TABLE`) or a
    fully-qualified ``database.table`` (split on the first dot). Teradata
    identifiers cannot contain a dot, so the split is unambiguous.
    """
    raw = resolve_registry_db(explicit)
    if "." in raw:
        db, _, table = raw.partition(".")
        return db.strip(), table.strip()
    return raw, DEFAULT_REGISTRY_TABLE
