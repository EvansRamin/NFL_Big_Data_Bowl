# Architecture du code

## Flux de données

```
data/*.csv ──► load.load_all() ──► dict t {games, plays, players, pffScoutingData, tracking}
                    │ (cache/tracking.parquet)
                    ▼
            metrics.build_table(t) ──► tab   (1 ligne / action)   → cache/cpt_table.parquet
                                   └─► duels (1 ligne / rusher·action) → cache/duels.parquet
                    │
        ┌───────────┼──────────────┬────────────────────┐
        ▼           ▼              ▼                    ▼
 validate.run   viz.make_all   app.py (Streamlit)   export_html.main
 outputs/       outputs/*.png   lit cache/            outputs/pocket_clock_dashboard.html
 validation_*   ranking_*.csv
```

`run_all.py` enchaîne `load` → `metrics` → `validate` → `viz`. Le dashboard et l'export HTML ne recalculent rien : ils lisent les parquet dans `cache/`.

## Modules

### `src/load.py` : chargement

| Élément | Description |
|---|---|
| `FPS = 10` | Nombre d'images par seconde du tracking |
| `DEBUG` | Activé par la variable d'environnement `DEBUG=1` : seuls les 5 premiers matchs sont chargés et le cache s'appelle `tracking_debug.parquet` |
| `SNAP_EVENTS`, `THROW_EVENTS`, `END_EVENTS` | Événements qui marquent le début et la fin de la fenêtre d'analyse |
| `load_tables()` | Charge games, plays, players et pffScoutingData |
| `normalize_direction(df)` | Fait aller l'attaque vers la droite |
| `load_tracking(force=False)` | Lit tous les matchs, ne garde que [snap, fin] et ajoute `snap_frame`, `end_frame` et `t` (secondes depuis le snap). Le résultat est mis en cache. `force=True` reconstruit le cache |
| `load_all(force=False)` | Renvoie le dict des tables plus `tracking` |

### `src/metrics.py` : calcul du CPT

| Élément | Description |
|---|---|
| `PRESSURE_RADIUS = 2.0` | Rayon de pression en yards |
| `ROBUSTNESS_RADII` | Rayons supplémentaires (1,5, 2, 3) calculés dans les colonnes `cpt_<r>` |
| `build_distances(t)` | Une ligne par (action, frame, rusher) avec la distance au QB |
| `rusher_entries(d, radius)` | Par (action, rusher) : instant (`entry_t`) et vitesse (`entry_speed`) de la 1re entrée dans le rayon |
| `play_cpt(d, radius)` | Par action : `cpt`, `censored`, `duration`, premier rusher |
| `build_table(t, radius)` | Renvoie `(tab, duels, skipped)`. Ajoute le contexte de jeu, le nombre de rushers et de bloqueurs, le flag de pression PFF, les noms du QB et du rusher, et le bloqueur du premier rusher |

### `src/analysis.py` : statistiques

| Élément | Description |
|---|---|
| `HORIZON = 3.0` | Horizon du RMST, en secondes |
| `MIN_PLAYS = 60` | Nombre minimal d'actions pour classer une équipe |
| `km(df, cpt="cpt")` | Ajuste un Kaplan-Meier. Avec une colonne `cpt_<r>`, l'événement est `cpt < duration` |
| `rmst(df, horizon)` | Aire sous la courbe KM |
| `clean_at(df, t)` | Survie KM à l'instant t |
| `team_ranking(tab, by)` | Classement par équipe (`by` vaut `possessionTeam` ou `defensiveTeam`) |
| `expected_rmst(tab)` | RMST attendu par action, avec le modèle de Cox |
| `team_over_expected(tab)` | RMST réel moins attendu, par équipe |
| `rusher_ranking(duels, min_rushes=150)` | Classement des rushers |
| `blocker_ranking(duels, min_duels=80)` | Classement des bloqueurs |

### `src/validate.py` : validation

`run(tab)` compare le RMST et le % propre à 2,5 s selon le résultat, le nombre de rushers, le play action et la couverture. Il calcule aussi l'accord avec PFF et le taux de complétion par tranche de CPT. Tout est affiché et écrit dans `outputs/validation_*.csv`.

### `src/viz.py` : figures statiques

`make_all(t, tab, duels)` produit les PNG `01` à `07`, le GIF `08` et les CSV de classement. `animate()` dessine le terrain, les joueurs et le cercle de 2 yd autour du QB, qui devient rouge quand la poche est rompue.

### `src/replay.py` : rejeu interactif

`play_figure(trk, pff, gameId, playId)` renvoie une figure Plotly animée, avec un curseur temporel et un bouton de lecture. Elle est utilisée par `app.py` et `export_html.py`.

### `app.py` : dashboard Streamlit

La barre latérale propose deux profils, coach offensif ou défensif, et le choix de l'équipe. La page affiche :
- des indicateurs : RMST, % propre à 2,5 s et nombre d'actions, avec l'écart à la moyenne NFL ;
- l'horloge de la poche de l'équipe comparée à la NFL ;
- les bloqueurs les plus battus ou les meilleurs rushers, selon le profil ;
- le rejeu des 40 actions où la poche a craqué le plus vite.

## Modifier les paramètres

| Pour… | Modifier |
|---|---|
| Changer le rayon de pression | `metrics.PRESSURE_RADIUS`, puis relancer `run_all.py` (le cache du tracking reste valide) |
| Changer l'horizon du RMST | `analysis.HORIZON` |
| Changer les seuils de classement | `analysis.MIN_PLAYS` et les arguments `min_rushes` / `min_duels` |
| Reconstruire le cache du tracking | Supprimer `cache/tracking.parquet` ou appeler `load_all(force=True)` |
| Tester rapidement | `DEBUG=1` |
