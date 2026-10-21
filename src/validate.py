"""Step 3: does the CPT make football sense? Prints + saves tables to outputs/."""
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
        rows.append({col: k, "n": len(g), "RMST_3s": rmst(g), "clean_2.5s": clean_at(g, 2.5),
                     "censored": g.censored.mean(), "median_throw_t": g.duration.median()})
    return pd.DataFrame(rows)


def pff_agreement(tab: pd.DataFrame) -> dict:
    """CPT vs PFF pressures. 'pff_pressure' = hit/hurry/sack. Our pressure = uncensored."""
    ours = ~tab.censored
    pff = tab.pff_pressure.fillna(False).astype(bool)
    return {"P(CPT<end | PFF pressure)": ours[pff].mean(), "P(CPT<end | no PFF pressure)": ours[~pff].mean(),
            "precision (PFF | ours)": pff[ours].mean(), "recall (ours | PFF)": ours[pff].mean(),
            "phi correlation": np.corrcoef(ours, pff)[0, 1]}


def result_by_cpt(tab: pd.DataFrame) -> pd.DataFrame:
    """Completion + yards per pass by 0.5 s CPT bucket (uncensored plays + censored ones at their duration)."""
    t = tab[tab.passResult.isin(["C", "I", "IN"])].copy()
    t["bucket"] = pd.cut(t.cpt, [0, 1.5, 2.0, 2.5, 3.0, 3.5, 10], right=False)
    return t.groupby("bucket", observed=True).agg(n=("cpt", "size"), completion=("passResult", lambda s: (s == "C").mean()),
                                                    yards_per_pass=("playResult", "mean")).reset_index()


def run(tab: pd.DataFrame) -> dict:
    OUT.mkdir(exist_ok=True)
    tab = tab.assign(blitz=tab.n_rushers.map(blitz_bucket), result=tab.passResult)
    res = {"by_result": compare(tab, "result"), "by_blitz": compare(tab, "blitz"),
           "by_play_action": compare(tab, "pff_playAction"), "by_coverage": compare(tab, "pff_passCoverageType"),
           "pff": pd.Series(pff_agreement(tab)), "result_vs_cpt": result_by_cpt(tab)}
    for k, v in res.items():
        print(f"\n== {k} ==\n{v.round(3).to_string()}")
        v.to_csv(OUT / f"validation_{k}.csv")
    return res
