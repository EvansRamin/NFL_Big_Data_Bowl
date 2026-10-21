# Code architecture

## Data flow

```
data/*.csv ──► load.load_all() ──► dict t {games, plays, players, pffScoutingData, tracking}
                    │ (cache/tracking.parquet)
                    ▼
            metrics.build_table(t) ──► tab   (1 row / play)          → cache/cpt_table.parquet
                                   └─► duels (1 row / rusher·play)   → cache/duels.parquet
                    │
        ┌───────────┼──────────────┬────────────────────┐
        ▼           ▼              ▼                    ▼
 validate.run   viz.make_all   app.py (Streamlit)   export_html.main
 outputs/       outputs/*.png   reads cache/          outputs/pocket_clock_dashboard.html
 validation_*   ranking_*.csv
```

`run_all.py` chains `load` → `metrics` → `validate` → `viz`. The dashboard and the HTML export recompute nothing: they read the parquet files in `cache/`.

## Modules

### `src/load.py`: loading

| Item | Description |
|---|---|
| `FPS = 10` | Tracking frames per second |
| `DEBUG` | Enabled with the `DEBUG=1` environment variable: only the first 5 games are loaded and the cache is named `tracking_debug.parquet` |
| `SNAP_EVENTS`, `THROW_EVENTS`, `END_EVENTS` | Events that mark the start and end of the analysis window |
| `load_tables()` | Loads games, plays, players and pffScoutingData |
| `normalize_direction(df)` | Makes the offense move to the right |
| `load_tracking(force=False)` | Reads every game, keeps only [snap, end] and adds `snap_frame`, `end_frame` and `t` (seconds since the snap). The result is cached. `force=True` rebuilds the cache |
| `load_all(force=False)` | Returns the dict of tables plus `tracking` |

### `src/metrics.py`: CPT computation

| Item | Description |
|---|---|
| `PRESSURE_RADIUS = 2.0` | Pressure radius in yards |
| `ROBUSTNESS_RADII` | Extra radii (1.5, 2, 3) computed into the `cpt_<r>` columns |
| `build_distances(t)` | One row per (play, frame, rusher) with the distance to the QB |
| `rusher_entries(d, radius)` | Per (play, rusher): time (`entry_t`) and speed (`entry_speed`) of the first entry into the radius |
| `play_cpt(d, radius)` | Per play: `cpt`, `censored`, `duration`, first rusher |
| `build_table(t, radius)` | Returns `(tab, duels, skipped)`. Adds game context, rusher and blocker counts, the PFF pressure flag, QB and rusher names, and the first rusher's blocker |

### `src/analysis.py`: statistics

| Item | Description |
|---|---|
| `HORIZON = 3.0` | RMST horizon, in seconds |
| `MIN_PLAYS = 60` | Minimum number of plays to rank a team |
| `km(df, cpt="cpt")` | Fits a Kaplan-Meier. With a `cpt_<r>` column, the event is `cpt < duration` |
| `rmst(df, horizon)` | Area under the KM curve |
| `clean_at(df, t)` | KM survival at time t |
| `team_ranking(tab, by)` | Team ranking (`by` is `possessionTeam` or `defensiveTeam`) |
| `expected_rmst(tab)` | Expected RMST per play, from the Cox model |
| `team_over_expected(tab)` | Actual minus expected RMST, per team |
| `rusher_ranking(duels, min_rushes=150)` | Rusher ranking |
| `blocker_ranking(duels, min_duels=80)` | Blocker ranking |

### `src/validate.py`: validation

`run(tab)` compares RMST and % clean at 2.5 s by result, number of rushers, play action and coverage. It also computes agreement with PFF and the completion rate per CPT bucket. Everything is printed and written to `outputs/validation_*.csv`.

### `src/viz.py`: static figures

`make_all(t, tab, duels)` produces PNGs `01` to `07`, GIF `08` and the ranking CSVs. `animate()` draws the field, the players and the 2 yd circle around the QB, which turns red when the pocket breaks.

### `src/replay.py`: interactive replay

`play_figure(trk, pff, gameId, playId)` returns an animated Plotly figure with a time slider and a play button. It is used by `app.py` and `export_html.py`.

### `src/theme.py`: visual identity

Design tokens (dark surfaces, a single amber accent, Archivo for headings and Inter for body text) taken from the mockup in `design/`. It also provides HTML helpers (`page_header`, `kpi`, `card_title`, `brand`) shared by the Streamlit app and the HTML export. Fonts are served from `static/fonts` through Streamlit's static file serving.

### `app.py`: Streamlit dashboard

The sidebar offers two points of view (offensive or defensive coach), a team picker and an optional comparison team. The page shows:
- KPIs: RMST, % clean at 2.5 s, league rank and number of plays, each compared with the NFL average;
- tabs: **Pocket clock** (team curve vs NFL), **League** (rankings), **Players** (most-beaten blockers or best rushers depending on the point of view), **Replay** (the 40 plays where the pocket broke fastest) and **Method**.

## Changing parameters

| To… | Change |
|---|---|
| Change the pressure radius | `metrics.PRESSURE_RADIUS`, then rerun `run_all.py` (the tracking cache stays valid) |
| Change the RMST horizon | `analysis.HORIZON` |
| Change ranking thresholds | `analysis.MIN_PLAYS` and the `min_rushes` / `min_duels` arguments |
| Rebuild the tracking cache | Delete `cache/tracking.parquet` or call `load_all(force=True)` |
| Test quickly | `DEBUG=1` |
