"""Programmatic SVG join-diagram generation from Semantic relationship metadata.

Dimensions match the original MortgagePlatform_Cookbook.html exactly:
  box width=140, gap=60, left margin=40 → 4 tables = 860px wide.

The SVG carries an explicit width attribute so it renders at its natural size
and does not stretch to fill the container.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

_PALETTE = ["#00233C", "#FF5F02", "#4A90E2", "#16a34a", "#7c3aed", "#d97706"]
_BOX_W   = 140
_BOX_H   = 36
_GAP     = 60
_MARGIN  = 40
_Y       = 44
_FONT    = "Inter, sans-serif"


@dataclass
class _Node:
    label: str
    x: int
    color: str


def make_join_diagram(tables: list[str], dashed_after: int | None = None) -> str:
    """Return an inline SVG join diagram for the given ordered table list.

    Args:
        tables:       Table names to render left-to-right.
        dashed_after: If set, edges from this index onward are dashed (LEFT OUTER).
    """
    if not tables:
        return ""

    n = len(tables)
    total_w = _MARGIN + n * _BOX_W + (n - 1) * _GAP + _MARGIN
    svg_h   = _BOX_H + _Y + 80

    nodes = [
        _Node(
            label=t,
            x=_MARGIN + i * (_BOX_W + _GAP),
            color=_PALETTE[i % len(_PALETTE)],
        )
        for i, t in enumerate(tables)
    ]

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{total_w}" height="{svg_h}" '
        f'viewBox="0 0 {total_w} {svg_h}" '
        f'style="max-width:100%;height:auto;" '
        f'role="img" aria-label="Join diagram: {html.escape(", ".join(tables))}">',
        "<defs>",
        '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">',
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#6b7280"/></marker>',
        "</defs>",
    ]

    # Edges (drawn first so boxes sit on top)
    for i in range(n - 1):
        x1 = nodes[i].x + _BOX_W
        x2 = nodes[i + 1].x
        cy = _Y + _BOX_H // 2
        dashed = dashed_after is not None and i >= dashed_after
        dash_attr = ' stroke-dasharray="6,4"' if dashed else ""
        parts.append(
            f'<line x1="{x1}" y1="{cy}" x2="{x2}" y2="{cy}" '
            f'stroke="#6b7280" stroke-width="1.5" '
            f'marker-end="url(#arrow)"{dash_attr}/>'
        )

    # Boxes
    for node in nodes:
        label = html.escape(node.label)
        cx = node.x + _BOX_W // 2
        parts.append(
            f'<rect x="{node.x}" y="{_Y}" width="{_BOX_W}" height="{_BOX_H}" '
            f'rx="6" ry="6" fill="{node.color}" stroke="#e2e4e8" stroke-width="0.5"/>'
        )
        parts.append(
            f'<text x="{cx}" y="{_Y + 22}" font-family="{_FONT}" '
            f'font-size="11" font-weight="600" fill="#FFFFFF" text-anchor="middle">'
            f"{label}</text>"
        )

    # Legend
    ly = _Y + _BOX_H + 18
    parts += [
        f'<text x="20" y="{ly}" font-family="{_FONT}" font-size="9" font-weight="600" fill="#6b7280">LEGEND</text>',
        f'<rect x="20" y="{ly + 6}" width="14" height="10" rx="2" fill="#00233C"/>',
        f'<text x="40" y="{ly + 14}" font-family="{_FONT}" font-size="10" fill="#6b7280">Entity</text>',
        f'<rect x="100" y="{ly + 6}" width="14" height="10" rx="2" fill="#FF5F02"/>',
        f'<text x="120" y="{ly + 14}" font-family="{_FONT}" font-size="10" fill="#6b7280">Associative / Bridge</text>',
        f'<rect x="264" y="{ly + 6}" width="14" height="10" rx="2" fill="#4A90E2"/>',
        f'<text x="284" y="{ly + 14}" font-family="{_FONT}" font-size="10" fill="#6b7280">Reference</text>',
        f'<line x1="362" y1="{ly + 11}" x2="386" y2="{ly + 11}" stroke="#6b7280" stroke-width="1.6"/>',
        f'<text x="392" y="{ly + 14}" font-family="{_FONT}" font-size="10" fill="#6b7280">INNER</text>',
        f'<line x1="440" y1="{ly + 11}" x2="464" y2="{ly + 11}" stroke="#6b7280" stroke-width="1.6" stroke-dasharray="6,4"/>',
        f'<text x="470" y="{ly + 14}" font-family="{_FONT}" font-size="10" fill="#6b7280">LEFT OUTER</text>',
    ]

    parts.append("</svg>")
    return "".join(parts)
