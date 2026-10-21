"""Étape 3 : le CPT est-il cohérent football ? Imprime + sauvegarde des tables dans outputs/."""
import numpy as np
import pandas as pd

from .analysis import clean_at, rmst
from .load import ROOT

OUT = ROOT / "outputs"


def blitz_bucket(n):
    return "3-4 rushers" if n <= 4 else ("5 rushers" if n == 5 else "6+ rushers")


def compare(tab: pd.DataFrame, col: str) -> pd.DataFrame:
    rows = []
    for k, g in tab.groupby(col):
        rows.append({col: k, "n": len(g), "RMST_3s": rmst(g), "propre_2.5s": clean_at(g, 2.5),
                     "censuré": g.censored.mean(), "t_med_lancer": g.duration.median()})
    return pd.DataFrame(rows)


def pff_agreement(tab: pd.DataFrame) -> dict:
    """CPT vs pressions PFF. 'pff_pressure' = hit/hurry/sack. Notre pression = non censuré."""
    ours = ~tab.censored
    pff = tab.pff_pressure.fillna(False).astype(bool)
    return {"P(CPT<fin | PFF pression)": ours[pff].mean(), "P(CPT<fin | pas de PFF)": ours[~pff].mean(),
            "precision (PFF | nous)": pff[ours].mean(), "rappel (nous | PFF)": ours[pff].mean(),
            "corrélation φ": np.corrcoef(ours, pff)[0, 1]}


def result_by_cpt(tab: pd.DataFrame) -> pd.DataFrame:
    """Complétion + yards par passe selon tranches de 0,5 s (actions non censurées + censurées sur leur durée)."""
    t = tab[tab.passResult.isin(["C", "I", "IN"])].copy()
    t["tranche"] = pd.cut(t.cpt, [0, 1.5, 2.0, 2.5, 3.0, 3.5, 10], right=False)
    return t.groupby("tranche", observed=True).agg(n=("cpt", "size"), completion=("passResult", lambda s: (s == "C").mean()),
                                                    yds_par_passe=("playResult", "mean")).reset_index()


def run(tab: pd.DataFrame) -> dict:
    OUT.mkdir(exist_ok=True)
    tab = tab.assign(blitz=tab.n_rushers.map(blitz_bucket), resultat=tab.passResult)
    res = {"par_resultat": compare(tab, "resultat"), "par_blitz": compare(tab, "blitz"),
           "par_play_action": compare(tab, "pff_playAction"), "par_couverture": compare(tab, "pff_passCoverageType"),
           "pff": pd.Series(pff_agreement(tab)), "resultat_vs_cpt": result_by_cpt(tab)}
    for k, v in res.items():
        print(f"\n== {k} ==\n{v.round(3).to_string()}")
        v.to_csv(OUT / f"validation_{k}.csv")
    return res
