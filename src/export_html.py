"""Version HTML autonome (sans serveur) : python -m src.export_html -> outputs/pocket_clock_dashboard.html"""
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from . import analysis as A
from .load import CACHE_DIR, ROOT, load_tables
from .replay import play_figure
from .viz import TEAM_COLORS


def main():
    tab = pd.read_parquet(CACHE_DIR / "cpt_table.parquet")
    trk = pd.read_parquet(CACHE_DIR / "tracking.parquet")
    pff = load_tables()["pffScoutingData"]
    figs = []
    # 1) classement interactif lignes offensives
    ol = A.team_ranking(tab, "possessionTeam").sort_values("rmst")
    f = go.Figure(go.Bar(x=ol.rmst - ol.rmst.mean(), y=ol.team, orientation="h", marker_color=[TEAM_COLORS[t] for t in ol.team],
                         customdata=ol[["n", "clean_2.5s"]], hovertemplate="%{y}: %{x:+.2f} s vs moyenne<br>%{customdata[0]} actions · %{customdata[1]:.0%} propres à 2,5 s<extra></extra>"))
    f.update_layout(title="Protection des lignes offensives : écart de poche propre vs moyenne NFL (s)", height=800)
    figs.append(f)
    # 2) horloge de la poche, une courbe par équipe (menu déroulant)
    f = go.Figure(); teams = sorted(tab.possessionTeam.unique())
    base = A.km(tab).survival_function_
    for i, tm in enumerate(teams):
        sf = A.km(tab[tab.possessionTeam == tm]).survival_function_
        f.add_scatter(x=sf.index, y=sf.iloc[:, 0] * 100, line=dict(shape="hv", color=TEAM_COLORS[tm], width=3), name=tm, visible=(i == 0))
    f.add_scatter(x=base.index, y=base.iloc[:, 0] * 100, line=dict(shape="hv", color="#888", dash="dash"), name="Moyenne NFL")
    f.update_layout(title="Horloge de la poche par équipe offensive (Kaplan-Meier)", yaxis_range=[40, 100.5], xaxis_range=[0, 4.5],
                    xaxis_title="secondes depuis le snap", yaxis_title="% poches propres",
                    updatemenus=[dict(buttons=[dict(label=tm, method="update", args=[{"visible": [j == i for j in range(len(teams))] + [True]}]) for i, tm in enumerate(teams)])])
    figs.append(f)
    # 3) rejeux des 3 sacks les plus rapides
    sk = tab[(tab.passResult == "S") & ~tab.censored & (tab.cpt >= 0.5)].sort_values("cpt").head(3)
    for r in sk.itertuples():
        figs.append(play_figure(trk[trk.gameId == r.gameId], pff, int(r.gameId), int(r.playId),
                                title=f"{r.possessionTeam} vs {r.defensiveTeam} — sack, rusher {r.first_rusher}"))
    html = "<html><head><meta charset='utf-8'><title>Pocket Clock</title></head><body style='font-family:sans-serif;max-width:1000px;margin:auto'>" \
           "<h1>⏱️ Pocket Clock — NFL 2021 sem. 1-8</h1><p>Clean Pocket Time : secondes avant qu'un rusher passe à &lt; 2 yd du QB.</p>"
    for i, fg in enumerate(figs):
        html += pio.to_html(fg, full_html=False, include_plotlyjs="cdn" if i == 0 else False)
    out = ROOT / "outputs" / "pocket_clock_dashboard.html"
    out.write_text(html + "</body></html>", encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
