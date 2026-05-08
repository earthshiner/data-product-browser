"""Join path diagram generator.

Implements the spec from join-diagrams.md:
- Variable-width nodes sized to label text
- BFS layer assignment (simple chain = single horizontal row)
- Bezier edge curves (horizontal: C midpoint control points)
- Edge labels with join column names on a background pill
- Node colouring by entity type
"""

from __future__ import annotations

import html
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import EntityMetadata, TableRelationship

_FONT           = "Inter, sans-serif"
_FONT_SIZE      = 11          # px, node label
_CHAR_W_RATIO   = 0.58        # Inter character width approximation
_NODE_H         = 38
_NODE_RADIUS    = 6
_NODE_PAD       = 28          # horizontal padding inside node
_LAYER_GAP      = 80          # horizontal gap between nodes in the same row
_MARGIN         = 30          # left/right margin
_ROW_Y          = 44          # top of node boxes
_LEGEND_GAP     = 28

# Node colours by entity type (matches spec)
_COL_ENTITY      = "#00233C"   # core entity (navy)
_COL_ASSOC       = "#FF5F02"   # associative / M:M (orange)
_COL_REFERENCE   = "#0369a1"   # reference / lookup (blue)
_COL_UNKNOWN     = "#4A90E2"   # fallback

_EDGE_SOLID  = "#73726c"
_EDGE_DASHED = "#0369a1"

_ARROW_ID = "jd-arrow"


def _node_w(label: str) -> int:
    return max(80, int(len(label) * _FONT_SIZE * _CHAR_W_RATIO) + _NODE_PAD)


def _node_colour(
    short: str,
    entities: list["EntityMetadata"] | None,
    relationships: list["TableRelationship"] | None,
) -> str:
    if entities:
        for e in entities:
            if e.table_name.upper() == short.upper():
                if e.natural_key_column:
                    return _COL_ENTITY
                else:
                    return _COL_ASSOC
    if relationships:
        for r in relationships:
            if (r.to_table.upper() == short.upper()
                    and r.relationship_type.upper() == "LOOKUP"):
                return _COL_REFERENCE
    return _COL_UNKNOWN


def _bezier_h(x1: float, y1: float, x2: float, y2: float) -> str:
    mx = (x1 + x2) / 2
    return f"M {x1:.0f},{y1:.0f} C {mx:.0f},{y1:.0f} {mx:.0f},{y2:.0f} {x2:.0f},{y2:.0f}"


