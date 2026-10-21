"""Pocket Clock dashboard.   streamlit run app.py   (requires running `python run_all.py` once first)"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import analysis as A
from src import theme as T
from src.load import CACHE_DIR, load_tables
from src.replay import play_figure
from src.viz import TEAM_COLORS

st.set_page_config(page_title="Pocket Clock", layout="wide")
st.markdown(T.CSS, unsafe_allow_html=True)

MIN_PLAYS_TEAM = 20     # below this the team metrics are not shown
LOW_SAMPLE = 30         # below this a rusher-count bucket is flagged
GROUPS = (("4 or fewer rushers", lambda n: n <= 4), ("5 rushers", lambda n: n == 5), ("6+ rushers", lambda n: n >= 6))


@st.cache_data
def data():
    tab = pd.read_parquet(CACHE_DIR / "cpt_table.parquet")
    duels = pd.read_parquet(CACHE_DIR / "duels.parquet")
    pff = load_tables()["pffScoutingData"]
    return tab, duels, pff


@st.cache_data
def tracking_for(gameId):
    return pd.read_parquet(CACHE_DIR / "tracking.parquet", filters=[("gameId", "==", int(gameId))])


@st.cache_data
def rankings(_tab):
    return A.team_ranking(_tab, "possessionTeam"), A.team_ranking(_tab, "defensiveTeam")


def tone(delta, higher_is_better):
    """'good' / 'bad' / 'neutral' for a delta vs NFL, or 'neutral' when the metric is descriptive."""
    if higher_is_better is None or abs(delta) < 1e-9:
        return "neutral"
    return "good" if (delta > 0) == higher_is_better else "bad"


def stats(df):
    return dict(throw=df.duration.median(), sack=(df.passResult == "S").mean(), rushers=df.n_rushers.mean(), pressured=(~df.censored).mean())


def card(key, title, caption=""):
    """Bordered card; the CSS targets the `card_*` key."""
    box = st.container(border=True, key=f"card_{key}")
    box.markdown(T.card_title(title, caption), unsafe_allow_html=True)
    return box


tab, duels, pff = data()
ol_rk, dr_rk = rankings(tab)
teams = sorted(tab.possessionTeam.unique())

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown(T.brand(), unsafe_allow_html=True)
    st.markdown('<div class="side-label">Point of view</div>', unsafe_allow_html=True)
    mode = st.radio("Point of view", ["Offensive coach", "Defensive coach"], label_visibility="collapsed", key="mode")
    off = mode == "Offensive coach"
    st.markdown('<div class="side-label">Team</div>', unsafe_allow_html=True)
    team = st.selectbox("Team", teams, index=teams.index("KC") if "KC" in teams else 0,
                        format_func=lambda c: f"{T.TEAM_NAMES.get(c, c)} ({c})", label_visibility="collapsed", key="team")
    st.markdown(f'<dl class="facts"><dt>Season</dt><dd>2021, weeks 1–8</dd><dt>Plays</dt><dd>{len(tab):,}</dd>'
                '<dt>Threshold</dt><dd>Rusher &lt; 2 yd</dd></dl>', unsafe_allow_html=True)

col = "possessionTeam" if off else "defensiveTeam"
rk = ol_rk if off else dr_rk
mine = tab[tab[col] == team]
team_name = T.TEAM_NAMES.get(team, team)

st.markdown(T.page_header("Offense · Pass protection" if off else "Defense · Pass rush", team_name,
                          f"{len(mine):,} dropbacks · weeks 1–8, 2021 · compared with the NFL average"), unsafe_allow_html=True)
if len(mine) < MIN_PLAYS_TEAM:
    st.warning(f"Only {len(mine)} plays for {team_name}: not enough data to compute reliable metrics.")
    st.stop()

nfl_rmst, my_rmst = A.rmst(tab), A.rmst(mine)
nfl_c, my_c = A.clean_at(tab, 2.5), A.clean_at(mine, 2.5)
rank_tbl = rk.sort_values("rmst", ascending=not off).reset_index(drop=True)   # best first: longest pocket for a line, shortest for a rush
rank = int(rank_tbl.index[rank_tbl.team == team][0]) + 1 if team in set(rank_tbl.team) else None
ms, ns = stats(mine), stats(tab)

# ---------------------------------------------------------------- KPI widgets
big = st.columns(4)
d_rmst, d_c = my_rmst - nfl_rmst, my_c - nfl_c
rank_tone = "neutral" if not rank else ("good" if rank <= 11 else "bad" if rank >= 22 else "neutral")
big[0].markdown(T.kpi("Clean pocket · 3 s RMST", f"{my_rmst:.2f}", "s", f"{d_rmst:+.2f} s vs NFL {nfl_rmst:.2f} s", tone(d_rmst, off)), unsafe_allow_html=True)
big[1].markdown(T.kpi("Clean at 2.5 s", f"{my_c * 100:.0f}", "%", f"{d_c * 100:+.0f} pts vs NFL {nfl_c:.0%}", tone(d_c, off)), unsafe_allow_html=True)
big[2].markdown(T.kpi("League rank", f"#{rank}" if rank else "–", "of 32", "#1 = best" if rank else "Too few plays", rank_tone),
                unsafe_allow_html=True)
big[3].markdown(T.kpi("Plays analyzed", f"{len(mine):,}", "dropbacks", f"NFL avg {len(tab) / len(teams):.0f}", "neutral"), unsafe_allow_html=True)

small = st.columns(4)
for c, (label, val, delta, nfl_val, higher, fmt) in zip(small, [
        ("Median time to throw", f"{ms['throw']:.2f} s", ms["throw"] - ns["throw"], f"{ns['throw']:.2f} s", None, "{:+.2f} s"),
        ("Sack rate", f"{ms['sack']:.1%}", (ms["sack"] - ns["sack"]) * 100, f"{ns['sack']:.1%}", not off, "{:+.1f} pts"),
        ("Avg rushers faced" if off else "Avg rushers sent", f"{ms['rushers']:.2f}", ms["rushers"] - ns["rushers"], f"{ns['rushers']:.2f}", None, "{:+.2f}"),
        ("Plays under pressure", f"{ms['pressured']:.0%}", (ms["pressured"] - ns["pressured"]) * 100, f"{ns['pressured']:.0%}", not off, "{:+.0f} pts")]):
    shown = fmt.format(delta)
    if float(shown.split()[0]) == 0:     # "-0 pts" is noise: show "+0" and no verdict
        shown, higher = shown.replace("-", "+"), None
    c.markdown(T.kpi(label, val, "", f"{shown} vs NFL {nfl_val}", tone(delta, higher), small=True), unsafe_allow_html=True)
st.markdown(f'<p class="note" style="margin:.75rem 0 1.25rem">Better / Worse is judged from the {"offensive" if off else "defensive"} coach\'s view. '
            'Neutral = descriptive, not a quality signal (e.g. how many rushers the defense chose to send).</p>', unsafe_allow_html=True)

t_clock, t_league, t_players, t_replay, t_method = st.tabs(["Pocket clock", "League", "Players", "Replay", "Method"])

# ---------------------------------------------------------------- pocket clock
with t_clock:
    left, right = st.columns([2, 1])

    def edge(rule):
        """(plays, pts vs NFL, share clean at 2.5 s) for a rusher-count bucket, or None if too small."""
        sub, nsub = mine[rule(mine.n_rushers)], tab[rule(tab.n_rushers)]
        if len(sub) < 5:
            return None
        return len(sub), (A.clean_at(sub, 2.5) - A.clean_at(nsub, 2.5)) * 100, A.clean_at(sub, 2.5)

    with left:
        c = card("clock", "How long the pocket stays clean",
                 f"Share of {team} pockets still clean, by seconds since the snap. Shaded band = 95% confidence interval.")
        km_m = A.km(mine)
        ci = km_m.confidence_interval_survival_function_
        kn, sf = A.km(tab).survival_function_, km_m.survival_function_
        fig = go.Figure()
        fig.add_scatter(x=list(ci.index) + list(ci.index[::-1]), y=list(ci.iloc[:, 1] * 100) + list(ci.iloc[::-1, 0] * 100), fill="toself",
                        fillcolor="rgba(255,183,3,.14)", line=dict(width=0), hoverinfo="skip", showlegend=False)
        fig.add_scatter(x=kn.index, y=kn.iloc[:, 0] * 100, mode="lines", name="NFL average", line=dict(shape="hv", width=2, color=T.REF, dash="dash"))
        fig.add_scatter(x=sf.index, y=sf.iloc[:, 0] * 100, mode="lines", name=team, line=dict(shape="hv", width=3, color=T.ACCENT),
                        hovertemplate="%{x:.1f} s · %{y:.0f}% clean<extra>" + team + "</extra>")
        fig.add_vline(x=2.5, line=dict(color=T.SUBTLE, dash="dot", width=1), annotation_text="2.5 s", annotation_font_color=T.MUTED)
        fig.update_layout(xaxis_title="seconds since the snap", yaxis_title="% of pockets still clean", yaxis_range=[40, 100.5],
                          xaxis_range=[0, 4.5], height=380, hovermode="x unified")
        c.plotly_chart(fig, width="stretch", theme=None)

        rows = []
        for name, rule in GROUPS:
            sub, nsub = mine[rule(mine.n_rushers)], tab[rule(tab.n_rushers)]
            rows.append((name, len(sub), A.clean_at(sub, 2.5) if len(sub) >= 5 else np.nan, A.clean_at(nsub, 2.5)))
        b = card("rushers", "Clean at 2.5 s, by number of rushers", f"More rushers, shorter clock. Buckets under {LOW_SAMPLE} plays are flagged as low sample.")
        labels = [f"{n}<br><span style='font-size:11px'>{k} {team} plays{' · low sample' if k < LOW_SAMPLE else ''}</span>" for n, k, _, _ in rows]
        bar = go.Figure()
        bar.add_bar(x=labels, y=[r[2] * 100 for r in rows], name=team, marker_color=T.ACCENT,
                    text=[f"{r[2]:.0%}" if r[2] == r[2] else "n/a" for r in rows], textposition="outside", textfont=dict(color=T.ACCENT))
        bar.add_bar(x=labels, y=[r[3] * 100 for r in rows], name="NFL average", marker=dict(color=T.SURFACE_2, line=dict(color=T.REF, width=1.5)),
                    text=[f"{r[3]:.0%}" for r in rows], textposition="outside", textfont=dict(color=T.REF))
        bar.update_layout(barmode="group", yaxis=dict(range=[0, 112], title="% clean at 2.5 s"), height=320, bargap=.35)
        b.plotly_chart(bar, width="stretch", theme=None)

    with right:
        g = card("gauge", "Clean pockets at 2.5 s", "A typical deep-drop timing. Marker = NFL average.")
        gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=my_c * 100, number=dict(suffix="%", valueformat=".0f", font=dict(size=46, family=T.FONT_DISPLAY)),
            gauge=dict(axis=dict(range=[0, 100], tickcolor=T.SUBTLE, tickfont=dict(color=T.SUBTLE, size=11)), bar=dict(color=T.ACCENT, thickness=.5),
                       bgcolor=T.BORDER, borderwidth=0, threshold=dict(line=dict(color=T.TEXT, width=3), thickness=.9, value=nfl_c * 100))))
        gauge.update_layout(height=230, margin=dict(l=20, r=20, t=20, b=0))
        g.plotly_chart(gauge, width="stretch", theme=None)
        t_c = tone(d_c, off)
        g.markdown(f'<p class="cap"><span class="pill {t_c}">{T.WORD[t_c]}</span> &nbsp;{d_c * 100:+.0f} pts vs NFL average {nfl_c:.0%}</p>',
                   unsafe_allow_html=True)

        verdict = lambda d: "better" if (d > 0) == off else "worse"   # noqa: E731
        base, blitz = edge(GROUPS[0][1]), edge(GROUPS[2][1])
        late, nfl_late = A.clean_at(mine, 3.0), A.clean_at(tab, 3.0)
        items = []
        if base:
            items.append(f"<li><strong>Base rush: {verdict(base[1])} than the league.</strong> Against 4 or fewer rushers {base[2]:.0%} of pockets "
                         f"are clean at 2.5 s, {base[1]:+.0f} pts vs the league ({base[0]} plays).</li>")
        if blitz:
            items.append(f"<li><strong>Blitz (6+ rushers): {verdict(blitz[1])} than the league.</strong> {blitz[2]:.0%} clean at 2.5 s, "
                         f"{blitz[1]:+.0f} pts vs the league ({blitz[0]} plays{' · low sample' if blitz[0] < LOW_SAMPLE else ''}).</li>")
        items.append(f"<li><strong>Late clock.</strong> {late:.0%} of pockets survive to 3 s (NFL {nfl_late:.0%}); "
                     "longer-developing concepts depend on this.</li>")
        i = card("insights", "What the clock says", f"Computed from the {len(mine):,} {team} plays.")
        i.markdown(f'<ol class="insights">{"".join(items)}</ol>', unsafe_allow_html=True)

# ---------------------------------------------------------------- league
with t_league:
    c = card("league", "Who keeps the pocket clean longest" if off else "Who breaks the pocket fastest",
             "Gap to the NFL average in clean-pocket time (3 s RMST). "
             + ("Right of the line = pocket stays clean longer than average. " if off else "Left of the line = pocket breaks faster than average. ")
             + "Bars in official team colors; dark colors get a light outline.")
    r = rk.assign(dev=rk.rmst - rk.rmst.mean()).sort_values("dev", ascending=off)
    colors = [TEAM_COLORS.get(t, "#888") for t in r.team]
    outline = [T.ACCENT if t == team else (T.OUTLINE if T.needs_outline(c_) else "rgba(0,0,0,0)") for t, c_ in zip(r.team, colors)]
    fig = go.Figure(go.Bar(
        x=r.dev, y=[("▶ " if t == team else "") + t for t in r.team], orientation="h",
        marker=dict(color=colors, line=dict(color=outline, width=[3 if t == team else 1.5 for t in r.team])),
        customdata=np.stack([r.n, r["clean_2.5s"], r.rmst, [T.TEAM_NAMES.get(t, t) for t in r.team]], axis=1),
        text=[f"{v:+.2f}" for v in r.dev], textposition="outside", textfont=dict(color=T.MUTED),
        hovertemplate="<b>%{customdata[3]}</b><br>%{x:+.2f} s vs NFL<br>RMST %{customdata[2]:.2f} s · %{customdata[1]:.0%} clean at 2.5 s"
                      "<br>%{customdata[0]} plays<extra></extra>"))
    m = r.dev.abs().max() * 1.3
    fig.update_layout(height=860, xaxis=dict(range=[-m, m], title="gap vs NFL average, seconds"), bargap=.25, margin=dict(l=10, r=40, t=10, b=10))
    c.plotly_chart(fig, width="stretch", theme=None)
    c.markdown('<p class="note">▶ = selected team</p>', unsafe_allow_html=True)

    if off:
        o = A.team_over_expected(tab).sort_values("over_expected")
        c2 = card("over", "Over expected · scheme-adjusted",
                  "Actual − expected RMST from a Cox model (rushers, play action, down, distance, formation, coverage).")
        fig = go.Figure(go.Bar(x=o.over_expected, y=[("▶ " if t == team else "") + t for t in o.team], orientation="h",
                               marker_color=[T.GOOD if v >= 0 else T.BAD for v in o.over_expected],
                               hovertemplate="<b>%{y}</b> %{x:+.2f} s above expected<extra></extra>"))
        fig.update_layout(height=780, xaxis_title="seconds above expected", margin=dict(l=10, r=10, t=10, b=10))
        c2.plotly_chart(fig, width="stretch", theme=None)

# ---------------------------------------------------------------- players
with t_players:
    pl, pr = st.columns(2)
    if off:
        bk = A.blocker_ranking(duels[duels.possessionTeam == team], min_duels=30)
        with pl:
            cb = card("blockers", f"Most-beaten {team} blockers", "Beaten = the assigned rusher entered the 2 yd circle. Min. 30 duels.")
            if bk.empty:
                cb.info("No blocker has enough duels (30+) for this team.")
            else:
                cb.dataframe(bk.assign(beaten_rate=bk.beaten_rate * 100)[["blocker", "blocker_pos", "duels", "beaten_rate", "mean_entry_t"]].head(10),
                             hide_index=True, width="stretch",
                             column_config={"blocker": "Player", "blocker_pos": "Pos", "duels": "Duels",
                                            "beaten_rate": st.column_config.ProgressColumn("Beaten", format="%.0f%%", min_value=0, max_value=100),
                                            "mean_entry_t": st.column_config.NumberColumn("Avg arrival (s)", format="%.2f")})
        rr = A.rusher_ranking(duels[duels.possessionTeam == team], min_rushes=15)
        rtitle, rcap = "Most dangerous opposing rushers", "Rushers who reached the QB most often against this offense. Min. 15 rushes."
    else:
        rr = A.rusher_ranking(duels[duels.defensiveTeam == team], min_rushes=40)
        rtitle, rcap = f"Best {team} rushers", "Share of rushes reaching the QB within 2 yd. Min. 40 rushes."
    with (pr if off else pl):
        cr = card("rushers_tbl", rtitle, rcap)
        if rr.empty:
            cr.info("No rusher has enough rushes for this selection.")
        else:
            cr.dataframe(rr.assign(reach_rate=rr.reach_rate * 100)[["rusher", "rushes", "wins", "reach_rate", "entry_speed"]].head(10),
                         hide_index=True, width="stretch",
                         column_config={"rusher": "Rusher", "rushes": "Rushes", "wins": "First",
                                        "reach_rate": st.column_config.ProgressColumn("Reached QB", format="%.0f%%", min_value=0, max_value=40),
                                        "entry_speed": st.column_config.NumberColumn("yd/s", format="%.1f")})

    top = A.rusher_ranking(duels, min_rushes=150).head(15).iloc[::-1]
    ct = card("top15", "Top 15 pass rushers, NFL", "Bar = times first to break the pocket. Label = times first · mean seconds to break it. Min. 150 rushes.")
    fig = go.Figure(go.Bar(x=top.wins, y=top.rusher, orientation="h", marker_color=T.ACCENT,
                           text=[f"{w:.0f} · {t:.2f} s" for w, t in zip(top.wins, top.cpt_when_first)], textposition="outside", textfont=dict(color=T.MUTED),
                           customdata=np.stack([top.rushes, top.reach_rate * 100], axis=1),
                           hovertemplate="<b>%{y}</b><br>%{x:.0f} pockets broken in %{customdata[0]:.0f} rushes<br>"
                                         "%{customdata[1]:.0f}% of rushes reach the QB<extra></extra>"))
    fig.update_layout(height=520, xaxis=dict(range=[0, top.wins.max() * 1.25], title="pockets broken (count)"))
    ct.plotly_chart(fig, width="stretch", theme=None)

# ---------------------------------------------------------------- replay
with t_replay:
    cp = card("replay", "Replay a play", "The circle is the 2 yd radius around the QB: white while the pocket is clean, red once a rusher gets through.")
    sel = mine.sort_values("cpt")
    sel = sel[~sel.censored & (sel.cpt >= 0.5)].head(40)   # cpt 0.0 = a rusher already within 2 yd at the snap, not a pocket collapse
    opt = {f"{r.possessionTeam} vs {r.defensiveTeam} · CPT {r.cpt:.1f}s · {r.passResult} · rusher {r.first_rusher}": (r.gameId, r.playId)
           for r in sel.itertuples()}
    if opt:
        k_ = cp.selectbox("Plays where the pocket broke (fastest first)", list(opt), key=f"replay_{col}_{team}")
        gid, pid = opt[k_]
        cp.plotly_chart(play_figure(tracking_for(gid), pff, int(gid), int(pid), title=k_), width="stretch", theme=None)
    else:
        cp.info("No broken-pocket play for this selection.")

# ---------------------------------------------------------------- method
with t_method:
    a, b = st.columns(2)
    with a:
        cm = card("method", "Method")
        cm.markdown("""
- **CPT** = first frame where a rusher is < 2 yd from the QB − snap, divided by 10.
- Plays with no arrival are **censored**; team rankings use **RMST** (area under the Kaplan-Meier curve over 3 s).
- **Expected CPT**: Cox regression on play context, so a line is not penalized for facing blitzes.
- **Duels**: `pff_nflIdBlockedPlayer` links each rusher to his assigned blocker.
- **Validation**: sacks have the shortest pockets, more rushers shorten the pocket, φ = 0.61 with PFF pressures.
""")
    with b:
        cl = card("limits", "Limitations")
        cl.markdown("""
- Only 8 weeks (~250 plays per team): read gaps as trends.
- The 2 yd threshold is arbitrary; rankings are moderately stable (Spearman 0.45-0.73).
- 68% of plays are censored (the QB throws before the pocket breaks).
- Distance ignores block quality and the QB's reads; tracking stops at the throw.
""")
st.markdown('<p class="note" style="text-align:center;margin-top:2rem">Pocket Clock · NFL Big Data Bowl 2023 data · built with Streamlit &amp; Plotly</p>',
            unsafe_allow_html=True)
