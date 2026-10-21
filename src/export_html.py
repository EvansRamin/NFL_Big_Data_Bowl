"""Standalone HTML version (no server) : python -m src.export_html -> outputs/pocket_clock_dashboard.html"""
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from . import analysis as A
from .load import CACHE_DIR, ROOT, load_tables
from . import theme as T
from .replay import play_figure
from .viz import TEAM_COLORS


def main():
    tab = pd.read_parquet(CACHE_DIR / "cpt_table.parquet")
    trk = pd.read_parquet(CACHE_DIR / "tracking.parquet")
    pff = load_tables()["pffScoutingData"]
    figs = []
    # 1) interactive offensive line ranking
    ol = A.team_ranking(tab, "possessionTeam").sort_values("rmst")
    f = go.Figure(go.Bar(x=ol.rmst - ol.rmst.mean(), y=ol.team, orientation="h", marker=dict(color=[TEAM_COLORS[t] for t in ol.team], line=dict(color=T.OUTLINE, width=1)),
                         customdata=ol[["n", "clean_2.5s"]], hovertemplate="%{y}: %{x:+.2f} s vs average<br>%{customdata[0]} plays · %{customdata[1]:.0%} clean at 2.5 s<extra></extra>"))
    f.update_layout(title="Offensive line protection · gap vs NFL avg (s)", height=800)
    figs.append(f)
    # 2) pocket clock, one curve per team (dropdown)
    f = go.Figure(); teams = sorted(tab.possessionTeam.unique())
    base = A.km(tab).survival_function_
    for i, tm in enumerate(teams):
        sf = A.km(tab[tab.possessionTeam == tm]).survival_function_
        f.add_scatter(x=sf.index, y=sf.iloc[:, 0] * 100, line=dict(shape="hv", color=TEAM_COLORS[tm], width=3), name=tm, visible=(i == 0))
    f.add_scatter(x=base.index, y=base.iloc[:, 0] * 100, line=dict(shape="hv", color="#888", dash="dash"), name="NFL average")
    f.update_layout(title="Pocket clock by offensive team (Kaplan-Meier)", yaxis_range=[40, 100.5], xaxis_range=[0, 4.5],
                    xaxis_title="seconds since the snap", yaxis_title="% clean pockets",
                    updatemenus=[dict(buttons=[dict(label=tm, method="update", args=[{"visible": [j == i for j in range(len(teams))] + [True]}]) for i, tm in enumerate(teams)])])
    figs.append(f)
    # 3) replays of the 3 fastest sacks
    sk = tab[(tab.passResult == "S") & ~tab.censored & (tab.cpt >= 0.5)].sort_values("cpt").head(3)
    for r in sk.itertuples():
        figs.append(play_figure(trk[trk.gameId == r.gameId], pff, int(r.gameId), int(r.playId),
                                title=f"{r.possessionTeam} vs {r.defensiveTeam} — sack, rusher {r.first_rusher}"))
    css = T.CSS.replace("<style>", "<style>.block-container{max-width:1100px;margin:auto;padding:24px}").replace("</style>", "</style>")
    head = T.page_header("NFL 2021 · weeks 1-8", "Pocket Clock", "Clean Pocket Time: seconds before a rusher gets within 2 yd of the QB.")
    html = f"<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Pocket Clock</title>{css}</head>" \
           f"<body style='margin:0;background:{T.BG};color:{T.TEXT};font-family:{T.FONT_BODY}'><div class='block-container'>{head}"
    for i, fg in enumerate(figs):
        fg.update_layout(template="pocket")
        html += f"<div style='margin-bottom:18px;background:{T.SURFACE};border:1px solid {T.BORDER};border-radius:12px;padding:12px'>" + pio.to_html(fg, full_html=False, include_plotlyjs="cdn" if i == 0 else False,
                                                                     config={"displayModeBar": False, "responsive": True}) + "</div>"
    html += "</div>"
    out = ROOT / "outputs" / "pocket_clock_dashboard.html"
    out.write_text(html + "</body></html>", encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