def make_join_diagram(
    tables: list[str],
    dashed_after: int | None = None,
    relationships: list["TableRelationship"] | None = None,
    entities: list["EntityMetadata"] | None = None,
) -> str:
    """Return an inline SVG join diagram.

    Args:
        tables:        Short table names, left-to-right order.
        dashed_after:  Legacy — if set, edges from this index onward are dashed.
        relationships: Full table_relationship list for edge labels + colours.
        entities:      entity_metadata list for node colour classification.
    """
    if not tables:
        return ""

    n = len(tables)
    widths = [_node_w(t) for t in tables]
    total_content_w = sum(widths) + (n - 1) * _LAYER_GAP
    total_w = max(total_content_w + 2 * _MARGIN, 400)
    svg_h = _NODE_H + _ROW_Y + _LEGEND_GAP + 28

    # Node x positions (left edge of each box)
    xs: list[int] = []
    x = _MARGIN + max(0, (total_w - 2 * _MARGIN - total_content_w) // 2)
    for w in widths:
        xs.append(x)
        x += w + _LAYER_GAP

    # Build index for relationship lookup
    rel_index: dict[tuple[str, str], "TableRelationship"] = {}
    if relationships:
        for r in relationships:
            if r.is_active:
                rel_index[(r.from_table.upper(), r.to_table.upper())] = r
                rel_index[(r.to_table.upper(), r.from_table.upper())] = r

    cy = _ROW_Y + _NODE_H // 2

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{total_w}" height="{svg_h}" '
        f'viewBox="0 0 {total_w} {svg_h}" '
        f'style="max-width:100%;height:auto;" '
        f'role="img" aria-label="Join diagram: {html.escape(", ".join(tables))}">',
        "<defs>",
        f'<marker id="{_ARROW_ID}" viewBox="0 0 10 10" refX="9" refY="5" '
        f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">',
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{_EDGE_SOLID}"/></marker>',
        "</defs>",
    ]

    # --- Edges (drawn first, behind nodes) ---
    for i in range(n - 1):
        x1 = xs[i] + widths[i]
        x2 = xs[i + 1]
        t_from = tables[i]
        t_to   = tables[i + 1]

        rel = rel_index.get((t_from.upper(), t_to.upper()))
        dashed = (dashed_after is not None and i >= dashed_after) or (
            rel is not None and rel.join_type.upper() != "INNER"
        )
        stroke     = _EDGE_DASHED if dashed else _EDGE_SOLID
        dash_attr  = ' stroke-dasharray="5,3"' if dashed else ""
        path       = _bezier_h(x1, cy, x2, cy)

        parts.append(
            f'<path d="{path}" fill="none" stroke="{stroke}" stroke-width="1.5" '
            f'marker-end="url(#{_ARROW_ID})"{dash_attr}/>'
        )

        # Edge label: join columns on a background pill
        if rel:
            label_lines = []
            join_t = rel.join_type.upper()
            card   = rel.cardinality or ""
            label_lines.append(f"{join_t}{f' ({card})' if card else ''}")
            label_lines.append(f"{rel.from_column} → {rel.to_column}")

            pill_w  = max(len(l) for l in label_lines) * 6 + 16
            pill_h  = 28
            pill_x  = (x1 + x2) / 2 - pill_w / 2
            pill_y  = cy - pill_h // 2 - 18

            parts.append(
                f'<rect x="{pill_x:.0f}" y="{pill_y:.0f}" '
                f'width="{pill_w:.0f}" height="{pill_h}" '
                f'rx="4" fill="#ffffff" stroke="#e2e4e8" stroke-width="0.5" opacity="0.95"/>'
            )
            parts.append(
                f'<text x="{pill_x + pill_w/2:.0f}" y="{pill_y + 11:.0f}" '
                f'font-family="{_FONT}" font-size="9" font-weight="500" '
                f'fill="#374151" text-anchor="middle">{html.escape(label_lines[0])}</text>'
            )
            parts.append(
                f'<text x="{pill_x + pill_w/2:.0f}" y="{pill_y + 22:.0f}" '
                f'font-family="{_FONT}" font-size="8" '
                f'fill="#6b7280" text-anchor="middle">{html.escape(label_lines[1])}</text>'
            )

    # --- Nodes (drawn on top) ---
    for i, (tname, w) in enumerate(zip(tables, widths)):
        color = _node_colour(tname, entities, relationships)
        label = html.escape(tname)
        cx_box = xs[i] + w // 2
        parts.append(
            f'<rect x="{xs[i]}" y="{_ROW_Y}" width="{w}" height="{_NODE_H}" '
            f'rx="{_NODE_RADIUS}" ry="{_NODE_RADIUS}" '
            f'fill="{color}" stroke="#e2e4e8" stroke-width="0.5"/>'
        )
        parts.append(
            f'<text x="{cx_box}" y="{_ROW_Y + 23}" font-family="{_FONT}" '
            f'font-size="{_FONT_SIZE}" font-weight="600" fill="#FFFFFF" text-anchor="middle">'
            f"{label}</text>"
        )

    # --- Legend ---
    ly = _ROW_Y + _NODE_H + 16
    legend_items = [
        (_COL_ENTITY,    "Entity"),
        (_COL_ASSOC,     "Associative"),
        (_COL_REFERENCE, "Reference"),
    ]
    lx = _MARGIN
    for color, label in legend_items:
        parts.append(f'<rect x="{lx}" y="{ly}" width="14" height="10" rx="2" fill="{color}"/>')
        parts.append(
            f'<text x="{lx + 18}" y="{ly + 9}" font-family="{_FONT}" '
            f'font-size="10" fill="#6b7280">{label}</text>'
        )
        lx += 18 + len(label) * 6 + 20

    parts.append(
        f'<line x1="{lx}" y1="{ly + 5}" x2="{lx + 24}" y2="{ly + 5}" '
        f'stroke="{_EDGE_SOLID}" stroke-width="1.5"/>'
    )
    parts.append(
        f'<text x="{lx + 28}" y="{ly + 9}" font-family="{_FONT}" '
        f'font-size="10" fill="#6b7280">INNER</text>'
    )
    lx += 70
    parts.append(
        f'<line x1="{lx}" y1="{ly + 5}" x2="{lx + 24}" y2="{ly + 5}" '
        f'stroke="{_EDGE_DASHED}" stroke-width="1.5" stroke-dasharray="5,3"/>'
    )
    parts.append(
        f'<text x="{lx + 28}" y="{ly + 9}" font-family="{_FONT}" '
        f'font-size="10" fill="#6b7280">LEFT OUTER</text>'
    )

    parts.append("</svg>")
    return "".join(parts)
