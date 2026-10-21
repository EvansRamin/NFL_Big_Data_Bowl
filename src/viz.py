"""Step 4: visualizations (PNG + GIF). Titles = conclusions, sources in the footer."""
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
SRC = "Source: NFL Big Data Bowl 2023, NFL 2021 season weeks 1-8 (8,532 pass plays) · CPT = seconds before a rusher gets within 2 yd of the QB"
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
    """Diverging bars centered on the NFL average (honest axis: no truncated bars)."""
    ref = rk[col].mean() if ref is None else ref
    rk = rk.assign(dev=rk[col] - ref).sort_values("dev")
    fig, ax = plt.subplots(figsize=(9, 10))
    ax.barh(rk.team, rk.dev, color=[TEAM_COLORS.get(t, "#888") for t in rk.team], height=0.75)
    ax.axvline(0, color=INK, lw=1)
    m = rk.dev.abs().max()
    for y, v in enumerate(rk.dev):
        ax.text(v + (0.004 if v >= 0 else -0.004), y, f"{v:+.2f}", va="center", ha="left" if v >= 0 else "right", fontsize=8, color=INK)
    ax.set_xlim(-m * 1.25, m * 1.25)
    ax.set_xlabel(xlabel + (f"  (0 = NFL average, {ref:.2f} s)" if col != "over_expected" else ""))
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
    ax.set_xlabel("Seconds since the snap"); ax.set_ylabel("% of pockets still clean")
    ax.grid(alpha=0.25); ax.legend(frameon=False, loc="lower left")
    _style(ax, title, sub)
    _save(fig, name)


def draw_field(ax, x0, x1, y0=0, y1=53.3):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color="#2e7d32", zorder=0))
    for x in range(int(np.ceil(x0 / 5)) * 5, int(x1) + 1, 5):
        ax.plot([x, x], [y0, y1], color="white", lw=1.4 if x % 10 == 0 else 0.5, alpha=0.5, zorder=1)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.axis("off")


def animate(t: dict, gameId: int, playId: int, name: str, radius=PRESSURE_RADIUS, row=None):
    """GIF of a play: dots per group, circle around the QB (red once crossed), timer."""
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
        ttl.set_text(ctitle + ("BROKEN at %.1f s" % ((hit[0] - snap) / FPS) if broken else "clean pocket"))
        return []
    upd(frames[0]); hit[0] = None
    ani = FuncAnimation(fig, upd, frames=frames + [frames[-1]] * 8, interval=100, blit=False)
    ani.save(OUT / name, writer=PillowWriter(fps=FPS))
    plt.close(fig)
    print("  ->", name)


