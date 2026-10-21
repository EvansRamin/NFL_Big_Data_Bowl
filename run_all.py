"""Pipeline complet : chargement -> CPT -> validation -> figures.   python run_all.py   (DEBUG=1 pour tester)"""
import pandas as pd
from src import load, metrics, validate, viz

if __name__ == "__main__":
    t = load.load_all(); load.summary(t)
    tab, duels, sk = metrics.build_table(t); metrics.summary(tab, sk)
    tab.to_parquet(load.CACHE_DIR / "cpt_table.parquet"); duels.to_parquet(load.CACHE_DIR / "duels.parquet")
    validate.run(tab)
    viz.make_all(t, tab, duels)
