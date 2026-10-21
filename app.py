"""Dashboard Pocket Clock.   streamlit run app.py   (nécessite d'avoir lancé `python run_all.py` une fois)"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import analysis as A
from src.load import CACHE_DIR, load_tables
from src.replay import play_figure

st.set_page_config(page_title="Pocket Clock", layout="wide")


@st.cache_data
def data():
    tab = pd.read_parquet(CACHE_DIR / "cpt_table.parquet")
    duels = pd.read_parquet(CACHE_DIR / "duels.parquet")
    pff = load_tables()["pffScoutingData"]
    return tab, duels, pff


@st.cache_data
def tracking_for(gameId):
    return pd.read_parquet(CACHE_DIR / "tracking.parquet", filters=[("gameId", "==", int(gameId))])


tab, duels, pff = data()
st.title("⏱️ Pocket Clock — combien de temps le QB a-t-il vraiment ?")
st.caption("Clean Pocket Time (CPT) : secondes entre le snap et le moment où un rusher passe à < 2 yd du QB. "
           "NFL 2021, semaines 1-8 (Big Data Bowl 2023).")
teams = sorted(tab.possessionTeam.unique())
mode = st.sidebar.radio("Je suis…", ["Coach offensif (ma ligne)", "Coach défensif (mon pass rush)"])
team = st.sidebar.selectbox("Équipe", teams, index=teams.index("KC") if "KC" in teams else 0)
off = mode.startswith("Coach offensif")
col = "possessionTeam" if off else "defensiveTeam"
mine = tab[tab[col] == team]
nfl_rmst, my_rmst = A.rmst(tab), A.rmst(mine)

c1, c2, c3 = st.columns(3)
c1.metric("Poche propre (RMST 3 s)", f"{my_rmst:.2f} s", f"{my_rmst - nfl_rmst:+.2f} s vs NFL", delta_color="normal" if off else "inverse")
c2.metric("Poches propres à 2,5 s", f"{A.clean_at(mine, 2.5):.0%}", f"{A.clean_at(mine, 2.5) - A.clean_at(tab, 2.5):+.0%} vs NFL",
          delta_color="normal" if off else "inverse")
c3.metric("Actions analysées", len(mine))

fig = go.Figure()
for df, name, color in ((tab, "Moyenne NFL", "#888"), (mine, team, "#d62828")):
    sf = A.km(df).survival_function_
    fig.add_scatter(x=sf.index, y=sf.iloc[:, 0] * 100, mode="lines", line=dict(shape="hv", width=3, color=color), name=name)
fig.update_layout(title="Horloge de la poche (% de poches encore propres)", xaxis_title="secondes depuis le snap",
                  yaxis_title="%", yaxis_range=[40, 100.5], xaxis_range=[0, 4.5], height=380)
st.plotly_chart(fig, width='stretch')

left, right = st.columns(2)
if off:
    bk = A.blocker_ranking(duels[duels.possessionTeam == team], min_duels=30)
    left.subheader("Où ma ligne craque : bloqueurs les plus battus")
    left.dataframe(bk[["blocker", "blocker_pos", "duels", "beaten_rate", "mean_entry_t"]].head(8).rename(columns={
        "blocker": "Joueur", "blocker_pos": "Poste", "duels": "Duels", "beaten_rate": "% battu", "mean_entry_t": "Arrivée moy. (s)"}),
        hide_index=True)
    rr = A.rusher_ranking(duels[duels.possessionTeam == team], min_rushes=15)
    right.subheader("Rushers adverses les plus dangereux contre moi")
else:
    rr = A.rusher_ranking(duels[duels.defensiveTeam == team], min_rushes=40)
    left.subheader("Mes meilleurs rushers (taux d'arrivée au QB)")
right_df = rr[["rusher", "rushes", "wins", "reach_rate", "entry_speed"]].head(8).rename(columns={
    "rusher": "Rusher", "rushes": "Rushs", "wins": "1er arrivé", "reach_rate": "% atteint QB", "entry_speed": "Vitesse (yd/s)"})
(right if off else left).dataframe(right_df, hide_index=True)

st.subheader("Rejouer une action")
sel = mine.sort_values("cpt")
sel = sel[~sel.censored].head(40)
opt = {f"{r.possessionTeam}-{r.defensiveTeam} · CPT {r.cpt:.1f}s · {r.passResult} · rusher {r.first_rusher}": (r.gameId, r.playId)
       for r in sel.itertuples()}
if opt:
    k = st.selectbox("Actions où la poche a craqué (les plus rapides d'abord)", list(opt))
    g, p = opt[k]
    st.plotly_chart(play_figure(tracking_for(g), pff, int(g), int(p), title=k), width='stretch')
st.caption("Limites : 8 semaines seulement, seuil de 2 yd arbitraire, la distance ne capte pas tout (blocs, lecture du QB).")
