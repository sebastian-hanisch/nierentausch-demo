"""Plotly-Abbildungen: Kompatibilitätsgraph (Paare auf einem Kreis, altruistische Spender auf einem inneren Kreis,
gewählte Kreise/Ketten hervorgehoben), Kreis-/Kettenlängen-Histogramm, Kappungs-Vergleich, Aufwand gegen Größe.
Achsen gesperrt (fixedrange) für Touch-Geräte. Kein geometrisches Kartenbild (Entfernung wäre hier fachlich falsch,
siehe `nt_scenario.py`) - stattdessen eine reine Layout-Anordnung ohne inhaltliche Bedeutung der Position."""

import math

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from nt_scenario import BLOOD_LABELS

CYCLE_COLOR = "#2ca02c"
CHAIN_COLOR = "#9467bd"
BG_COLOR = "rgba(150,150,150,0.18)"
UNMATCHED_COLOR = "#bbbbbb"
ALT_COLOR = "#d62728"


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.08), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _positions(n, n_alt, r_pair=10.0, r_alt=4.0):
    pair_pos = {i: (r_pair * math.cos(2 * math.pi * i / max(n, 1)), r_pair * math.sin(2 * math.pi * i / max(n, 1))) for i in range(n)}
    alt_pos = {a: (r_alt * math.cos(2 * math.pi * a / max(n_alt, 1) + 0.3), r_alt * math.sin(2 * math.pi * a / max(n_alt, 1) + 0.3)) for a in range(n_alt)}
    return pair_pos, alt_pos


def _seg(p0, p1):
    return [p0[0], p1[0], None], [p0[1], p1[1], None]


def build_graph(sc, res, revealed=None, height=520):
    """`revealed`: wie viele der gewählten Kreise/Ketten schon gezeichnet werden (None = alle) - fürs Abspielen."""
    n, n_alt = sc.n, sc.n_alt
    pair_pos, alt_pos = _positions(n, n_alt)
    fig = go.Figure()

    all_edges = sc.compatible_edges()
    bx, by = [], []
    for donor, p, q in all_edges:
        p0 = alt_pos[donor[1]] if donor[0] == "alt" else pair_pos[donor[1]]
        p1 = pair_pos[p]
        x, y = _seg(p0, p1)
        bx += x
        by += y
    fig.add_trace(go.Scatter(x=bx, y=by, mode="lines", line=dict(color=BG_COLOR, width=1), hoverinfo="skip", name="mögliche Kanten"))

    shown = res.chosen if revealed is None else res.chosen[:revealed]
    matched_pairs = set()
    for c in shown:
        color = CYCLE_COLOR if c.kind == "cycle" else CHAIN_COLOR
        nodes = ([("alt", c.alt)] if c.kind == "chain" else []) + [("pair", p) for p in c.pairs]
        cx, cy = [], []
        for a, b in zip(nodes, nodes[1:]):
            p0 = alt_pos[a[1]] if a[0] == "alt" else pair_pos[a[1]]
            p1 = alt_pos[b[1]] if b[0] == "alt" else pair_pos[b[1]]
            x, y = _seg(p0, p1)
            cx += x
            cy += y
        if c.kind == "cycle":
            p0 = pair_pos[c.pairs[-1]]
            p1 = pair_pos[c.pairs[0]]
            x, y = _seg(p0, p1)
            cx += x
            cy += y
        fig.add_trace(go.Scatter(x=cx, y=cy, mode="lines", line=dict(color=color, width=3), hoverinfo="skip",
                                 name="Kreis" if c.kind == "cycle" else "Kette", showlegend=False))
        matched_pairs.update(c.pairs)

    for label, idx_list, color in (("versorgt", sorted(matched_pairs), CYCLE_COLOR), ("unversorgt", [i for i in range(n) if i not in matched_pairs], UNMATCHED_COLOR)):
        if idx_list:
            fig.add_trace(go.Scatter(x=[pair_pos[i][0] for i in idx_list], y=[pair_pos[i][1] for i in idx_list], mode="markers+text", name=label,
                                     text=[BLOOD_LABELS[sc.patient_type[i]] for i in idx_list], textposition="top center",
                                     hovertext=[f"Paar {i}: Patient {BLOOD_LABELS[sc.patient_type[i]]}, Spender {BLOOD_LABELS[sc.donor_type[i]]}" for i in idx_list],
                                     hoverinfo="text", marker=dict(symbol="circle", size=13, color=color, line=dict(width=1, color="#333"))))
    if n_alt:
        fig.add_trace(go.Scatter(x=[alt_pos[a][0] for a in range(n_alt)], y=[alt_pos[a][1] for a in range(n_alt)], mode="markers+text", name="altruistischer Spender",
                                 text=[BLOOD_LABELS[t] for t in sc.alt_type], textposition="bottom center",
                                 hovertext=[f"Altruistischer Spender {a}: {BLOOD_LABELS[sc.alt_type[a]]}" for a in range(n_alt)], hoverinfo="text",
                                 marker=dict(symbol="star", size=15, color=ALT_COLOR, line=dict(width=1, color="#333"))))

    fig.update_xaxes(visible=False, scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False)
    fig.update_layout(showlegend=False)
    return _base(fig, height)


def build_length_hist(hist_share, height=280):
    lengths = sorted(hist_share)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[str(L) for L in lengths], y=[100 * hist_share[L] for L in lengths], marker_color=CYCLE_COLOR))
    fig.update_xaxes(title="Größe (Kreis- oder Kettenlänge)")
    fig.update_yaxes(title="Anteil aller gewählten Kreise/Ketten [%]", rangemode="tozero")
    return _base(fig, height)


def build_cap_comparison(cap2_share, general_share, cap2_q, general_q, height=280):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    labels = ["Kappung 2 (exakt)", "Allgemein (Heuristik)"]
    fig.add_trace(go.Bar(x=labels, y=[100 * cap2_share, 100 * general_share], name="Versorgungsanteil [%]", marker_color=CYCLE_COLOR), secondary_y=False)
    fig.add_trace(go.Bar(x=labels, y=[cap2_q, general_q], name="Qualität (Summe)", marker_color=CHAIN_COLOR), secondary_y=True)
    fig.update_yaxes(title="Versorgungsanteil [%]", rangemode="tozero", range=[0, 105], secondary_y=False)
    fig.update_yaxes(title="Qualität (Summe)", rangemode="tozero", showgrid=False, secondary_y=True)
    fig.update_layout(barmode="group")
    fig = _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.3), height=height + 30)
    return fig


def build_scale(rows, height=320):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[r["n"] for r in rows], y=[r["steps"] for r in rows], mode="lines+markers", name="Aufwand", line=dict(color=CHAIN_COLOR)))
    fig.update_xaxes(title="Anzahl unverträglicher Paare n")
    fig.update_yaxes(title="Schritte (Kandidaten + Kombinationsschritte)", type="log")
    fig = _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.3), height=height + 30)
    return fig
