"""Étape 4 : visualisations (PNG + GIF). Titres = conclusions, sources en pied de page."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Circle, Rectangle

from . import analysis as A
from .load import FPS, ROOT
from .metrics import PRESSURE_RADIUS

OUT = ROOT / "outputs"
SRC = "Source : NFL Big Data Bowl 2023, saison NFL 2021 sem. 1-8 (8 532 actions de passe) · CPT = secondes avant qu'un rusher passe à < 2 yd du QB"
TEAM_COLORS = {
    "ARI": "#97233F", "ATL": "#A71930", "BAL": "#241773", "BUF": "#00338D", "CAR": "#0085CA", "CHI": "#0B162A",
    "CIN": "#FB4F14", "CLE": "#FF3C00", "DAL": "#003594", "DEN": "#FB4F14", "DET": "#0076B6", "GB": "#203731",
    "HOU": "#03202F", "IND": "#002C5F", "JAX": "#006778", "KC": "#E31837", "LA": "#003594", "LAC": "#0080C6",
    "LV": "#000000", "MIA": "#008E97", "MIN": "#4F2683", "NE": "#002244", "NO": "#D3BC8D", "NYG": "#0B2265",
    "NYJ": "#125740", "PHI": "#004C54", "PIT": "#FFB612", "SEA": "#69BE28", "SF": "#AA0000", "TB": "#D50A0A",
    "TEN": "#4B92DB", "WAS": "#5A1414"}
INK, MUTED, RED = "#1f2430", "#6b7280", "#d62828"


def _style(ax, title, sub=None):
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold", color=INK, pad=22 if sub else 10)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=10, color=MUTED)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def _foot(fig, extra=""):
    fig.text(0.01, 0.005, SRC + extra, fontsize=7, color=MUTED, ha="left", va="bottom")


def _save(fig, name):
    OUT.mkdir(exist_ok=True)
    _foot(fig)
    fig.savefig(OUT / name, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  ->", name)


def team_bars(rk: pd.DataFrame, name: str, title: str, sub: str, xlabel: str, col="rmst", ref=None):
    """Barres divergentes centrées sur la moyenne NFL (axe honnête : pas de barres tronquées)."""
    ref = rk[col].mean() if ref is None else ref
    rk = rk.assign(dev=rk[col] - ref).sort_values("dev")
    fig, ax = plt.subplots(figsize=(9, 10))
    ax.barh(rk.team, rk.dev, color=[TEAM_COLORS.get(t, "#888") for t in rk.team], height=0.75)
    ax.axvline(0, color=INK, lw=1)
    m = rk.dev.abs().max()
    for y, v in enumerate(rk.dev):
        ax.text(v + (0.004 if v >= 0 else -0.004), y, f"{v:+.2f}", va="center", ha="left" if v >= 0 else "right", fontsize=8, color=INK)
    ax.set_xlim(-m * 1.25, m * 1.25)
    ax.set_xlabel(xlabel + (f"  (0 = moyenne NFL, {ref:.2f} s)" if col != "over_expected" else ""))
    _style(ax, title, sub)
    _save(fig, name)


def km_curves(tab, by, labels, name, title, sub):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    cols = ["#2a9d8f", "#e9a100", RED, "#6a4c93"]
    for (key, lab), c in zip(labels.items(), cols):
        g = tab[tab[by] == key] if not callable(by) else tab[by(tab) == key]
        k = A.km(g)
        sf = k.survival_function_
        ax.step(sf.index, sf.iloc[:, 0] * 100, where="post", color=c, lw=2.4, label=f"{lab} (n={len(g)})")
    ax.set_xlim(0, 4.5); ax.set_ylim(40, 100.5)
    ax.set_xlabel("Secondes depuis le snap"); ax.set_ylabel("% de poches encore propres")
    ax.grid(alpha=0.25); ax.legend(frameon=False, loc="lower left")
    _style(ax, title, sub)
    _save(fig, name)


def draw_field(ax, x0, x1, y0=0, y1=53.3):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color="#2e7d32", zorder=0))
    for x in range(int(np.ceil(x0 / 5)) * 5, int(x1) + 1, 5):
        ax.plot([x, x], [y0, y1], color="white", lw=1.4 if x % 10 == 0 else 0.5, alpha=0.5, zorder=1)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.axis("off")


def animate(t: dict, gameId: int, playId: int, name: str, radius=PRESSURE_RADIUS, row=None):
    """GIF d'une action : points par équipe, cercle autour du QB (rouge quand franchi), chronomètre."""
    trk, pff = t["tracking"], t["pffScoutingData"]
    a = trk[(trk.gameId == gameId) & (trk.playId == playId)].merge(
        pff[pff.gameId.eq(gameId) & pff.playId.eq(playId)][["nflId", "pff_role"]], on="nflId", how="left")
    frames = sorted(a.frameId.unique())
    qb = a[a.pff_role == "Pass"].set_index("frameId")
    cx, cy = qb.x.mean(), qb.y.mean()
    fig, ax = plt.subplots(figsize=(9, 5.5))
    draw_field(ax, cx - 13, cx + 11, max(0, cy - 12), min(53.3, cy + 12))
    off = (row["possessionTeam"] if row is not None else None)
    ctitle = (f"{row['possessionTeam']} vs {row['defensiveTeam']} — " if row is not None else "")
    ttl = ax.text(0.01, 0.97, "", transform=ax.transAxes, color="white", fontsize=9, fontweight="bold", va="top")
    clk = ax.text(0.99, 0.03, "", transform=ax.transAxes, color="white", fontsize=14, fontweight="bold", va="bottom", ha="right")
    circ = Circle((0, 0), radius, fill=False, lw=3, color="white", zorder=5); ax.add_patch(circ)
    sc = {k: ax.scatter([], [], s=90, zorder=4, edgecolor="black", linewidth=0.6) for k in ("off", "def", "qb", "rush", "ball")}
    sc["off"].set_color("#4cc9f0"); sc["def"].set_color("#f4a261"); sc["qb"].set_color("#ffd60a"); sc["qb"].set_sizes([160])
    sc["rush"].set_color("#e63946"); sc["ball"].set_color("#6f4518"); sc["ball"].set_sizes([30])
    snap = a.snap_frame.iloc[0]
    hit = [None]

    def upd(f):
        d = a[a.frameId == f]
        isball = d.team.astype(str) == "football"
        role = d.pff_role
        qbrow = d[role == "Pass"]
        rush = d[role == "Pass Rush"]
        rest = d[~isball & ~role.isin(["Pass", "Pass Rush"])]
        offs = rest[rest.pff_role.isin(["Pass Block", "Pass Route"]) | (rest.pff_role.isna())]
        defs = rest[rest.pff_role == "Coverage"]
        sc["off"].set_offsets(offs[["x", "y"]].to_numpy()); sc["def"].set_offsets(defs[["x", "y"]].to_numpy())
        sc["qb"].set_offsets(qbrow[["x", "y"]].to_numpy()); sc["rush"].set_offsets(rush[["x", "y"]].to_numpy())
        sc["ball"].set_offsets(d[isball][["x", "y"]].to_numpy())
        if len(qbrow):
            circ.center = (qbrow.x.iloc[0], qbrow.y.iloc[0])
            dist = np.hypot(rush.x - qbrow.x.iloc[0], rush.y - qbrow.y.iloc[0])
            if (dist < radius).any() and hit[0] is None:
                hit[0] = f
        broken = hit[0] is not None
        circ.set_color("#ff1d1d" if broken else "white"); circ.set_linewidth(4 if broken else 3)
        clk.set_text(f"{(f - snap) / FPS:4.1f} s")
        ttl.set_text(ctitle + ("ROMPUE à %.1f s" % ((hit[0] - snap) / FPS) if broken else "poche propre"))
        return []
    upd(frames[0]); hit[0] = None
    ani = FuncAnimation(fig, upd, frames=frames + [frames[-1]] * 8, interval=100, blit=False)
    ani.save(OUT / name, writer=PillowWriter(fps=FPS))
    plt.close(fig)
    print("  ->", name)


