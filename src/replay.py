"""Interactive Plotly replay of a play (used by the Streamlit dashboard and the HTML export).

Top panel: the field, centred on the QB, with the 2 yd pocket circle. Bottom panel: distance between the QB and the closest
rusher over time, with the pressure threshold, so the moment the pocket breaks can be read without watching dots.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from . import theme as T
from .load import FPS
from .metrics import PRESSURE_RADIUS

COL = {"qb": T.ACCENT, "rush": T.BAD, "off": "#4cc9f0", "def": "#f4a261", "ball": "#c08457"}
LABEL = {"off": "Offense", "def": "Coverage", "rush": "Pass rush", "qb": "QB", "ball": "Ball"}
TURF, LINES = "#0f1c16", "rgba(255,255,255,.10)"
GROUPS = ("off", "def", "rush", "qb", "ball")
MAX_DIST = 12.0   # yd, cap of the distance panel


def _circle(cx, cy, r, n=60):
    a = np.linspace(0, 2 * np.pi, n)
    return cx + r * np.cos(a), cy + r * np.sin(a)


def _players(a: pd.DataFrame, names: dict | None) -> pd.DataFrame:
    a = a.copy()
    a["who"] = a.nflId.map(names or {}).fillna("") if "nflId" in a else ""
    return a


def play_figure(trk: pd.DataFrame, pff: pd.DataFrame, gameId: int, playId: int, radius=PRESSURE_RADIUS, title="",
                names: dict | None = None) -> go.Figure:
    """`names` optionally maps nflId -> display name, shown on hover."""
    a = trk[(trk.gameId == gameId) & (trk.playId == playId)].merge(
        pff[(pff.gameId == gameId) & (pff.playId == playId)][["nflId", "pff_role"]], on="nflId", how="left")
    a["grp"] = np.select([a.pff_role == "Pass", a.pff_role == "Pass Rush", a.team.astype(str) == "football", a.pff_role == "Coverage"],
                         ["qb", "rush", "ball", "def"], "off")
    a = _players(a, names)
    frames_ids = sorted(a.frameId.unique())
    snap = a.snap_frame.iloc[0]
    qb0 = a[a.grp == "qb"]
    cx, cy = qb0.x.mean(), qb0.y.mean()
    ball0 = a[(a.grp == "ball") & (a.frameId == snap)]
    los_x = float(ball0.x.iloc[0]) if len(ball0) else None

    # first pass: nearest-rusher distance per frame and the frame where the pocket breaks
    t_axis, dist, hit = [], [], None
    for f in frames_ids:
        d = a[a.frameId == f]
        q, r = d[d.grp == "qb"], d[d.grp == "rush"]
        m = float(np.hypot(r.x - q.x.iloc[0], r.y - q.y.iloc[0]).min()) if len(q) and len(r) else np.nan
        t_axis.append((f - snap) / FPS)
        dist.append(min(m, MAX_DIST) if m == m else np.nan)
        if hit is None and m == m and m < radius:
            hit = f
    hit_t = None if hit is None else (hit - snap) / FPS

    def status(i, f):
        red = hit is not None and f >= hit
        text = f"<b>{t_axis[i]:.1f} s</b> · " + (f"<span style='color:{T.BAD}'>pocket broken at {hit_t:.1f} s</span>" if red
                                                else f"<span style='color:{T.GOOD}'>clean pocket</span>")
        return dict(text=text, xref="paper", yref="paper", x=0.01, y=0.99, xanchor="left", yanchor="top", showarrow=False,
                    align="left", bgcolor="rgba(11,13,16,.75)", borderpad=6, font=dict(size=14, color=T.TEXT, family=T.FONT_BODY))

    frames = []
    for i, f in enumerate(frames_ids):
        d = a[a.frameId == f]
        q = d[d.grp == "qb"]
        red = hit is not None and f >= hit
        cxs, cys = _circle(q.x.iloc[0], q.y.iloc[0], radius) if len(q) else ([], [])
        data = [go.Scatter(x=d[d.grp == g].x, y=d[d.grp == g].y) for g in GROUPS]
        data.append(go.Scatter(x=cxs, y=cys, line=dict(color=T.BAD if red else T.TEXT, width=3)))
        data.append(go.Scatter(x=[t_axis[i]], y=[dist[i]], marker=dict(color=T.BAD if red else T.ACCENT)))
        frames.append(go.Frame(data=data, traces=[0, 1, 2, 3, 4, 5, 7], name=str(f), layout=go.Layout(annotations=[status(i, f)])))

    fig = make_subplots(rows=2, cols=1, row_heights=[0.8, 0.2], vertical_spacing=0.12)
    d0 = a[a.frameId == frames_ids[0]]
    for g in GROUPS:
        sub = d0[d0.grp == g]
        fig.add_trace(go.Scatter(
            x=sub.x, y=sub.y, mode="markers", name=LABEL[g], text=[(w or LABEL[g]) for w in sub.who], customdata=sub.s,
            hovertemplate="<b>%{text}</b><br>%{customdata:.1f} yd/s<extra>" + LABEL[g] + "</extra>",
            marker=dict(size={"qb": 18, "ball": 8}.get(g, 13), color=COL[g],
                        line=dict(width=1.5, color=T.TEXT if g in ("qb", "rush") else T.BG))), row=1, col=1)
    cx0, cy0 = _circle(float(qb0[qb0.frameId == frames_ids[0]].x.iloc[0]), float(qb0[qb0.frameId == frames_ids[0]].y.iloc[0]), radius)
    fig.add_trace(go.Scatter(x=cx0, y=cy0, mode="lines", name=f"{radius:g} yd radius", line=dict(color=T.TEXT, width=3), hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=t_axis, y=dist, mode="lines", name="Closest rusher", line=dict(color=T.REF, width=2),
                             hovertemplate="%{x:.1f} s · %{y:.1f} yd<extra>closest rusher</extra>"), row=2, col=1)
    fig.add_trace(go.Scatter(x=[t_axis[0]], y=[dist[0]], mode="markers", showlegend=False, hoverinfo="skip",
                             marker=dict(size=11, color=T.ACCENT, line=dict(width=2, color=T.BG))), row=2, col=1)
    fig.frames = frames

    if los_x is not None:
        fig.add_vline(x=los_x, line=dict(color=T.ACCENT, width=1, dash="dot"), row=1, col=1)
    fig.add_hrect(y0=0, y1=radius, fillcolor=T.BAD, opacity=0.18, line_width=0, row=2, col=1)
    fig.add_hline(y=radius, line=dict(color=T.BAD, width=1, dash="dash"), row=2, col=1,
                  annotation_text=f"{radius:g} yd = pressure", annotation_font=dict(color=T.BAD, size=11), annotation_position="top right")
    snap_steps = [dict(method="animate", label=f"{t:.1f}", args=[[str(f)], dict(mode="immediate", frame=dict(duration=0, redraw=True))])
                  for f, t in zip(frames_ids, t_axis)]
    fig.update_layout(
        height=780, margin=dict(l=10, r=10, t=70, b=90), paper_bgcolor=T.SURFACE, plot_bgcolor=TURF,
        title=dict(text=title, font=dict(size=14, color=T.MUTED), x=0, y=0.98, yanchor="top"),
        legend=dict(orientation="h", y=1.01, yanchor="bottom", x=0, font=dict(color=T.MUTED)),
        annotations=[status(0, frames_ids[0])],
        xaxis=dict(range=[cx - 16, cx + 14], showgrid=True, gridcolor=LINES, dtick=5, zeroline=False, showticklabels=False, constrain="domain"),
        yaxis=dict(range=[cy - 10, cy + 10], scaleanchor="x", scaleratio=1, showgrid=False, zeroline=False, showticklabels=False, constrain="domain"),
        xaxis2=dict(range=[0, max(t_axis)], title="seconds since the snap", gridcolor=T.GRID),
        yaxis2=dict(range=[0, MAX_DIST], title="yd to QB", gridcolor=T.GRID, dtick=4),
        updatemenus=[dict(type="buttons", direction="left", active=-1, x=0, y=-0.17, xanchor="left", yanchor="top", pad=dict(t=0, r=6),
                          bgcolor=T.SURFACE_2, bordercolor=T.BORDER_STRONG, font=dict(color=T.TEXT, size=13), buttons=[
            dict(label="▶ Play", method="animate", args=[None, dict(frame=dict(duration=100, redraw=True), fromcurrent=True, transition=dict(duration=0))]),
            dict(label="❚❚ Pause", method="animate", args=[[None], dict(frame=dict(duration=0), mode="immediate")])])],
        sliders=[dict(steps=snap_steps, x=0.22, len=0.78, y=-0.17, yanchor="top", pad=dict(t=0, b=0),
                      currentvalue=dict(prefix="t = ", suffix=" s", font=dict(color=T.MUTED)),
                      bgcolor=T.BORDER, activebgcolor=T.ACCENT, bordercolor=T.BORDER_STRONG, tickcolor=T.BORDER_STRONG,
                      font=dict(color=T.SUBTLE))])
    return fig
