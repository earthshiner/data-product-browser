"""FastAPI application serving the Data Product Browser.

Routes are read-only. The API returns the same ``DataProduct`` JSON shape that
the CLI ``dump`` command produces, so the static frontend and offline snapshots
share one contract.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ..exceptions import DataProductError
from .service import DataProductService

_STATIC_DIR = Path(__file__).parent / "static"


def create_app(service: DataProductService) -> FastAPI:
    """Build the FastAPI app wired to a metadata service."""
    app = FastAPI(
        title="Data Product Browser",
        description="Browse AI-Native Data Product metadata served live from Teradata.",
        version="1.0",
    )

    @app.get("/api/products")
    def list_products() -> dict:
        """List deployed data product names."""
        try:
            return {"products": service.list_products()}
        except DataProductError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Teradata error: {exc}") from None

    @app.get("/api/products/{product_name}")
    def get_product(
        product_name: str,
        lookback: int = Query(90, ge=1, le=3650, description="Observability window in days"),
        refresh: bool = Query(False, description="Bypass the cache and re-collect"),
    ) -> JSONResponse:
        """Return the full metadata snapshot for one data product."""
        try:
            dp, warnings = service.get(product_name, lookback_days=lookback, refresh=refresh)
        except DataProductError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Teradata error: {exc}") from None

        return JSONResponse({"data_product": dp.model_dump(mode="json"), "warnings": warnings})

    # Mounted last so the API routes above take precedence over the SPA shell.
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")

    return app
