"""Statistiques sur le CPT : courbes de survie (Kaplan-Meier), RMST, classements, CPT attendu (Cox)."""
import warnings

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter, KaplanMeierFitter

warnings.filterwarnings("ignore")
HORIZON = 3.0   # s : fenêtre sur laquelle on mesure la "poche propre" (RMST)
MIN_PLAYS = 60  # actions min pour classer une équipe / 25 pour un rusher


def km(df: pd.DataFrame, cpt="cpt") -> KaplanMeierFitter:
    """KM : événement = pression (non censuré). Gère proprement les actions censurées."""
    return KaplanMeierFitter().fit(df[cpt], event_observed=~df["censored"] if cpt == "cpt" else df[cpt] < df["duration"])


def rmst(df: pd.DataFrame, horizon: float = HORIZON, cpt="cpt") -> float:
    """Temps moyen de poche propre sur [0, horizon] = aire sous la courbe KM (secondes)."""
    k = km(df, cpt)
    grid = np.linspace(0, horizon, 301)
    return float(np.trapezoid(k.survival_function_at_times(grid).to_numpy(), grid))


def clean_at(df: pd.DataFrame, t: float, cpt="cpt") -> float:
    """% de poches encore propres à t secondes (KM)."""
    return float(km(df, cpt).survival_function_at_times([t]).iloc[0])


def team_ranking(tab: pd.DataFrame, by: str, cpt="cpt", min_plays=MIN_PLAYS) -> pd.DataFrame:
    """RMST + % propre à 2.5 s par équipe ('possessionTeam' = OL, 'defensiveTeam' = pass rush)."""
    rows = []
    for team, g in tab.groupby(by):
        if len(g) >= min_plays:
            rows.append({"team": team, "n": len(g), "rmst": rmst(g, cpt=cpt),
                         "clean_2.5s": clean_at(g, 2.5, cpt), "sack_rate": (g.passResult == "S").mean()})
    out = pd.DataFrame(rows).sort_values("rmst", ascending=False).reset_index(drop=True)
    out["rank"] = out.index + 1
    return out


# ---------- CPT attendu (bonus) : Cox sur le contexte ----------
def _features(tab: pd.DataFrame) -> pd.DataFrame:
    f = pd.DataFrame(index=tab.index)
    f["n_rushers"] = tab.n_rushers.astype(float)
    f["play_action"] = tab.pff_playAction.fillna(0).astype(float)
    f["down"] = tab.down.astype(float)
    f["yards_to_go"] = tab.yardsToGo.clip(upper=20).astype(float)
    f["shotgun"] = (tab.offenseFormation == "SHOTGUN").astype(float)
    f["man"] = (tab.pff_passCoverageType == "Man").astype(float)
    f["defenders_in_box"] = tab.defendersInBox.fillna(tab.defendersInBox.median()).astype(float)
    return f


def expected_rmst(tab: pd.DataFrame, horizon: float = HORIZON, cpt="cpt") -> pd.Series:
    """RMST attendu par action selon le contexte (nb de rushers, PA, down, distance, formation, couverture)."""
    f = _features(tab)
    d = f.assign(T=tab[cpt].clip(lower=0.05), E=(~tab.censored).astype(int)) if cpt == "cpt" else \
        f.assign(T=tab[cpt].clip(lower=0.05), E=(tab[cpt] < tab.duration).astype(int))
    ok = d.notna().all(axis=1)
    cph = CoxPHFitter(penalizer=0.01).fit(d[ok], "T", "E")
    grid = np.linspace(0, horizon, 61)
    sf = cph.predict_survival_function(f[ok], times=grid)
    out = pd.Series(np.nan, index=tab.index)
    out[ok] = np.trapezoid(sf.to_numpy(), grid, axis=0)
    return out


def team_over_expected(tab: pd.DataFrame, by="possessionTeam", min_plays=MIN_PLAYS) -> pd.DataFrame:
    """RMST réel - attendu par équipe (la valeur ajoutée de la ligne, indépendante du schéma)."""
    t = tab.copy()
    t["exp_rmst"] = expected_rmst(t)
    rows = []
    for team, g in t.groupby(by):
        if len(g) >= min_plays:
            rows.append({"team": team, "n": len(g), "rmst": rmst(g), "expected": float(g.exp_rmst.mean())})
    o = pd.DataFrame(rows)
    o["over_expected"] = o.rmst - o.expected
    return o.sort_values("over_expected", ascending=False).reset_index(drop=True)


def rusher_ranking(duels: pd.DataFrame, min_rushes=150) -> pd.DataFrame:
    """Rushers : % de victoires (1er à entrer), CPT moyen quand 1er, nb de rushs, vitesse d'entrée."""
    g = duels.groupby(["rusherId", "rusher"])
    out = g.agg(rushes=("rusherId", "size"), wins=("won_first", "sum"),
                reach_rate=("entry_t", lambda s: s.notna().mean()),
                mean_entry_t=("entry_t", "mean"), entry_speed=("entry_speed", "mean")).reset_index()
    wins = duels[duels.won_first].groupby("rusherId")["cpt"].mean().rename("cpt_when_first")
    out = out.merge(wins, on="rusherId", how="left")
    out["win_rate"] = out.wins / out.rushes
    return out[out.rushes >= min_rushes].sort_values("reach_rate", ascending=False).reset_index(drop=True)


def blocker_ranking(duels: pd.DataFrame, min_duels=80) -> pd.DataFrame:
    """Bloqueurs : % de duels où le rusher assigné franchit le rayon (et à quelle vitesse en moyenne)."""
    d = duels.dropna(subset=["blockerId"])
    out = d.groupby(["blockerId", "blocker", "blocker_pos"]).agg(
        duels=("rusherId", "size"), beaten_rate=("entry_t", lambda s: s.notna().mean()),
        mean_entry_t=("entry_t", "mean"), team=("possessionTeam", lambda s: s.mode().iloc[0])).reset_index()
    return out[out.duels >= min_duels].sort_values("beaten_rate", ascending=False).reset_index(drop=True)
