"""Column-level ERD SVG generator.

Produces a table-per-box diagram matching the style of the existing
MortgagePlatform_Cookbook.html: navy headers, alternating column rows,
NOT NULL badges, PII/SENSITIVE flags, join-column connectors.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field

from ..models import ColumnMetadata, EntityMetadata, TableRelationship

# Layout constants
_BOX_W = 300
_HDR_H = 28  # table header row height
_COL_H = 24  # per-column row height
_GAP_X = 60  # horizontal gap between tables
_TOP_Y = 40  # y offset for first table
_LEGEND_GAP = 28  # gap below last table before legend
_FONT = "Inter, -apple-system, sans-serif"
_MONO = "'JetBrains Mono', Menlo, monospace"
_COLORS = ["#00233C", "#FF5F02", "#4A90E2", "#16a34a", "#7c3aed"]


@dataclass
class _ColRow:
    name: str
    data_type: str
    is_required: bool
    is_pii: bool
    is_sensitive: bool
    is_join: bool
    is_key: bool


@dataclass
class _Table:
    short_name: str
    full_name: str
    color: str
    cols: list[_ColRow] = field(default_factory=list)

    @property
    def box_h(self) -> int:
        return _HDR_H + len(self.cols) * _COL_H

    def col_y_centre(self, col_name: str, table_top_y: int) -> int | None:
        col_upper = col_name.upper()
        for i, c in enumerate(self.cols):
            if c.name.upper() == col_upper:
                return table_top_y + _HDR_H + i * _COL_H + _COL_H // 2
        return None


def _short(fq: str) -> str:
    return fq.split(".")[-1] if "." in fq else fq


def _build_tables(
    table_names: list[str],
    columns: list[ColumnMetadata],
    relationships: list[TableRelationship],
    entities: list[EntityMetadata],
) -> list[_Table]:
    # All lookups are case-insensitive — Teradata returns names in varying case
    join_cols: dict[str, set[str]] = {}
    for r in relationships:
        if r.is_active:
            join_cols.setdefault(r.from_table.upper(), set()).add(r.from_column.upper())
            join_cols.setdefault(r.to_table.upper(), set()).add(r.to_column.upper())

    natural_keys: dict[str, set[str]] = {}
    for e in entities:
        if e.natural_key_column:
            natural_keys.setdefault(e.table_name.upper(), set()).add(e.natural_key_column.upper())

    tables = []
    for i, tname in enumerate(table_names):
        short = _short(tname)
        cols_for = [c for c in columns if c.table_name.upper() == short.upper()]
        if not cols_for:
            continue

        rows = [
            _ColRow(
                name=c.column_name,
                data_type=c.data_type or "",
                is_required=bool(c.is_required),
                is_pii=bool(c.is_pii),
                is_sensitive=bool(c.is_sensitive),
                is_join=c.column_name.upper() in join_cols.get(short.upper(), set()),
                is_key=c.column_name.upper() in natural_keys.get(short.upper(), set()),
            )
            for c in cols_for
        ]

        tables.append(
            _Table(
                short_name=short,
                full_name=tname,
                color=_COLORS[i % len(_COLORS)],
                cols=rows,
            )
        )

    return tables


def _render_table(t: _Table, x: int, y: int, parts: list[str]) -> None:
    h = t.box_h
    esc = html.escape

    # Outer box
    parts.append(
        f'<rect x="{x}" y="{y}" width="{_BOX_W}" height="{h}" rx="4" '
        f'fill="#FFFFFF" stroke="#e2e4e8" stroke-width="1"/>'
    )
    # Header
    parts.append(
        f'<rect x="{x}" y="{y}" width="{_BOX_W}" height="{_HDR_H}" rx="4" fill="{t.color}"/>'
        f'<rect x="{x}" y="{y + _HDR_H - 4}" width="{_BOX_W}" height="4" fill="{t.color}"/>'
    )
    parts.append(
        f'<text x="{x + 10}" y="{y + 18}" font-family="{_FONT}" font-size="11" '
        f'font-weight="600" fill="#FFFFFF">{esc(t.short_name)}</text>'
    )

    # Column rows
    for idx, col in enumerate(t.cols):
        ry = y + _HDR_H + idx * _COL_H
        bg = "#f7f8fa" if idx % 2 == 0 else "#FFFFFF"
        cy = ry + _COL_H // 2 + 4  # text baseline

        parts.append(f'<rect x="{x}" y="{ry}" width="{_BOX_W}" height="{_COL_H}" fill="{bg}"/>')

        # PK/FK badge (text rect, no emoji — reliable across all browsers/SVG renderers)
        badge_x = x + 6
        name_x = x + 10
        if col.is_key:
            parts.append(
                f'<rect x="{badge_x}" y="{ry + 5}" width="16" height="13" rx="2" fill="#0d9488"/>'
                f'<text x="{badge_x + 8}" y="{ry + 15}" font-family="{_FONT}" font-size="7" '
                f'font-weight="700" fill="#FFFFFF" text-anchor="middle">PK</text>'
            )
            name_x = badge_x + 20
        elif col.is_join:
            parts.append(
                f'<rect x="{badge_x}" y="{ry + 5}" width="16" height="13" rx="2" fill="#FF5F02"/>'
                f'<text x="{badge_x + 8}" y="{ry + 15}" font-family="{_FONT}" font-size="7" '
                f'font-weight="700" fill="#FFFFFF" text-anchor="middle">FK</text>'
            )
            name_x = badge_x + 20

        name_color = "#FF5F02" if col.is_join else "#00233C"
        parts.append(
            f'<text x="{name_x}" y="{cy}" font-family="{_FONT}" font-size="10" '
            f'fill="{name_color}">{esc(col.name)}</text>'
        )

        # Data type (right-aligned, monospace)
        type_x = x + _BOX_W - 4
        parts.append(
            f'<text x="{type_x}" y="{cy}" font-family="{_MONO}" font-size="9" '
            f'fill="#FF5F02" text-anchor="end">{esc(col.data_type)}</text>'
        )

        # Attribute badges — stack left of the data type
        bx = x + 160
        if col.is_required:
            parts.append(
                f'<rect x="{bx}" y="{ry + 5}" width="18" height="13" rx="3" fill="#6b7280"/>'
                f'<text x="{bx + 9}" y="{ry + 15}" font-family="{_FONT}" font-size="8" '
                f'font-weight="700" fill="#FFFFFF" text-anchor="middle">NN</text>'
            )
            bx += 22
        if col.is_pii:
            parts.append(
                f'<rect x="{bx}" y="{ry + 5}" width="22" height="13" rx="3" fill="#dc2626"/>'
                f'<text x="{bx + 11}" y="{ry + 15}" font-family="{_FONT}" font-size="8" '
                f'font-weight="700" fill="#FFFFFF" text-anchor="middle">PII</text>'
            )
            bx += 26
        if col.is_sensitive:
            parts.append(
                f'<rect x="{bx}" y="{ry + 5}" width="30" height="13" rx="3" fill="#d97706"/>'
                f'<text x="{bx + 15}" y="{ry + 15}" font-family="{_FONT}" font-size="8" '
                f'font-weight="700" fill="#FFFFFF" text-anchor="middle">SENS</text>'
            )

    # Bottom separator
    parts.append(
        f'<line x1="{x}" y1="{y + h}" x2="{x + _BOX_W}" y2="{y + h}" '
        f'stroke="#e2e4e8" stroke-width="0.5"/>'
    )


def _render_connectors(
    tables: list[_Table],
    xs: list[int],
    relationships: list[TableRelationship],
    parts: list[str],
) -> None:
    # Case-insensitive lookup so Teradata mixed-case names always match
    table_index = {t.short_name.upper(): i for i, t in enumerate(tables)}
    drawn: set[tuple] = set()

    for r in relationships:
        if not r.is_active:
            continue
        ai = table_index.get(r.from_table.upper())
        bi = table_index.get(r.to_table.upper())
        if ai is None or bi is None or ai == bi:
            continue

        # Deduplicate — one edge per table pair
        edge_key = (min(ai, bi), max(ai, bi))
        if edge_key in drawn:
            continue
        drawn.add(edge_key)

        # Always draw left-to-right regardless of relationship direction
        if ai <= bi:
            li, ri = ai, bi
            from_col, to_col = r.from_column, r.to_column
        else:
            li, ri = bi, ai
            from_col, to_col = r.to_column, r.from_column

        lt = tables[li]
        rt = tables[ri]

        ly = lt.col_y_centre(from_col, _TOP_Y)
        ry_val = rt.col_y_centre(to_col, _TOP_Y)
        if ly is None or ry_val is None:
            continue

        x1 = xs[li] + _BOX_W
        x2 = xs[ri]
        dashed = ' stroke-dasharray="6,4"' if r.join_type.upper() != "INNER" else ""
        parts.append(
            f'<line x1="{x1}" y1="{ly}" x2="{x2}" y2="{ry_val}" '
            f'stroke="#FF5F02" stroke-width="1.5" marker-end="url(#erd-arrow)"{dashed}/>'
        )


def _render_legend(y: int, parts: list[str]) -> None:
    lx = 20
    # PK badge
    parts.append(
        f'<rect x="{lx}" y="{y - 10}" width="16" height="13" rx="2" fill="#0d9488"/>'
        f'<text x="{lx + 8}" y="{y}" font-family="{_FONT}" font-size="7" '
        f'font-weight="700" fill="#FFFFFF" text-anchor="middle">PK</text>'
    )
    lx += 22
    parts.append(
        f'<text x="{lx}" y="{y}" font-family="{_FONT}" font-size="9" fill="#6b7280">Natural key</text>'
    )
    lx += 76
    # FK badge
    parts.append(
        f'<rect x="{lx}" y="{y - 10}" width="16" height="13" rx="2" fill="#FF5F02"/>'
        f'<text x="{lx + 8}" y="{y}" font-family="{_FONT}" font-size="7" '
        f'font-weight="700" fill="#FFFFFF" text-anchor="middle">FK</text>'
    )
    lx += 22
    parts.append(
        f'<text x="{lx}" y="{y}" font-family="{_FONT}" font-size="9" fill="#6b7280">Join column  ·  </text>'
    )
    lx += 82
    parts.append(
        f'<rect x="{lx}" y="{y - 10}" width="18" height="13" rx="3" fill="#6b7280"/>'
        f'<text x="{lx + 9}" y="{y}" font-family="{_FONT}" font-size="8" '
        f'font-weight="700" fill="#FFFFFF" text-anchor="middle">NN</text>'
    )
    lx += 24
    parts.append(
        f'<text x="{lx}" y="{y}" font-family="{_FONT}" font-size="9" fill="#6b7280">=NOT NULL  ·  </text>'
    )
    lx += 78
    parts.append(
        f'<rect x="{lx}" y="{y - 10}" width="22" height="13" rx="3" fill="#dc2626"/>'
        f'<text x="{lx + 11}" y="{y}" font-family="{_FONT}" font-size="8" '
        f'font-weight="700" fill="#FFFFFF" text-anchor="middle">PII</text>'
    )
    lx += 28
    parts.append(
        f'<text x="{lx}" y="{y}" font-family="{_FONT}" font-size="9" fill="#6b7280">  ·  </text>'
    )
    lx += 22
    parts.append(
        f'<rect x="{lx}" y="{y - 10}" width="30" height="13" rx="3" fill="#d97706"/>'
        f'<text x="{lx + 15}" y="{y}" font-family="{_FONT}" font-size="8" '
        f'font-weight="700" fill="#FFFFFF" text-anchor="middle">SENS</text>'
    )
    lx += 36
    parts.append(
        f'<text x="{lx}" y="{y}" font-family="{_FONT}" font-size="9" fill="#6b7280">=Sensitive</text>'
    )


def make_column_erd(
    tables: list[str],
    columns: list[ColumnMetadata],
    relationships: list[TableRelationship],
    entities: list[EntityMetadata],
) -> str:
    """Return an inline SVG column-level ERD for the given table list."""
    built = _build_tables(tables, columns, relationships, entities)
    if not built:
        return ""

    n = len(built)
    total_w = n * _BOX_W + (n - 1) * _GAP_X + 40
    max_h = max(t.box_h for t in built)
    total_h = _TOP_Y + max_h + _LEGEND_GAP + 16

    xs = [20 + i * (_BOX_W + _GAP_X) for i in range(n)]

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{total_w}" height="{total_h}" '
        f'viewBox="0 0 {total_w} {total_h}" '
        f'style="max-width:100%;height:auto;" '
        f'role="img" aria-label="Column ERD: {html.escape(", ".join(t.short_name for t in built))}">',
        "<defs>",
        '<marker id="erd-arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#FF5F02"/></marker>',
        "</defs>",
    ]

    for t, x in zip(built, xs):
        _render_table(t, x, _TOP_Y, parts)

    _render_connectors(built, xs, relationships, parts)
    _render_legend(_TOP_Y + max_h + _LEGEND_GAP, parts)

    parts.append("</svg>")
    return "".join(parts)
