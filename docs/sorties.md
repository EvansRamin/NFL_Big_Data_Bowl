# Référence des sorties

Tous ces fichiers sont générés par `python run_all.py`, sauf le dashboard HTML qui vient de `python -m src.export_html`.

## Figures (`outputs/`)

| Fichier | Contenu |
|---|---|
| `01_classement_lignes_offensives.png` | Écart de RMST de chaque ligne offensive par rapport à la moyenne NFL |
| `02_classement_pass_rush_equipes.png` | RMST imposé par chaque défense (plus court = meilleur rush) |
| `03_top_pass_rushers.png` | Top 15 des rushers selon leur taux d'arrivée à < 2 yd du QB |
| `04_horloge_poche_par_rushers.png` | Courbes de Kaplan-Meier pour 4 rushers ou moins, 5, et 6 ou plus |
| `05_horloge_poche_man_vs_zone.png` | Courbes de Kaplan-Meier en couverture man et en zone |
| `06_cpt_au_dessus_attendu.png` | RMST réel − attendu par ligne offensive (modèle de Cox) |
| `07_qb_horloge_interne.png` | Pour chaque QB (≥ 80 actions) : temps médian avant le lancer et RMST |
| `08_sack_le_plus_rapide.gif` | Animation du sack le plus rapide (CPT ≥ 0,5 s) |
| `pocket_clock_dashboard.html` | Dashboard autonome : classement interactif, horloge par équipe et rejeu des 3 sacks les plus rapides |

## Classements (`outputs/ranking_*.csv`, `qb_clock.csv`)

**`ranking_offensive_lines.csv`** et **`ranking_pass_rush_teams.csv`**

| Colonne | Description |
|---|---|
| `team` | Équipe |
| `n` | Nombre d'actions |
| `rmst` | Temps moyen de poche propre sur 3 s (s) |
| `clean_2.5s` | Part des poches encore propres à 2,5 s (KM) |
| `sack_rate` | Part des actions terminées par un sack |
| `rank` | Rang (1 = RMST le plus long) |

**`ranking_over_expected.csv`** : colonnes `team`, `n`, `rmst`, `expected` (RMST moyen prédit par le modèle de Cox) et `over_expected` (= `rmst − expected`).

**`ranking_rushers.csv`**

| Colonne | Description |
|---|---|
| `rusher`, `rusherId` | Joueur |
| `rushes` | Nombre de rushs |
| `wins` / `win_rate` | Nombre et part des actions où il est le premier à entrer dans le rayon |
| `reach_rate` | Part des rushs où il entre dans le rayon (critère de tri) |
| `mean_entry_t` | Temps moyen d'entrée (s), quand il entre |
| `entry_speed` | Vitesse moyenne au moment de l'entrée (yd/s) |
| `cpt_when_first` | CPT moyen des actions où il est arrivé le premier |

**`ranking_blockers.csv`** : colonnes `blocker`, `blocker_pos` (poste d'alignement), `team`, `duels`, `beaten_rate` (part des duels où le rusher assigné entre dans le rayon) et `mean_entry_t`.

**`qb_clock.csv`** : colonnes `qb`, `n`, `throw_t` (temps médian avant le lancer ou le sack), `rmst` et `pressured` (part des actions non censurées).

**`robustesse_classement_OL.csv`** : rang de chaque ligne offensive avec un rayon de 1,5, 2 et 3 yd.

## Validation (`outputs/validation_*.csv`)

| Fichier | Regroupement |
|---|---|
| `validation_par_resultat.csv` | `passResult` (C = complète, I = incomplète, IN = interception, S = sack, R = course du QB) |
| `validation_par_blitz.csv` | 3-4, 5 ou 6+ rushers |
| `validation_par_play_action.csv` | Play action (0 ou 1) |
| `validation_par_couverture.csv` | Man, zone ou autre |

Ces quatre fichiers ont les colonnes `n`, `RMST_3s`, `propre_2.5s`, `censuré` (part censurée) et `t_med_lancer` (durée médiane de l'action).

- **`validation_pff.csv`** : accord avec les pressions PFF. Il contient les probabilités conditionnelles, la précision, le rappel et la corrélation φ.
- **`validation_resultat_vs_cpt.csv`** : taux de complétion et yards par passe pour chaque tranche de CPT de 0,5 s.

## Cache (`cache/`)

| Fichier | Contenu |
|---|---|
| `tracking.parquet` | Tracking normalisé restreint à [snap, fin], avec `snap_frame`, `end_frame` et `t` |
| `tracking_debug.parquet` | Même chose en mode `DEBUG=1` (5 matchs) |
| `cpt_table.parquet` | Table `tab` : une ligne par action |
| `duels.parquet` | Table `duels` : une ligne par (action, rusher) |

### Colonnes principales de `cpt_table.parquet`

| Colonne | Description |
|---|---|
| `gameId`, `playId` | Clé de l'action |
| `cpt` | Clean Pocket Time (s) |
| `censored` | `True` si aucun rusher n'est entré dans le rayon |
| `duration` | Durée de la fenêtre snap → fin (s) |
| `cpt_1.5`, `cpt_2.0`, `cpt_3.0` | CPT avec d'autres rayons |
| `first_rusher`, `first_rusherId`, `first_entry_speed` | Premier rusher à entrer dans le rayon |
| `first_blocker`, `first_blockerId`, `first_blocker_pos` | Bloqueur assigné à ce rusher |
| `qb`, `qbId` | Quarterback |
| `n_rushers`, `n_blockers` | Nombre de rushers et de bloqueurs (PFF) |
| `pff_pressure` | Au moins un hit, hurry ou sack PFF |
| `possessionTeam`, `defensiveTeam`, `down`, `yardsToGo`, `passResult`, `playResult`, `offenseFormation`, `pff_passCoverage`, `pff_passCoverageType`, `pff_playAction`, `dropBackType`, `defendersInBox`, `quarter` | Contexte de l'action, repris de `plays.csv` |

### Colonnes de `duels.parquet`

Les colonnes sont `rusherId`/`rusher`, `blockerId`/`blocker`/`blocker_pos`, `entry_t` et `entry_speed` (NaN si le rusher n'entre jamais dans le rayon). On y trouve aussi `won_first`, les flags PFF du bloqueur (`pff_beatenByDefender`, `pff_hurryAllowed`, `pff_sackAllowed`, `pff_hitAllowed`) et le contexte de l'action (`possessionTeam`, `defensiveTeam`, `cpt`, `censored`, `n_rushers`).
