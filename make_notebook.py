import nbformat as nbf
nb = nbf.v4.new_notebook(); C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s)); code = lambda s: C.append(nbf.v4.new_code_cell(s))
md("# ⏱️ Pocket Clock — combien de temps le QB a-t-il vraiment ?\nNFL **2021** sem. 1-8 (Big Data Bowl 2023). Métrique inventée : **Clean Pocket Time (CPT)** = secondes entre le snap et le 1er moment où un pass rusher passe à < 2 yd du QB. Si personne n'arrive avant le lancer/sack, l'action est *censurée* (gardée, traitée par Kaplan-Meier).")
code("import os, sys; os.chdir(os.path.dirname(os.path.abspath('')) if os.path.basename(os.getcwd())=='notebooks' else os.getcwd()); sys.path.insert(0, os.getcwd())\n"
     "import pandas as pd; from IPython.display import Image, display\n"
     "from src import load, metrics, analysis as A, validate, viz\n"
     "# DEBUG=1 dans l'environnement -> 5 matchs seulement")
md("## 1. Chargement (cache parquet) et CPT")
code("t = load.load_all(); load.summary(t)\ntab, duels, sk = metrics.build_table(t); metrics.summary(tab, sk)\ntab.head()")
md("## 2. Validation football\nLe CPT doit être plus court sur les sacks, avec plus de rushers, et concorder avec les pressions PFF.")
code("res = validate.run(tab)")
md("## 3. Visualisations")
code("viz.make_all(t, tab, duels)")
for n, cap in [("01_classement_lignes_offensives", "Lignes offensives"), ("02_classement_pass_rush_equipes", "Pass rush par équipe"),
               ("03_top_pass_rushers", "Meilleurs rushers"), ("04_horloge_poche_par_rushers", "Horloge de la poche"),
               ("06_cpt_au_dessus_attendu", "CPT au-dessus de l'attendu"), ("07_qb_horloge_interne", "QB : horloge interne")]:
    md(f"### {cap}"); code(f"display(Image('outputs/{n}.png'))")
md("### Le sack le plus rapide (GIF)"); code("display(Image('outputs/08_sack_le_plus_rapide.gif'))")
md("## 4. Robustesse du seuil (1.5 / 2 / 3 yd)")
code("rob = pd.read_csv('outputs/robustesse_classement_OL.csv', index_col=0); display(rob.corr(method='spearman').round(2)); rob")
md("## Limites\n8 semaines seulement (~250 actions/équipe), seuil de 2 yd arbitraire (classements modérément stables : ρ de Spearman ≈ 0,45-0,73 entre seuils), ~68 % des actions censurées (le QB lance avant la pression) → courbes peu fiables au-delà de ~3 s, et la distance ne capte ni les blocs ni la lecture du QB.")
nb.metadata["kernelspec"] = {"name": "pocketclock", "display_name": "pocketclock", "language": "python"}; nb.cells = C; nbf.write(nb, "notebooks/analysis.ipynb")
