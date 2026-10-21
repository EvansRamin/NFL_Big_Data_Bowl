# Méthodologie

## 1. Données et préparation

- **Source** : Big Data Bowl 2023, saison NFL 2021, semaines 1 à 8 (122 matchs, 8 532 passes).
- **Temps** : le tracking est échantillonné à 10 images/s. Le temps est calculé à partir de `frameId` (une frame = 0,1 s) et non de la colonne `time`.
- **Sens du jeu** : il est normalisé pour que l'attaque aille toujours vers la droite. Quand `playDirection == "left"`, on applique `x → 120 − x`, `y → 53,3 − y` et on ajoute 180° à `o` et `dir`.
- **Fenêtre d'analyse** : du snap (`ball_snap` ou `autoevent_ballsnap`) jusqu'au premier des événements suivants : lancer (`pass_forward`, `autoevent_passforward`), sack (`qb_sack`, `qb_strip_sack`), `pass_shovel` ou `run`. S'il n'y en a aucun, on va jusqu'à la dernière frame. Les actions sans snap sont écartées.
- **Rôles** : ils viennent de `pffScoutingData.pff_role`. Le QB est `"Pass"`, les rushers `"Pass Rush"`, les bloqueurs `"Pass Block"`.

## 2. Clean Pocket Time (CPT)

Pour chaque action et chaque frame, on calcule la distance euclidienne entre le QB et chaque rusher. Le calcul est entièrement vectorisé : c'est une jointure QB × rushers sur `(gameId, playId, frameId)`.

```
CPT = (première frame où un rusher est à < PRESSURE_RADIUS du QB − frame du snap) / 10
```

- `PRESSURE_RADIUS` vaut 2,0 yd par défaut. On le change dans `src/metrics.py`.
- Le rusher qui franchit le rayon en premier est enregistré (`first_rusher`), avec sa vitesse au moment où il entre (`first_entry_speed`).
- **Censure** : si aucun rusher n'entre dans le rayon avant la fin de l'action, CPT = durée observée et `censored = True`. On sait seulement que le QB a eu *au moins* ce temps-là. Jeter ces actions biaiserait fortement les résultats vers le bas, puisqu'elles représentent 68 % des cas.

## 3. Statistiques de survie

On traite le CPT comme une durée de survie : l'« événement » est la pression, et les actions censurées sont prises en compte.

- **Courbe de Kaplan-Meier** (`analysis.km`) : elle donne le pourcentage de poches encore propres à chaque instant. C'est ce que nous appelons l'« horloge de la poche ».
- **RMST** (*restricted mean survival time*, `analysis.rmst`) : c'est l'aire sous la courbe KM entre 0 et `HORIZON = 3 s`. Elle se lit comme « en moyenne, sur les 3 premières secondes, la poche reste propre X s ». C'est l'indicateur de classement principal parce qu'il intègre correctement la censure.
- **% propre à 2,5 s** (`analysis.clean_at`) : la valeur de la courbe KM à t = 2,5 s.

## 4. Classements

| Classement | Fonction | Règle |
|---|---|---|
| Lignes offensives | `team_ranking(tab, "possessionTeam")` | RMST décroissant, ≥ 60 actions |
| Pass rush par équipe | `team_ranking(tab, "defensiveTeam")` | RMST imposé à l'adversaire (le plus court = meilleur rush) |
| Rushers | `rusher_ranking(duels)` | % de rushs où le rusher atteint le rayon, ≥ 150 rushs |
| Bloqueurs | `blocker_ranking(duels)` | % de duels où le rusher assigné atteint le rayon, ≥ 80 duels |

Les **duels** relient chaque rusher au bloqueur qui lui était assigné grâce à `pff_nflIdBlockedPlayer`. Un rusher « gagne » une action s'il est le premier à entrer dans le rayon (`won_first`).

## 5. CPT attendu (modèle de Cox)

`analysis.expected_rmst` ajuste une régression de Cox à risques proportionnels (`lifelines.CoxPHFitter`, pénalisation 0,01). Ses variables de contexte sont :

- le nombre de rushers ;
- le play action ;
- le down ;
- la distance à franchir (plafonnée à 20 yd) ;
- la formation shotgun ;
- la couverture man ;
- le nombre de défenseurs dans la box (valeurs manquantes remplacées par la médiane).

On prédit la courbe de survie de chaque action, puis on l'intègre sur [0, 3 s] pour obtenir un RMST attendu. Par équipe, **réel − attendu** mesure ce que la ligne apporte une fois le schéma défensif et l'appel offensif pris en compte.

## 6. Validation

Le CPT doit se comporter comme un football coach s'y attendrait. Les contrôles sont dans `src/validate.py` et les tables dans `outputs/validation_*.csv`.

| Contrôle | Attendu | Observé |
|---|---|---|
| Par résultat | Sacks < incomplètes < complètes | RMST 2,63 s (sacks) contre 2,86 s (complètes) |
| Par nombre de rushers | Plus de rushers → poche plus courte | 87 % propres à 2,5 s avec 3-4 rushers, 70 % avec 6+ |
| Accord avec PFF (hit/hurry/sack) | Forte concordance | φ = 0,61 ; précision 81 % ; rappel 69 % |
| Couverture man / zone | Peu d'effet direct | Courbes quasi superposées |
| Play action | — | Pas d'effet sur le RMST, mais lancer plus tardif (3,3 s contre 2,7 s) |

**Robustesse au seuil** : le classement des lignes offensives est recalculé avec des rayons de 1,5, 2 et 3 yd (`outputs/robustesse_classement_OL.csv`). La corrélation de Spearman est de 0,73 entre 1,5 et 2 yd, mais seulement de 0,45 entre 2 et 3 yd.

## 7. Limites

1. **Taille d'échantillon** : ~250 actions par équipe. Les écarts entre équipes (≤ 0,26 s) sont des tendances, sans intervalle de confiance calculé.
2. **Seuil arbitraire** : le rayon de 2 yd est un choix, et les classements y sont moyennement sensibles (voir plus haut).
3. **Censure informative** : un QB qui lance vite « cache » les faiblesses de sa ligne. L'hypothèse de censure non informative de Kaplan-Meier n'est donc pas pleinement respectée. Au-delà de ~3 s, il reste peu d'actions à risque.
4. **Ce que la distance ne mesure pas** : la qualité technique du bloc, la lecture du QB, les pressions perçues sans proximité physique, et ce qui se passe après le lancer (le tracking s'arrête à la fin de l'action).
5. **Effets mélangés** : le play action allonge le temps avant le lancer sans allonger la poche propre. Le CPT seul ne peut pas séparer ces deux effets.
