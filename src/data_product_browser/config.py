"""Configuration for data product discovery.

The governance registry database name varies per Teradata system, so it is
configurable. Resolution order: explicit argument > ``TDP_REGISTRY_DB`` env var
> the standard default.
"""

from __future__ import annotations

import os

# Standard governance registry database name; override per system.
DEFAULT_REGISTRY_DB = "DataProductsMaster_GOV_BUS_V"

_ENV_REGISTRY_DB = "TDP_REGISTRY_DB"


def resolve_registry_db(explicit: str | None = None) -> str:
    """Return the registry database to use, honouring override precedence."""
    return explicit or os.environ.get(_ENV_REGISTRY_DB) or DEFAULT_REGISTRY_DB
