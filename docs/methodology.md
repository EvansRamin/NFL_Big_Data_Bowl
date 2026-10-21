# Methodology

## 1. Data and preparation

- **Source**: Big Data Bowl 2023, 2021 NFL season, weeks 1 to 8 (122 games, 8,532 dropbacks).
- **Time**: tracking is sampled at 10 frames/s. Time is computed from `frameId` (one frame = 0.1 s), not from the `time` column.
- **Play direction**: normalized so the offense always moves to the right. When `playDirection == "left"`, we apply `x → 120 − x`, `y → 53.3 − y` and add 180° to `o` and `dir`.
- **Analysis window**: from the snap (`ball_snap` or `autoevent_ballsnap`) to the first of: a throw (`pass_forward`, `autoevent_passforward`), a sack (`qb_sack`, `qb_strip_sack`), `pass_shovel` or `run`. If none of these occurs, the window runs to the last frame. Plays without a snap are dropped.
- **Roles**: taken from `pffScoutingData.pff_role`. The QB is `"Pass"`, rushers are `"Pass Rush"`, blockers are `"Pass Block"`.

## 2. Clean Pocket Time (CPT)

For every play and frame, we compute the Euclidean distance between the QB and each rusher. The computation is fully vectorized: a QB × rushers join on `(gameId, playId, frameId)`.

```
CPT = (first frame where a rusher is within PRESSURE_RADIUS of the QB − snap frame) / 10
```

- `PRESSURE_RADIUS` defaults to 2.0 yd. It is set in `src/metrics.py`.
- The first rusher to cross the radius is recorded (`first_rusher`), along with his speed when he enters it (`first_entry_speed`).
- **Censoring**: if no rusher enters the radius before the play ends, CPT = observed duration and `censored = True`. All we know is that the QB had *at least* that much time. Dropping these plays would heavily bias the results downward, since they make up 68% of all plays.

## 3. Survival statistics

CPT is treated as a survival time: the "event" is pressure, and censored plays are accounted for.

- **Kaplan-Meier curve** (`analysis.km`): the share of pockets still clean at each instant. This is what we call the "pocket clock".
- **RMST** (*restricted mean survival time*, `analysis.rmst`): the area under the KM curve between 0 and `HORIZON = 3 s`. It reads as "on average, over the first 3 seconds, the pocket stays clean for X s". It is the main ranking metric because it handles censoring correctly.
- **% clean at 2.5 s** (`analysis.clean_at`): the KM curve's value at t = 2.5 s.

## 4. Rankings

| Ranking | Function | Rule |
|---|---|---|
| Offensive lines | `team_ranking(tab, "possessionTeam")` | RMST descending, ≥ 60 plays |
| Team pass rush | `team_ranking(tab, "defensiveTeam")` | RMST allowed to the opponent (shortest = best rush) |
| Rushers | `rusher_ranking(duels)` | % of rushes where the rusher reaches the radius, ≥ 150 rushes |
| Blockers | `blocker_ranking(duels)` | % of duels where the assigned rusher reaches the radius, ≥ 80 duels |

**Duels** link each rusher to the blocker assigned to him, using `pff_nflIdBlockedPlayer`. A rusher "wins" a play if he is the first to enter the radius (`won_first`).

## 5. Expected CPT (Cox model)

`analysis.expected_rmst` fits a Cox proportional hazards regression (`lifelines.CoxPHFitter`, penalizer 0.01). Its context variables are:

- number of rushers;
- play action;
- down;
- yards to go (capped at 20);
- shotgun formation;
- man coverage;
- defenders in the box (missing values filled with the median).

We predict each play's survival curve and integrate it over [0, 3 s] to get an expected RMST. Per team, **actual − expected** measures what the line contributes once the defensive scheme and the offensive call are accounted for.

## 6. Validation

CPT should behave the way a football coach would expect. The checks are in `src/validate.py` and the tables in `outputs/validation_*.csv`.

| Check | Expected | Observed |
|---|---|---|
| By result | Sacks < incompletions < completions | RMST 2.63 s (sacks) vs 2.86 s (completions) |
| By number of rushers | More rushers → shorter pocket | 87% clean at 2.5 s with 3-4 rushers, 70% with 6+ |
| Agreement with PFF (hit/hurry/sack) | Strong agreement | φ = 0.61; precision 81%; recall 69% |
| Man vs zone coverage | Little direct effect | Curves nearly overlap |
| Play action | — | No effect on RMST, but later throws (3.3 s vs 2.7 s) |

**Threshold robustness**: the offensive line ranking is recomputed with 1.5, 2 and 3 yd radii (`outputs/robustness_ol_ranking.csv`). Spearman correlation is 0.73 between 1.5 and 2 yd, but only 0.45 between 2 and 3 yd.

## 7. Limitations

1. **Sample size**: about 250 plays per team. Gaps between teams (≤ 0.26 s) are trends; no confidence intervals are computed.
2. **Arbitrary threshold**: the 2 yd radius is a choice, and rankings are moderately sensitive to it (see above).
3. **Informative censoring**: a QB who throws quickly "hides" his line's weaknesses, so the Kaplan-Meier assumption of non-informative censoring does not fully hold. Beyond ~3 s, few plays remain at risk.
4. **What distance does not measure**: technical block quality, the QB's read, pressure felt without physical proximity, and anything after the throw (tracking stops at the end of the window).
5. **Mixed effects**: play action delays the throw without lengthening the clean pocket. CPT alone cannot separate these two effects.
