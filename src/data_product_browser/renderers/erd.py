"""Column-level ERD SVG generator.

Adopts the visual language of the ``data-model-erd`` skill — proper badge
vocabulary (PK / NK / FK / PII / SENS / NN), key-anchored bezier connectors with
cardinality labels, and a themeable palette (light | navy | black). Output is a
static, self-contained inline SVG suitable for embedding once per recipe in the
Cookbook page (no JS — the full zoom/pan/hover/drag experience belongs to a
standalone diagram, not dozens of inline copies in a scrolling document).

Badge support reflects the metadata the browser actually collects:
  PK   surrogate_key_column (EntityMetadata)
  NK   natural_key_column   (EntityMetadata)
  FK   a source_column of an active TableRelationship
  PII  ColumnMetadata.is_pii
  SENS ColumnMetadata.is_sensitive
  NN   ColumnMetadata.is_required
(PI and identity are not collected by the browser, so they are not shown.)
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field

from ..models import ColumnMetadata, EntityMetadata, TableRelationship

# Layout constants
_BOX_W = 320
_HDR_H = 40  # table header band
_COL_H = 24  # per-column row height
_GAP_X = 168  # horizontal gap between tables (room for connectors + labels)
_TOP_Y = 20  # y offset for first table
_LEGEND_GAP = 30  # gap below tallest table before legend
_FONT = "Inter, -apple-system, sans-serif"
_MONO = "'JetBrains Mono', Menlo, monospace"

# ---------------------------------------------------------------------------
# Themes — mirror the data-model-erd skill palettes (light is the default so the
# diagram blends with the light Cookbook page).
# ---------------------------------------------------------------------------
_THEMES = {
    "light": {
        "box": "#FFFFFF", "box_stroke": "#AEC1D1", "hdr": "#EAF1F7",
        "ename": "#00233C", "edb": "#5f7488", "row_alt": "#F7FAFC",
        "rowdiv": "#E3EAF0", "cn": "#00233C", "cn_fk": "#2F6FBF",
        "ct": "#5f7488", "edge_hard": "#E5550A", "edge_soft": "#2F6FBF",
        "card_ink": "#00233C", "card_bg": "#FFFFFF", "legend": "#5f7488",
        "pk_bg": "#FF5F02", "pk_tx": "#FFFFFF", "nk_st": "#2F6FBF", "nk_tx": "#2F6FBF",
        "fk_bg": "#2F6FBF", "fk_tx": "#FFFFFF", "pii_bg": "#9C6FA8", "pii_tx": "#FFFFFF",
        "sens_bg": "#D64545", "sens_tx": "#FFFFFF", "nn_st": "#AEC1D1", "nn_tx": "#5f7488",
    },
    "navy": {
        "box": "#06304a", "box_stroke": "#1d6388", "hdr": "#0a3a59",
        "ename": "#E6EEF5", "edb": "#8FB0C7", "row_alt": "#073651",
        "rowdiv": "#0e3f5e", "cn": "#E6EEF5", "cn_fk": "#7fb4ee",
        "ct": "#8FB0C7", "edge_hard": "#FF5F02", "edge_soft": "#4A90E2",
        "card_ink": "#FFFFFF", "card_bg": "#001829", "legend": "#8FB0C7",
        "pk_bg": "#FF5F02", "pk_tx": "#2a1400", "nk_st": "#4A90E2", "nk_tx": "#7fb4ee",
        "fk_bg": "#4A90E2", "fk_tx": "#04162b", "pii_bg": "#D8BFD8", "pii_tx": "#3a2440",
        "sens_bg": "#FF6B5B", "sens_tx": "#330d08", "nn_st": "#1d6388", "nn_tx": "#8FB0C7",
    },
    "black": {
        "box": "#101013", "box_stroke": "#3b3b44", "hdr": "#17171b",
        "ename": "#F2F4F7", "edb": "#9aa1ab", "row_alt": "#0c0c0e",
        "rowdiv": "#222228", "cn": "#F2F4F7", "cn_fk": "#7fb4ee",
        "ct": "#9aa1ab", "edge_hard": "#FF6A12", "edge_soft": "#4A90E2",
        "card_ink": "#FFFFFF", "card_bg": "#000000", "legend": "#9aa1ab",
        "pk_bg": "#FF5F02", "pk_tx": "#1a0c00", "nk_st": "#4A90E2", "nk_tx": "#7fb4ee",
        "fk_bg": "#4A90E2", "fk_tx": "#04162b", "pii_bg": "#D8BFD8", "pii_tx": "#2a1830",
        "sens_bg": "#FF6B5B", "sens_tx": "#2a0a06", "nn_st": "#3b3b44", "nn_tx": "#9aa1ab",
    },
}


@dataclass
class _ColRow:
    name: str
    data_type: str
    pk: bool
    nk: bool
    fk: bool
    pii: bool
    sens: bool
    nn: bool

    @property
    def is_key(self) -> bool:
        return self.pk or self.nk


@dataclass
class _Table:
    short_name: str
    full_name: str
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
    # Case-insensitive lookups — Teradata returns names in varying case.
    fk_source: dict[str, set[str]] = {}
    for r in relationships:
        if r.is_active:
            fk_source.setdefault(r.source_table.upper(), set()).add(r.source_column.upper())

    natural_keys: dict[str, str] = {}
    surrogate_keys: dict[str, str] = {}
    for e in entities:
        if e.natural_key_column:
            natural_keys[e.table_name.upper()] = e.natural_key_column.upper()
        if e.surrogate_key_column:
            surrogate_keys[e.table_name.upper()] = e.surrogate_key_column.upper()

    tables: list[_Table] = []
    for tname in table_names:
        short = _short(tname)
        key = short.upper()
        cols_for = [c for c in columns if c.table_name.upper() == key]
        if not cols_for:
            continue

        nk_col = natural_keys.get(key)
        pk_col = surrogate_keys.get(key)
        fk_cols = fk_source.get(key, set())

        rows = [
            _ColRow(
                name=c.column_name,
                data_type=c.data_type or "",
                pk=(pk_col is not None and c.column_name.upper() == pk_col),
                nk=(nk_col is not None and c.column_name.upper() == nk_col),
                fk=c.column_name.upper() in fk_cols,
                pii=bool(c.is_pii),
                sens=bool(c.is_sensitive),
                nn=bool(c.is_required),
            )
            for c in cols_for
        ]
        tables.append(_Table(short_name=short, full_name=tname, cols=rows))

    return tables


def _badge(parts: list[str], x: int, y: int, label: str, fill: str | None,
           stroke: str | None, text: str, pal: dict) -> int:
    """Draw one badge chip at (x,y); return its width incl. trailing gap."""
    w = len(label) * 6.4 + 8
    if fill:
        parts.append(f'<rect x="{x}" y="{y}" width="{w:.0f}" height="15" rx="4" fill="{fill}"/>')
    else:
        parts.append(f'<rect x="{x}" y="{y}" width="{w:.0f}" height="15" rx="4" '
                     f'fill="none" stroke="{stroke}" stroke-width="1"/>')
    parts.append(f'<text x="{x + w / 2:.0f}" y="{y + 11}" font-family="{_FONT}" font-size="9.5" '
                 f'font-weight="700" fill="{text}" text-anchor="middle">{label}</text>')
    return int(w) + 4


def _render_table(t: _Table, x: int, y: int, parts: list[str], pal: dict) -> None:
    h = t.box_h
    esc = html.escape

    parts.append(
        f'<rect x="{x}" y="{y}" width="{_BOX_W}" height="{h}" rx="9" '
        f'fill="{pal["box"]}" stroke="{pal["box_stroke"]}" stroke-width="1.4"/>'
    )
    # Header band (rounded top via path)
    parts.append(
        f'<path d="M{x} {y + 9} a9 9 0 0 1 9 -9 h{_BOX_W - 18} a9 9 0 0 1 9 9 '
        f'v{_HDR_H - 9} h-{_BOX_W} z" fill="{pal["hdr"]}"/>'
    )
    parts.append(
        f'<text x="{x + 12}" y="{y + 18}" font-family="{_FONT}" font-size="13" '
        f'font-weight="700" fill="{pal["ename"]}">{esc(t.short_name)}</text>'
    )
    parts.append(
        f'<text x="{x + 12}" y="{y + 32}" font-family="{_FONT}" font-size="9.5" '
        f'fill="{pal["edb"]}">entity</text>'
    )

    for idx, col in enumerate(t.cols):
        ry = y + _HDR_H + idx * _COL_H
        cy = ry + _COL_H // 2 + 4
        if idx % 2 == 0:
            parts.append(f'<rect x="{x + 1}" y="{ry}" width="{_BOX_W - 2}" height="{_COL_H}" '
                         f'fill="{pal["row_alt"]}" opacity="0.5"/>')
        if idx > 0:
            parts.append(f'<line x1="{x + 10}" y1="{ry}" x2="{x + _BOX_W - 10}" y2="{ry}" '
                         f'stroke="{pal["rowdiv"]}" stroke-width="1"/>')

        cn_col = pal["cn_fk"] if col.fk else pal["cn"]
        weight = "600" if col.is_key else "400"
        parts.append(
            f'<text x="{x + 12}" y="{cy}" font-family="{_FONT}" font-size="12" '
            f'font-weight="{weight}" fill="{cn_col}">{esc(col.name)}</text>'
        )

        # Badges, right-aligned (skill order: PK NK FK PII SENS NN)
        chips = []
        if col.pk:   chips.append(("PK", pal["pk_bg"], None, pal["pk_tx"]))
        if col.nk:   chips.append(("NK", None, pal["nk_st"], pal["nk_tx"]))
        if col.fk:   chips.append(("FK", pal["fk_bg"], None, pal["fk_tx"]))
        if col.pii:  chips.append(("PII", pal["pii_bg"], None, pal["pii_tx"]))
        if col.sens: chips.append(("SENS", pal["sens_bg"], None, pal["sens_tx"]))
        if col.nn:   chips.append(("NN", None, pal["nn_st"], pal["nn_tx"]))

        widths = [int(len(lbl) * 6.4 + 8) + 4 for lbl, *_ in chips]
        bx = x + _BOX_W - 12 - sum(widths)
        type_right = bx - 6
        for (lbl, fill, stroke, txc), w in zip(chips, widths):
            _badge(parts, bx, ry + 4, lbl, fill, stroke, txc, pal)
            bx += w

        parts.append(
            f'<text x="{type_right}" y="{cy}" font-family="{_MONO}" font-size="9.5" '
            f'fill="{pal["ct"]}" text-anchor="end">{esc(col.data_type)}</text>'
        )


def _render_connectors(
    tables: list[_Table],
    xs: list[int],
    relationships: list[TableRelationship],
    parts: list[str],
    pal: dict,
) -> list[dict]:
    """Draw connector lines + endpoint dots (beneath the boxes).

    Returns a list of label specs to be drawn *on top* of the boxes afterwards,
    so cardinality pills are never clipped under an adjacent table.
    """
    table_index = {t.short_name.upper(): i for i, t in enumerate(tables)}
    drawn: set[tuple] = set()
    labels: list[dict] = []

    for r in relationships:
        if not r.is_active:
            continue
        si = table_index.get(r.source_table.upper())
        ti = table_index.get(r.target_table.upper())
        if si is None or ti is None or si == ti:
            continue
        edge_key = (min(si, ti), max(si, ti), r.source_column.upper(), r.target_column.upper())
        if edge_key in drawn:
            continue
        drawn.add(edge_key)

        st, tt = tables[si], tables[ti]
        sy = st.col_y_centre(r.source_column, _TOP_Y)
        ty = tt.col_y_centre(r.target_column, _TOP_Y)
        if sy is None or ty is None:
            continue

        s_left = xs[si] > xs[ti]
        sx = xs[si] if s_left else xs[si] + _BOX_W
        tx = xs[ti] + _BOX_W if s_left else xs[ti]
        dx = max(60, abs(tx - sx) * 0.45) * (-1 if s_left else 1)
        path = f"M {sx} {sy} C {sx + dx:.0f} {sy}, {tx - dx:.0f} {ty}, {tx} {ty}"

        is_hard = (r.relationship_type or "").upper() == "FK" or bool(r.is_mandatory)
        colour = pal["edge_hard"] if is_hard else pal["edge_soft"]
        dash = "" if is_hard else ' stroke-dasharray="7,5"'
        parts.append(f'<path d="{path}" fill="none" stroke="{colour}" stroke-width="2.3"{dash}/>')
        parts.append(f'<circle cx="{sx}" cy="{sy}" r="3.2" fill="{colour}"/>')
        parts.append(f'<circle cx="{tx}" cy="{ty}" r="3.2" fill="{colour}"/>')

        # Build the label, clamped to the available inter-box gap so it never
        # overflows under a neighbouring table.
        gap = abs(tx - sx)
        card = r.cardinality or ""
        meaning = (r.relationship_meaning or "").strip()
        label = card
        if meaning:
            candidate = f"{card}  \u00b7  {meaning}" if card else meaning
            if len(candidate) * 5.4 + 10 <= gap * 0.96:
                label = candidate
            else:
                # try a truncated meaning, else fall back to cardinality only
                room = int((gap * 0.96 - 10) / 5.4) - (len(card) + 5)
                if room >= 6:
                    label = f"{card}  \u00b7  {meaning[:room - 1]}\u2026"
        if label:
            labels.append({"x": (sx + tx) / 2, "y": (sy + ty) / 2, "text": label})

    return labels


def _render_edge_labels(labels: list[dict], parts: list[str], pal: dict) -> None:
    for lab in labels:
        w = len(lab["text"]) * 5.4 + 10
        mx, my = lab["x"], lab["y"]
        parts.append(f'<rect x="{mx - w / 2:.0f}" y="{my - 9:.0f}" width="{w:.0f}" height="16" '
                     f'rx="5" fill="{pal["card_bg"]}" opacity="0.92"/>')
        parts.append(f'<text x="{mx:.0f}" y="{my + 3:.0f}" font-family="{_FONT}" font-size="10" '
                     f'font-weight="600" fill="{pal["card_ink"]}" text-anchor="middle">'
                     f'{html.escape(lab["text"])}</text>')


def _render_legend(x0: int, y: int, parts: list[str], pal: dict) -> None:
    lx = x0
    items = [
        ("PK", pal["pk_bg"], None, pal["pk_tx"], "key"),
        ("NK", None, pal["nk_st"], pal["nk_tx"], "natural"),
        ("FK", pal["fk_bg"], None, pal["fk_tx"], "foreign"),
        ("PII", pal["pii_bg"], None, pal["pii_tx"], ""),
        ("SENS", pal["sens_bg"], None, pal["sens_tx"], ""),
        ("NN", None, pal["nn_st"], pal["nn_tx"], "not null"),
    ]
    for lbl, fill, stroke, txc, note in items:
        w = _badge(parts, lx, y - 11, lbl, fill, stroke, txc, pal)
        lx += w + 2
        if note:
            parts.append(f'<text x="{lx}" y="{y}" font-family="{_FONT}" font-size="9" '
                         f'fill="{pal["legend"]}">{note}</text>')
            lx += len(note) * 5 + 14
        else:
            lx += 8
    # Edge legend
    parts.append(f'<line x1="{lx}" y1="{y - 4}" x2="{lx + 22}" y2="{y - 4}" '
                 f'stroke="{pal["edge_hard"]}" stroke-width="2.3"/>')
    parts.append(f'<text x="{lx + 27}" y="{y}" font-family="{_FONT}" font-size="9" '
                 f'fill="{pal["legend"]}">FK</text>')
    lx += 27 + 20
    parts.append(f'<line x1="{lx}" y1="{y - 4}" x2="{lx + 22}" y2="{y - 4}" '
                 f'stroke="{pal["edge_soft"]}" stroke-width="2.3" stroke-dasharray="7,5"/>')
    parts.append(f'<text x="{lx + 27}" y="{y}" font-family="{_FONT}" font-size="9" '
                 f'fill="{pal["legend"]}">soft</text>')


def make_column_erd(
    tables: list[str],
    columns: list[ColumnMetadata],
    relationships: list[TableRelationship],
    entities: list[EntityMetadata],
    theme: str = "light",
) -> str:
    """Return an inline SVG column-level ERD for the given table list.

    ``theme`` is one of ``light`` (default, matches the Cookbook page), ``navy``
    or ``black`` (mirrors the data-model-erd skill themes).
    """
    pal = _THEMES.get(theme, _THEMES["light"])
    built = _build_tables(tables, columns, relationships, entities)
    if not built:
        return ""

    n = len(built)
    total_w = 20 + n * _BOX_W + (n - 1) * _GAP_X + 20
    max_h = max(t.box_h for t in built)
    total_h = _TOP_Y + max_h + _LEGEND_GAP + 18

    xs = [20 + i * (_BOX_W + _GAP_X) for i in range(n)]

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{total_h}" '
        f'viewBox="0 0 {total_w} {total_h}" style="max-width:100%;height:auto;" role="img" '
        f'aria-label="Column ERD: {html.escape(", ".join(t.short_name for t in built))}">',
    ]
    # Connectors first so boxes sit on top (matches the skill's edge layer).
    edge_labels = _render_connectors(built, xs, relationships, parts, pal)
    for t, x in zip(built, xs):
        _render_table(t, x, _TOP_Y, parts, pal)
    # Edge labels on top of the boxes so cardinality pills are never clipped.
    _render_edge_labels(edge_labels, parts, pal)
    _render_legend(20, _TOP_Y + max_h + _LEGEND_GAP, parts, pal)
    parts.append("</svg>")
    return "".join(parts)
