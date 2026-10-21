# ⏱️ Pocket Clock — how much time does the QB really have?

We invented the **Clean Pocket Time (CPT)**: the number of seconds between the snap and the moment a pass rusher gets within 2 yards of the QB, computed directly from the tracking data of the 8,532 pass plays of the 2021 NFL season (weeks 1-8), with plays where nobody arrives treated as "censored" (Kaplan-Meier) rather than thrown away. Over 3 seconds, the Rams' pockets stay clean 2.95 s on average, the Vikings' 2.69 s; at 2.5 s, 87% of pockets hold against 4 rushers but only 70% against 6 or more. An offensive coach sees where their line breaks (most-beaten blockers), a defensive coach sees which rusher reaches the QB most often (Hendrickson: 24% of his rushes), a scout compares blockers, and a broadcaster shows the "pocket clock" on air.

![ranking](outputs/01_offensive_line_ranking.png)
![clock](outputs/04_pocket_clock_by_rushers.png)

## How to run
```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python run_all.py                    # full pipeline (~3 min the first time, then parquet cache); DEBUG=1 for 5 games
.venv/bin/streamlit run app.py                 # interactive dashboard (team, blockers, rushers, play replay)
.venv/bin/python -m src.export_html            # standalone HTML version: outputs/pocket_clock_dashboard.html
```
Notebook: `notebooks/analysis.ipynb` (Restart & Run All OK, venv kernel). Images/GIF in `outputs/`.

## Method
- Data: Big Data Bowl 2023 (**2021** season, weeks 1-8, 122 games). Tracking at 10 frames/s; time comes from `frameId`, not `time`. Play direction normalized (offense moves right).
- Window: from the snap (`ball_snap`/`autoevent_ballsnap`) to the throw, sack, or last frame. QB = `pff_role == "Pass"`, rushers = `"Pass Rush"`.
- **CPT** = (first frame with QB-rusher distance < `PRESSURE_RADIUS` − snap frame) / 10. If no rusher arrives: CPT = observed duration, `censored = True`.
- Team rankings: **RMST** (mean clean-pocket time over 3 s = area under the Kaplan-Meier curve), which handles censored plays.
- **Expected CPT**: Cox regression (rusher count, play action, down, distance, formation, coverage); "over expected" = the line's added value independent of scheme.
- Duels: `pff_nflIdBlockedPlayer` links each rusher to his assigned blocker (most-beaten blockers ranking, rusher entry speed).
- Validation: sacks = shortest pockets (RMST 2.63 s vs 2.86 s on completions); more rushers = shorter pocket; agreement with PFF pressures (hit/hurry/sack): φ = 0.61, 81% of our pressures are also PFF pressures and we capture 69% of theirs.

## Limitations (methodological honesty)
- Only 8 weeks: ~250 plays per team, so gaps between teams (≤ 0.26 s) should be read as trends, not truths.
- The 2 yd threshold is arbitrary and rankings are only moderately stable (Spearman correlation 0.73 between 1.5 and 2 yd, 0.45 between 2 and 3 yd).
- 68% of plays are censored (the QB throws before pressure arrives): censoring is informative (a quick QB "hides" his line), and curves are unreliable beyond ~3 s.
- Distance captures neither block quality, nor the QB's read, nor "mental" pressure; tracking stops at the throw.
- Play action shows no longer pocket in RMST, but lengthens time to throw (3.3 s vs 2.7 s): the two effects are mixed.
