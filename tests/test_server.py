"""Tests for the Data Product Browser web server and metadata service."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from data_product_browser.models import ColumnMetadata, DataProduct, EntityMetadata
from data_product_browser.server.app import create_app
from data_product_browser.server.service import DataProductService


def _sample_product(name: str = "MortgagePlatform") -> DataProduct:
    return DataProduct(
        product_name=name,
        generated_dts=datetime.now(timezone.utc),
        entities=[
            EntityMetadata(
                entity_metadata_key=1,
                module_name="Domain",
                entity_name="Loan",
                database_name=f"{name}_Domain",
                table_name="loan",
            )
        ],
        columns=[
            ColumnMetadata(
                column_metadata_key=1,
                database_name=f"{name}_Domain",
                table_name="loan",
                column_name="loan_id",
                data_type="INTEGER",
                is_pii=0,
                is_required=1,
            )
        ],
    )


class _StubService:
    """Stand-in for DataProductService that needs no Teradata connection."""

    def list_products(self) -> list[str]:
        return ["MortgagePlatform"]

    def get(self, name: str, lookback_days: int = 90, refresh: bool = False):
        return _sample_product(name), ["warn: lineage_graph skipped"]


def _client() -> TestClient:
    return TestClient(create_app(_StubService()))


def test_list_products():
    resp = _client().get("/api/products")
    assert resp.status_code == 200
    assert resp.json() == {"products": ["MortgagePlatform"]}


def test_get_product_shape():
    resp = _client().get("/api/products/MortgagePlatform")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"data_product", "warnings"}
    assert body["data_product"]["entities"][0]["entity_name"] == "Loan"
    assert body["warnings"] == ["warn: lineage_graph skipped"]


def test_static_shell_served():
    client = _client()
    assert client.get("/").status_code == 200
    assert client.get("/app.js").status_code == 200


# --- service cache behaviour -------------------------------------------------


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.sql = sql

    def fetchall(self):
        return self._rows


class _FakeConnection:
    def __init__(self, rows):
        self._rows = rows
        self.closed = False

    def cursor(self):
        return _FakeCursor(self._rows)

    def close(self):
        self.closed = True


def test_list_products_strips_semantic_suffix():
    conn = _FakeConnection([("MortgagePlatform_Semantic",), ("Retail_Semantic",)])
    service = DataProductService(lambda: conn)
    assert service.list_products() == ["MortgagePlatform", "Retail"]
    assert conn.closed is True


def test_get_caches_within_ttl(monkeypatch):
    calls = {"n": 0}

    def fake_collect(name, connection, lookback_days=90):
        calls["n"] += 1
        return _sample_product(name), []

    monkeypatch.setattr("data_product_browser.server.service.collect", fake_collect)
    service = DataProductService(lambda: _FakeConnection([]), ttl_seconds=300)

    service.get("MortgagePlatform")
    service.get("MortgagePlatform")
    assert calls["n"] == 1  # second call served from cache

    service.get("MortgagePlatform", refresh=True)
    assert calls["n"] == 2  # refresh bypasses cache
