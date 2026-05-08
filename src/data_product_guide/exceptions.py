"""Friendly exceptions raised by the collector and CLI.

All errors that a user might encounter during normal operation are represented
here so the CLI can print a clean, actionable message without a traceback.
"""

from __future__ import annotations

import re


class DataProductError(Exception):
    """Base class for all user-facing errors."""


class AccessDeniedError(DataProductError):
    """The connected user lacks SELECT on a required object."""

    def __init__(self, object_name: str, user: str, product_name: str) -> None:
        self.object_name = object_name
        self.user = user
        self.product_name = product_name

    def __str__(self) -> str:
        dbs = [
            f"{self.product_name}_Semantic",
            f"{self.product_name}_Memory",
            f"{self.product_name}_Observability",
        ]
        grants = "\n".join(f"    GRANT SELECT ON {db} TO {self.user};" for db in dbs)
        return (
            f"No SELECT access to '{self.object_name}'.\n\n"
            f"  Ask your Teradata DBA to grant access to the data product databases:\n\n"
            f"{grants}"
        )


class ObjectNotFoundError(DataProductError):
    """A required table or view does not exist."""

    def __init__(self, object_name: str, product_name: str) -> None:
        self.object_name = object_name
        self.product_name = product_name

    def __str__(self) -> str:
        return (
            f"Object '{self.object_name}' does not exist.\n\n"
            f"  Check that the product name is correct and the data product\n"
            f"  databases have been fully deployed:\n\n"
            f"    data-product-guide generate {self.product_name}   ← verify this spelling"
        )


class LoginError(DataProductError):
    """Username or password rejected by Teradata."""

    def __str__(self) -> str:
        return (
            "Login failed — the username or password is incorrect.\n\n"
            "  Re-store your password:\n\n"
            "    data-product-guide store-password"
        )


class ConnectionError(DataProductError):
    """Cannot reach the Teradata host."""

    def __init__(self, host: str) -> None:
        self.host = host

    def __str__(self) -> str:
        return (
            f"Cannot connect to Teradata at '{self.host}'.\n\n"
            f"  Check that TD_HOST in your .env is correct and the host is reachable."
        )


class SnapshotNotFoundError(DataProductError):
    """The JSON snapshot file does not exist."""

    def __init__(self, path: str) -> None:
        self.path = path

    def __str__(self) -> str:
        return (
            f"Snapshot file not found: {self.path}\n\n"
            f"  Create one first:\n\n"
            f"    data-product-guide dump <product> --output {self.path}"
        )


class InvalidSnapshotError(DataProductError):
    """The JSON snapshot file is malformed or from an incompatible version."""

    def __init__(self, path: str, detail: str) -> None:
        self.path = path
        self.detail = detail

    def __str__(self) -> str:
        return (
            f"Snapshot file '{self.path}' is invalid or corrupted.\n\n"
            f"  Detail: {self.detail}\n\n"
            f"  Re-generate a fresh snapshot:\n\n"
            f"    data-product-guide dump <product> --output {self.path}"
        )


class InvalidArtefactError(DataProductError):
    """An unrecognised --artefact value was supplied."""

    def __init__(self, value: str) -> None:
        self.value = value

    def __str__(self) -> str:
        return (
            f"Unknown artefact '{self.value}'.\n\n"
            f"  Valid choices: all, cookbook, ops"
        )


# ---------------------------------------------------------------------------
# Parser — converts raw teradatasql OperationalError into a typed exception
# ---------------------------------------------------------------------------

_TD_ERROR_RE = re.compile(r"\[Error\s+(\d+)\]")
_OBJECT_RE = re.compile(
    r"(?:access to|Object)\s+'?([A-Za-z0-9_.]+)'?",
    re.IGNORECASE,
)
# 5315 error text: "... access to DBC.TablesV.ColumnName."
# Match only DatabaseName.TableName — stop before a third dot or trailing period.
_OWNER_OBJ_RE = re.compile(
    r"SELECT WITH GRANT OPTION access to ([A-Za-z0-9_]+\.[A-Za-z0-9_]+)",
    re.IGNORECASE,
)


def parse_teradata_error(
    exc: Exception,
    product_name: str,
    user: str,
    host: str,
    query_context: str = "",
    view_owner: str | None = None,
) -> DataProductError:
    """Convert a teradatasql OperationalError into a DataProductError.

    Args:
        query_context: Fully-qualified name of the object being queried when the
                       error occurred, e.g. ``"MortgagePlatform_Semantic.lineage_graph"``.
        view_owner:    If already resolved, the CreatorName of the failing view.
                       When provided, the GRANT statement uses the real owner name
                       instead of the ``<view_owner>`` placeholder.
    """
    msg = str(exc)

    code_match = _TD_ERROR_RE.search(msg)
    code = int(code_match.group(1)) if code_match else 0

    obj_match = _OBJECT_RE.search(msg)
    obj = obj_match.group(1) if obj_match else "unknown object"

    context_line = (
        f"\n\n  Failed while querying: {query_context}" if query_context else ""
    )

    if code == 3523:
        return AccessDeniedError(obj, user, product_name)

    if code == 3807:
        return ObjectNotFoundError(obj, product_name)

    if code in (8017, 1017):
        return LoginError()

    if code == 5315:
        owner_match = _OWNER_OBJ_RE.search(msg)
        dbc_obj = owner_match.group(1) if owner_match else "DBC.TablesV"
        view_ref = query_context or "unknown view"
        grantee = view_owner if view_owner else "<view_owner>"
        grant_line = f"    GRANT SELECT ON {dbc_obj} TO {grantee} WITH GRANT OPTION;"
        owner_note = (
            f"  View owner: {view_owner}"
            if view_owner
            else (
                f"  To find the view owner:\n\n"
                f"    SELECT CreatorName FROM DBC.TablesV\n"
                f"    WHERE DatabaseName = '{product_name}_Semantic'\n"
                f"      AND TableName = 'lineage_graph';"
            )
        )
        return DataProductError(
            f"View permission error on '{view_ref}'.{context_line}\n\n"
            f"  The view owner does not have SELECT WITH GRANT OPTION on '{dbc_obj}'.\n\n"
            f"  Ask your Teradata DBA to run:\n\n"
            f"{grant_line}\n\n"
            f"{owner_note}"
        )

    if "unable to connect" in msg.lower() or "connection refused" in msg.lower():
        return ConnectionError(host)

    # Unknown error — include the query context so the user knows where it failed
    first_line = msg.splitlines()[0]
    return DataProductError(
        f"Teradata error while querying '{product_name}'.{context_line}\n\n"
        f"  {first_line}"
    )
