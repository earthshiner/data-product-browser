"""Tests for the Data Product Browser web server and metadata service."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from data_product_browser.models import ColumnMetadata, DataProduct, EntityMetadata
from data_product_browser.server.app import create_app
from data_product_browser.server.service import DataProductService


def _sample_product(name: str = "CallCentre Data Product") -> DataProduct:
    return DataProduct(
        product_name=name,
        generated_dts=datetime.now(timezone.utc),
        entities=[
            EntityMetadata(
                entity_metadata_id=1,
                module_name="Domain",
                entity_name="Call",
                database_name="CallCentre_DOM_STD_V",
                table_name="Call_Current",
            )
        ],
        columns=[
            ColumnMetadata(
                column_metadata_id=1,
                database_name="CallCentre_DOM_STD_V",
                table_name="Call_Current",
                column_name="call_id",
                data_type="BIGINT",
                is_pii=0,
                is_required=1,
            )
        ],
    )


class _StubService:
    """Stand-in for DataProductService that needs no Teradata connection."""

    def list_products(self) -> list[dict]:
        return [
            {
                "product_name": "CallCentre Data Product",
                "product_version": "1.0.0",
                "product_status": "ACTIVE",
            }
        ]

    def get(self, name: str, lookback_days: int = 90, refresh: bool = False):
        return _sample_product(name), ["warn: trust_engine_latest skipped"]


def _client() -> TestClient:
    return TestClient(create_app(_StubService()))


def test_list_products():
    resp = _client().get("/api/products")
    assert resp.status_code == 200
    body = resp.json()
    assert body["products"][0]["product_name"] == "CallCentre Data Product"


def test_get_product_shape():
    resp = _client().get("/api/products/CallCentre%20Data%20Product")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"data_product", "warnings"}
    assert body["data_product"]["entities"][0]["entity_name"] == "Call"
    assert body["warnings"] == ["warn: trust_engine_latest skipped"]


def test_static_shell_served():
    client = _client()
    assert client.get("/").status_code == 200
    assert client.get("/app.js").status_code == 200


# --- service cache + discovery ----------------------------------------------


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


def test_list_products_reads_registry(monkeypatch):
    captured = {}

    def fake_discover(conn, registry_db=None):
        captured["registry_db"] = registry_db
        from data_product_browser.models import RegistryEntry

        return [RegistryEntry(product_name="CallCentre Data Product", product_status="ACTIVE")]

    monkeypatch.setattr("data_product_browser.server.service.discover_products", fake_discover)
    conn = _FakeConnection([])
    service = DataProductService(lambda: conn, registry_db="MyReg_GOV_BUS_V")
    products = service.list_products()
    assert products[0]["product_name"] == "CallCentre Data Product"
    assert captured["registry_db"] == "MyReg_GOV_BUS_V"
    assert conn.closed is True


def test_get_caches_within_ttl(monkeypatch):
    calls = {"n": 0}

    def fake_collect(name, connection, registry_db=None, lookback_days=90):
        calls["n"] += 1
        return _sample_product(name), []

    monkeypatch.setattr("data_product_browser.server.service.collect", fake_collect)
    service = DataProductService(lambda: _FakeConnection([]), ttl_seconds=300)

    service.get("CallCentre Data Product")
    service.get("CallCentre Data Product")
    assert calls["n"] == 1  # second call served from cache

    service.get("CallCentre Data Product", refresh=True)
    assert calls["n"] == 2  # refresh bypasses cache
