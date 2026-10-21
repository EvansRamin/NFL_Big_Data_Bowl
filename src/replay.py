"""Interactive Plotly replay of a play (used by the Streamlit dashboard and the HTML export)."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .load import FPS
from .metrics import PRESSURE_RADIUS

COL = {"qb": "#ffd60a", "rush": "#e63946", "off": "#4cc9f0", "def": "#f4a261", "ball": "#6f4518"}


def _circle(cx, cy, r, n=60):
    a = np.linspace(0, 2 * np.pi, n)
    return cx + r * np.cos(a), cy + r * np.sin(a)


def play_figure(trk: pd.DataFrame, pff: pd.DataFrame, gameId: int, playId: int, radius=PRESSURE_RADIUS, title="") -> go.Figure:
    a = trk[(trk.gameId == gameId) & (trk.playId == playId)].merge(
        pff[(pff.gameId == gameId) & (pff.playId == playId)][["nflId", "pff_role"]], on="nflId", how="left")
    a["grp"] = np.select([a.pff_role == "Pass", a.pff_role == "Pass Rush", a.team.astype(str) == "football", a.pff_role == "Coverage"],
                         ["qb", "rush", "ball", "def"], "off")
    frames_ids = sorted(a.frameId.unique())
    snap = a.snap_frame.iloc[0]
    qb0 = a[a.grp == "qb"]
    cx, cy = qb0.x.mean(), qb0.y.mean()
    hit = None
    frames = []
    for f in frames_ids:
        d = a[a.frameId == f]
        q = d[d.grp == "qb"]; r = d[d.grp == "rush"]
        if len(q) and hit is None and (np.hypot(r.x - q.x.iloc[0], r.y - q.y.iloc[0]) < radius).any():
            hit = f
        cxs, cys = _circle(q.x.iloc[0], q.y.iloc[0], radius) if len(q) else ([], [])
        red = hit is not None
        data = [go.Scatter(x=d[d.grp == g].x, y=d[d.grp == g].y, mode="markers",
                           marker=dict(size=14 if g != "ball" else 7, color=COL[g], line=dict(width=1, color="black")))
                for g in ("off", "def", "rush", "qb", "ball")]
        data.append(go.Scatter(x=cxs, y=cys, mode="lines", line=dict(color="#ff1d1d" if red else "white", width=4)))
        label = f"{(f - snap) / FPS:.1f} s — " + (f"POCKET BROKEN at {(hit - snap) / FPS:.1f} s" if red else "clean pocket")
        frames.append(go.Frame(data=data, name=str(f), layout=go.Layout(title=dict(text=f"{title}<br><sup>{label}</sup>"))))
    fig = go.Figure(data=frames[0].data, frames=frames)
    names = ["Offense", "Defense (coverage)", "Pass rush", "QB", "Ball", "2 yd radius"]
    for tr, n in zip(fig.data, names):
        tr.name = n
    fig.update_layout(
        title=dict(text=frames[0].layout.title.text), plot_bgcolor="#2e7d32", height=560, margin=dict(l=10, r=10, t=70, b=50),
        legend=dict(orientation="h", y=-0.04, yanchor="top", x=0),
        xaxis=dict(range=[cx - 13, cx + 11], showgrid=True, gridcolor="rgba(255,255,255,.35)", dtick=5, zeroline=False, showticklabels=False),
        yaxis=dict(range=[cy - 12, cy + 12], scaleanchor="x", showgrid=False, zeroline=False, showticklabels=False),
        updatemenus=[dict(type="buttons", x=0.02, y=0.02, buttons=[
            dict(label="▶ Replay", method="animate", args=[None, dict(frame=dict(duration=100, redraw=True), fromcurrent=False)]),
            dict(label="⏸", method="animate", args=[[None], dict(frame=dict(duration=0), mode="immediate")])])],
        sliders=[dict(steps=[dict(method="animate", label=f"{(int(f) - snap) / FPS:.1f}", args=[[str(f)], dict(mode="immediate", frame=dict(duration=0, redraw=True))])
                             for f in frames_ids], currentvalue=dict(prefix="t = ", suffix=" s"))])
    return fig