def make_all(t: dict, tab: pd.DataFrame, duels: pd.DataFrame):
    OUT.mkdir(exist_ok=True)
    avg = A.rmst(tab)
    # 1) offensive lines
    ol = A.team_ranking(tab, "possessionTeam"); ol.to_csv(OUT / "ranking_offensive_lines.csv", index=False)
    best, worst = ol.iloc[0], ol.iloc[-1]
    team_bars(ol, "01_offensive_line_ranking.png",
              f"{best.team} vs {worst.team} : {best.rmst - worst.rmst:.2f} s of clean pocket separate the best and worst line",
              "Mean clean-pocket time over the first 3 seconds (RMST), longer = better protection",
              "Clean-pocket gap vs average (s)")
    # 2) defenses / pass rush
    dr = A.team_ranking(tab, "defensiveTeam"); dr.to_csv(OUT / "ranking_pass_rush_teams.csv", index=False)
    team_bars(dr.assign(rmst=dr.rmst), "02_pass_rush_team_ranking.png",
              f"The {dr.iloc[-1].team} pass rush breaks the pocket fastest in the NFL",
              "Mean clean-pocket time imposed on the opposing offense (shorter = better rush)", "Clean-pocket gap vs average (s)")
    # 3) rushers
    rr = A.rusher_ranking(duels); rr.to_csv(OUT / "ranking_rushers.csv", index=False)
    top = rr.head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 6.5))
    ax.barh(top.rusher, top.reach_rate * 100, color="#d62828")
    for y, (v, n, w) in enumerate(zip(top.reach_rate * 100, top.rushes, top.wins)):
        ax.text(v, y, f" {v:.0f}%  ({int(w)} times first in {n} rushes)", va="center", fontsize=8)
    ax.set_xlim(0, top.reach_rate.max() * 100 * 1.35); ax.set_xlabel("% of rushes where he reaches the QB (< 2 yd) before the throw")
    _style(ax, f"{rr.iloc[0].rusher} reaches the QB on {rr.iloc[0].reach_rate:.0%} of his rushes",
           "Top 15 pass rushers (≥ 150 rushes), rate of arriving within 2 yd of the QB")
    _save(fig, "03_top_pass_rushers.png")
    # 4) pocket clock
    tab = tab.assign(rush_grp=np.where(tab.n_rushers <= 4, "4 or fewer", np.where(tab.n_rushers == 5, "5", "6+")))
    km_curves(tab, "rush_grp", {"4 or fewer": "4 rushers or fewer", "5": "5 rushers", "6+": "6+ rushers"},
              "04_pocket_clock_by_rushers.png",
              f"At 2.5 s, {A.clean_at(tab[tab.rush_grp=='4 or fewer'],2.5):.0%} of pockets hold against 4 rushers, {A.clean_at(tab[tab.rush_grp=='6+'],2.5):.0%} against 6+",
              "Pocket clock: % of pockets still clean (Kaplan-Meier, censored plays included)")
    cov = tab[tab.pff_passCoverageType.isin(["Man", "Zone"])]
    km_curves(cov, "pff_passCoverageType", {"Man": "Man coverage", "Zone": "Zone coverage"},
              "05_pocket_clock_man_vs_zone.png", "Man or zone: the pocket holds the same, the number of rushers is what matters",
              "Pocket clock by coverage type")
    # 5) expected vs actual CPT
    oe = A.team_over_expected(tab); oe.to_csv(OUT / "ranking_over_expected.csv", index=False)
    team_bars(oe, "06_cpt_over_expected.png",
              f"{oe.iloc[0].team} protects {oe.iloc[0].over_expected:+.2f} s above what its scheme predicts",
              "Actual − expected RMST (Cox model: rusher count, play action, down, distance, formation, coverage)",
              "Clean-pocket seconds above expected", col="over_expected", ref=0)
    # 6) QB internal clock
    q = tab.dropna(subset=["qb"]).groupby("qb").filter(lambda g: len(g) >= 80)
    qs = q.groupby("qb").apply(lambda g: pd.Series({"n": len(g), "throw_t": g.duration.median(), "rmst": A.rmst(g),
                                                   "pressured": (~g.censored).mean()}), include_groups=False).reset_index()
    qs.to_csv(OUT / "qb_clock.csv", index=False)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(qs.throw_t, qs.rmst, s=qs.n * 0.8, color="#264653", alpha=0.7)
    for _, r in qs.iterrows():
        ax.text(r.throw_t, r.rmst, " " + r.qb.split()[-1], fontsize=8)
    ax.set_xlabel("Median time to throw / sack (s)"); ax.set_ylabel("Clean-pocket time (RMST, s)")
    ax.grid(alpha=0.25)
    _style(ax, "QB internal clocks: who throws before the pocket cracks?",
           "Each dot = one QB (≥ 80 plays). Top left: reads fast, clean pocket; right: holds the ball a long time")
    _save(fig, "07_qb_internal_clock.png")
    # 7) duels
    bk = A.blocker_ranking(duels); bk.to_csv(OUT / "ranking_blockers.csv", index=False)
    # 8) robustness
    rob = pd.DataFrame({f"{r} yd": A.team_ranking(tab, "possessionTeam", cpt=("cpt" if r == 2.0 else f"cpt_{r}")).set_index("team")["rank"]
                        for r in (1.5, 2.0, 3.0)})
    rob.index.name = "team"; rob = rob.sort_values("2.0 yd"); rob.to_csv(OUT / "robustness_ol_ranking.csv")
    print("  robustness spearman:\n", rob.corr(method="spearman").round(2))
    # 9) GIF of the fastest sack
    sk = tab[(tab.passResult == "S") & ~tab.censored].sort_values("cpt")
    sk = sk[sk.cpt >= 0.5]
    r = sk.iloc[0]
    animate(t, int(r.gameId), int(r.playId), "08_fastest_sack.gif", row=r)
    print(f"  GIF : {r.possessionTeam}-{r.defensiveTeam}, CPT={r.cpt:.1f}s, rusher={r.first_rusher}")
    return {"ol": ol, "dr": dr, "rr": rr, "oe": oe, "qs": qs, "bk": bk, "rob": rob, "fast_sack": r}