def make_all(t: dict, tab: pd.DataFrame, duels: pd.DataFrame):
    OUT.mkdir(exist_ok=True)
    avg = A.rmst(tab)
    # 1) lignes offensives
    ol = A.team_ranking(tab, "possessionTeam"); ol.to_csv(OUT / "ranking_offensive_lines.csv", index=False)
    best, worst = ol.iloc[0], ol.iloc[-1]
    team_bars(ol, "01_classement_lignes_offensives.png",
              f"{best.team} vs {worst.team} : {best.rmst - worst.rmst:.2f} s de poche propre d'écart entre la meilleure et la pire ligne",
              "Temps moyen de poche propre sur les 3 premières secondes (RMST), plus long = meilleure protection",
              "Écart de poche propre vs moyenne (s)")
    # 2) défenses / pass rush
    dr = A.team_ranking(tab, "defensiveTeam"); dr.to_csv(OUT / "ranking_pass_rush_teams.csv", index=False)
    team_bars(dr.assign(rmst=dr.rmst), "02_classement_pass_rush_equipes.png",
              f"Le pass rush des {dr.iloc[-1].team} casse la poche le plus vite de la NFL",
              "Temps moyen de poche propre imposé à l'attaque adverse (plus court = meilleur rush)", "Écart de poche propre vs moyenne (s)")
    # 3) rushers
    rr = A.rusher_ranking(duels); rr.to_csv(OUT / "ranking_rushers.csv", index=False)
    top = rr.head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 6.5))
    ax.barh(top.rusher, top.reach_rate * 100, color="#d62828")
    for y, (v, n, w) in enumerate(zip(top.reach_rate * 100, top.rushes, top.wins)):
        ax.text(v, y, f" {v:.0f}%  ({int(w)} fois 1er sur {n} rushs)", va="center", fontsize=8)
    ax.set_xlim(0, top.reach_rate.max() * 100 * 1.35); ax.set_xlabel("% des rushs où il atteint le QB (< 2 yd) avant le lancer")
    _style(ax, f"{rr.iloc[0].rusher} atteint le QB sur {rr.iloc[0].reach_rate:.0%} de ses rushs",
           "Top 15 pass rushers (≥ 150 rushs), taux d'arrivée à < 2 yd du QB")
    _save(fig, "03_top_pass_rushers.png")
    # 4) horloge de la poche
    tab = tab.assign(rush_grp=np.where(tab.n_rushers <= 4, "4 ou moins", np.where(tab.n_rushers == 5, "5", "6+")))
    km_curves(tab, "rush_grp", {"4 ou moins": "4 rushers ou moins", "5": "5 rushers", "6+": "6 rushers et +"},
              "04_horloge_poche_par_rushers.png",
              f"À 2,5 s, {A.clean_at(tab[tab.rush_grp=='4 ou moins'],2.5):.0%} des poches tiennent à 4 rushers, {A.clean_at(tab[tab.rush_grp=='6+'],2.5):.0%} à 6+",
              "Horloge de la poche : % de poches encore propres (Kaplan-Meier, actions censurées incluses)")
    cov = tab[tab.pff_passCoverageType.isin(["Man", "Zone"])]
    km_curves(cov, "pff_passCoverageType", {"Man": "Couverture Man", "Zone": "Couverture Zone"},
              "05_horloge_poche_man_vs_zone.png", "Man ou zone : la poche tient pareil, c'est le nombre de rushers qui compte",
              "Horloge de la poche selon le type de couverture")
    # 5) CPT attendu vs réel
    oe = A.team_over_expected(tab); oe.to_csv(OUT / "ranking_over_expected.csv", index=False)
    team_bars(oe, "06_cpt_au_dessus_attendu.png",
              f"{oe.iloc[0].team} protège {oe.iloc[0].over_expected:+.2f} s au-dessus de ce que son schéma laisse prévoir",
              "RMST réel − attendu (modèle de Cox : nb de rushers, play action, down, distance, formation, couverture)",
              "Secondes de poche propre au-dessus de l'attendu", col="over_expected", ref=0)
    # 6) QB horloge interne
    q = tab.dropna(subset=["qb"]).groupby("qb").filter(lambda g: len(g) >= 80)
    qs = q.groupby("qb").apply(lambda g: pd.Series({"n": len(g), "throw_t": g.duration.median(), "rmst": A.rmst(g),
                                                   "pressured": (~g.censored).mean()}), include_groups=False).reset_index()
    qs.to_csv(OUT / "qb_clock.csv", index=False)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(qs.throw_t, qs.rmst, s=qs.n * 0.8, color="#264653", alpha=0.7)
    for _, r in qs.iterrows():
        ax.text(r.throw_t, r.rmst, " " + r.qb.split()[-1], fontsize=8)
    ax.set_xlabel("Temps médian avant lancer / sack (s)"); ax.set_ylabel("Temps de poche propre (RMST, s)")
    ax.grid(alpha=0.25)
    _style(ax, "L'horloge interne des QB : qui lance avant que la poche ne craque ?",
           "Chaque point = un QB (≥ 80 actions). En haut à gauche : lit vite, poche propre ; à droite : garde longtemps le ballon")
    _save(fig, "07_qb_horloge_interne.png")
    # 7) duels
    bk = A.blocker_ranking(duels); bk.to_csv(OUT / "ranking_blockers.csv", index=False)
    # 8) robustesse
    rob = pd.DataFrame({f"{r} yd": A.team_ranking(tab, "possessionTeam", cpt=("cpt" if r == 2.0 else f"cpt_{r}")).set_index("team")["rank"]
                        for r in (1.5, 2.0, 3.0)})
    rob.index.name = "team"; rob = rob.sort_values("2.0 yd"); rob.to_csv(OUT / "robustesse_classement_OL.csv")
    print("  robustesse spearman:\n", rob.corr(method="spearman").round(2))
    # 9) GIF du sack le plus rapide
    sk = tab[(tab.passResult == "S") & ~tab.censored].sort_values("cpt")
    sk = sk[sk.cpt >= 0.5]
    r = sk.iloc[0]
    animate(t, int(r.gameId), int(r.playId), "08_sack_le_plus_rapide.gif", row=r)
    print(f"  GIF : {r.possessionTeam}-{r.defensiveTeam}, CPT={r.cpt:.1f}s, rusher={r.first_rusher}")
    return {"ol": ol, "dr": dr, "rr": rr, "oe": oe, "qs": qs, "bk": bk, "rob": rob, "fast_sack": r}
