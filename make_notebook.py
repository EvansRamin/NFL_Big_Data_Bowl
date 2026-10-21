import nbformat as nbf
nb = nbf.v4.new_notebook(); C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s)); code = lambda s: C.append(nbf.v4.new_code_cell(s))
md("# ⏱️ Pocket Clock — how much time does the QB really have?\nNFL **2021** weeks 1-8 (Big Data Bowl 2023). Invented metric: **Clean Pocket Time (CPT)** = seconds between the snap and the first moment a pass rusher gets within 2 yd of the QB. If nobody arrives before the throw/sack, the play is *censored* (kept, handled with Kaplan-Meier).")
code("import os, sys; os.chdir(os.path.dirname(os.path.abspath('')) if os.path.basename(os.getcwd())=='notebooks' else os.getcwd()); sys.path.insert(0, os.getcwd())\n"
     "import pandas as pd; from IPython.display import Image, display\n"
     "from src import load, metrics, analysis as A, validate, viz\n"
     "# DEBUG=1 in the environment -> 5 games only")
md("## 1. Loading (parquet cache) and CPT")
code("t = load.load_all(); load.summary(t)\ntab, duels, sk = metrics.build_table(t); metrics.summary(tab, sk)\ntab.head()")
md("## 2. Football validation\nThe CPT should be shorter on sacks, with more rushers, and agree with PFF pressures.")
code("res = validate.run(tab)")
md("## 3. Visualizations")
code("viz.make_all(t, tab, duels)")
for n, cap in [("01_offensive_line_ranking", "Offensive lines"), ("02_pass_rush_team_ranking", "Pass rush by team"),
               ("03_top_pass_rushers", "Best rushers"), ("04_pocket_clock_by_rushers", "Pocket clock"),
               ("06_cpt_over_expected", "CPT over expected"), ("07_qb_internal_clock", "QB: internal clock")]:
    md(f"### {cap}"); code(f"display(Image('outputs/{n}.png'))")
md("### The fastest sack (GIF)"); code("display(Image('outputs/08_fastest_sack.gif'))")
md("## 4. Threshold robustness (1.5 / 2 / 3 yd)")
code("rob = pd.read_csv('outputs/robustness_ol_ranking.csv', index_col=0); display(rob.corr(method='spearman').round(2)); rob")
md("## Limitations\nOnly 8 weeks (~250 plays/team), arbitrary 2 yd threshold (moderately stable rankings: Spearman ρ ≈ 0.45-0.73 across thresholds), ~68% of plays censored (the QB throws before pressure) → curves unreliable beyond ~3 s, and distance captures neither blocking quality nor the QB's reads.")
nb.metadata["kernelspec"] = {"name": "pocketclock", "display_name": "pocketclock", "language": "python"}; nb.cells = C; nbf.write(nb, "notebooks/analysis.ipynb")
