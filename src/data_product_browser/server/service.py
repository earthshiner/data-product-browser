"""Cached metadata service backing the web server.

``collect()`` runs ~18 queries against three live databases, so hitting it on
every page click would be far too slow. This module wraps it with a small
per-product TTL cache and a refresh override, and discovers deployed products
by scanning ``DBC.DatabasesV`` for ``*_Semantic`` databases.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from ..collector import collect
from ..models import DataProduct

# Suffix that identifies a data product's Semantic database.
_SEMANTIC_SUFFIX = "_Semantic"

ConnectionFactory = Callable[[], Any]


class DataProductService:
    """Serves cached DataProduct snapshots from a live Teradata connection.

    Args:
        connection_factory: Zero-arg callable returning a fresh, open
            teradatasql connection. A new connection is opened and closed per
            request so connections are never shared across threads.
        ttl_seconds: How long a cached snapshot stays fresh before the next
            request triggers a re-collect.
    """

    def __init__(self, connection_factory: ConnectionFactory, ttl_seconds: int = 300) -> None:
        self._connect = connection_factory
        self._ttl = ttl_seconds
        # product_name -> (expires_at, DataProduct, warnings)
        self._cache: dict[str, tuple[float, DataProduct, list[str]]] = {}

    def list_products(self) -> list[str]:
        """Return the names of all deployed data products, sorted.

        A product is detected by the presence of a ``<name>_Semantic`` database.
        """
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT DatabaseName FROM DBC.DatabasesV "
                    "WHERE DatabaseName LIKE '%' || ? "
                    "ORDER BY DatabaseName",
                    [_SEMANTIC_SUFFIX],
                )
                names = [str(row[0]).strip() for row in cur.fetchall()]
        finally:
            conn.close()

        return [n[: -len(_SEMANTIC_SUFFIX)] for n in names if n.endswith(_SEMANTIC_SUFFIX)]

    def get(
        self,
        product_name: str,
        lookback_days: int = 90,
        refresh: bool = False,
    ) -> tuple[DataProduct, list[str]]:
        """Return a (cached) DataProduct snapshot plus any collection warnings.

        Args:
            product_name: Data product name prefix, e.g. ``MortgagePlatform``.
            lookback_days: Observability window passed through to ``collect()``.
            refresh: When True, bypass the cache and re-collect.
        """
        now = time.time()
        cached = self._cache.get(product_name)
        if not refresh and cached is not None and cached[0] > now:
            return cached[1], cached[2]

        conn = self._connect()
        try:
            dp, warnings = collect(product_name, conn, lookback_days=lookback_days)
        finally:
            conn.close()

        self._cache[product_name] = (now + self._ttl, dp, warnings)
        return dp, warnings
