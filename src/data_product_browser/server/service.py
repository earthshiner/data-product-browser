"""Cached metadata service backing the web server.

``collect()`` runs many queries across several live databases, so hitting it on
every page click would be too slow. This module wraps it with a small per-product
TTL cache and a refresh override, and discovers products via the governance
registry.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from ..collector import collect, discover_products
from ..config import resolve_registry_db
from ..models import DataProduct
from ..renderers.sql_highlight import highlight_sql

ConnectionFactory = Callable[[], Any]


class DataProductService:
    """Serves cached DataProduct snapshots from a live Teradata connection.

    Args:
        connection_factory: Zero-arg callable returning a fresh, open
            teradatasql connection. A new connection is opened and closed per
            request so connections are never shared across threads.
        registry_db: Governance registry database (configurable per system).
        ttl_seconds: How long a cached snapshot stays fresh before the next
            request triggers a re-collect.
    """

    def __init__(
        self,
        connection_factory: ConnectionFactory,
        registry_db: str | None = None,
        ttl_seconds: int = 300,
    ) -> None:
        self._connect = connection_factory
        self._registry_db = resolve_registry_db(registry_db)
        self._ttl = ttl_seconds
        # product_name -> (expires_at, DataProduct, warnings)
        self._cache: dict[str, tuple[float, DataProduct, list[str]]] = {}

    def list_products(self) -> list[dict]:
        """Return active products from the registry as lightweight dicts."""
        conn = self._connect()
        try:
            entries = discover_products(conn, self._registry_db)
        finally:
            conn.close()
        return [
            {
                "product_name": e.product_name,
                "product_version": e.product_version,
                "product_status": e.product_status,
            }
            for e in entries
        ]

    def get(
        self,
        product_name: str,
        lookback_days: int = 90,
        refresh: bool = False,
    ) -> tuple[DataProduct, list[str]]:
        """Return a (cached) DataProduct snapshot plus any collection warnings."""
        now = time.time()
        cached = self._cache.get(product_name)
        if not refresh and cached is not None and cached[0] > now:
            return cached[1], cached[2]

        conn = self._connect()
        try:
            dp, warnings = collect(
                product_name,
                conn,
                registry_db=self._registry_db,
                lookback_days=lookback_days,
            )
        finally:
            conn.close()

        self._cache[product_name] = (now + self._ttl, dp, warnings)
        return dp, warnings

    def show_ddl(self, database: str, table: str) -> dict:
        """Run ``SHOW TABLE <db>.<table>`` and return raw + highlighted text.

        Identifiers must be validated by the caller — this method assumes the
        names are already safe to interpolate into SQL.
        """
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(f"SHOW TABLE {database}.{table}")
                rows = cur.fetchall()
        finally:
            conn.close()
        ddl = "\n".join("" if r[0] is None else str(r[0]) for r in rows).strip()
        return {"ddl": ddl, "ddl_html": highlight_sql(ddl)}
