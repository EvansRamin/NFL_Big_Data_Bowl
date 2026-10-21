"""Clean Pocket Time (CPT): seconds between the snap and the first moment a rusher comes within PRESSURE_RADIUS of the QB.

If no rusher arrives before the end of the play (throw/sack), the play is CENSORED:
cpt = observed duration, censored = True (the QB had at least that much time).
"""
import numpy as np
import pandas as pd

from .load import FPS, load_all

PRESSURE_RADIUS = 2.0                 # yards, configurable
ROBUSTNESS_RADII = (1.5, 2.0, 3.0)
KEYS = ["gameId", "playId"]


def build_distances(t: dict) -> pd.DataFrame:
    """One row per (play, frame, rusher): distance to the QB, rusher speed, t since the snap.

    Vectorized: QB x rushers join on (gameId, playId, frameId), no loop.
    """
    trk = t["tracking"]
    roles = t["pffScoutingData"][KEYS + ["nflId", "pff_role"]]
    m = trk.merge(roles, on=KEYS + ["nflId"], how="inner")
    qb = (m[m.pff_role == "Pass"].drop_duplicates(KEYS + ["frameId"])  # 1 QB per play
          [KEYS + ["frameId", "nflId", "x", "y"]]
          .rename(columns={"nflId": "qbId", "x": "qx", "y": "qy"}))
    rs = (m[m.pff_role == "Pass Rush"][KEYS + ["frameId", "nflId", "x", "y", "s", "t", "snap_frame", "end_frame"]]
          .rename(columns={"nflId": "rusherId"}))
    d = rs.merge(qb, on=KEYS + ["frameId"], how="inner")
    d["dist"] = np.hypot(d.x - d.qx, d.y - d.qy).astype("float32")
    return d


def rusher_entries(d: pd.DataFrame, radius: float) -> pd.DataFrame:
    """Per (play, rusher): first frame under `radius` -> entry_t, entry_speed (NaN if never)."""
    inside = d[d.dist < radius].sort_values("frameId")
    first = inside.groupby(KEYS + ["rusherId"], as_index=False).first()
    first = first[KEYS + ["rusherId", "t", "s"]].rename(columns={"t": "entry_t", "s": "entry_speed"})
    allr = d[KEYS + ["rusherId"]].drop_duplicates()
    return allr.merge(first, on=KEYS + ["rusherId"], how="left")


def play_cpt(d: pd.DataFrame, radius: float) -> pd.DataFrame:
    """CPT per play for a given radius (+ first rusher, his entry speed)."""
    ent = rusher_entries(d, radius)
    win = (ent.dropna(subset=["entry_t"]).sort_values("entry_t")
           .groupby(KEYS, as_index=False).first()
           .rename(columns={"rusherId": "first_rusherId", "entry_t": "cpt", "entry_speed": "first_entry_speed"}))
    dur = (d.groupby(KEYS)[["t", "end_frame", "snap_frame"]]
           .agg(t=("t", "max"), end_frame=("end_frame", "first"), snap_frame=("snap_frame", "first")))
    dur["duration"] = (dur.end_frame - dur.snap_frame) / FPS
    out = dur[["duration"]].reset_index().merge(win, on=KEYS, how="left")
    out["censored"] = out["cpt"].isna()
    out["cpt"] = out["cpt"].fillna(out["duration"])
    return out


def build_table(t: dict, radius: float = PRESSURE_RADIUS):
    """Final per-play table + duels table (rusher <-> assigned blocker).

    Returns (plays_table, duels_table, skipped_dict).
    """
    d = build_distances(t)
    base = play_cpt(d, radius)
    for r in ROBUSTNESS_RADII:                       # robustness columns
        base[f"cpt_{r}"] = play_cpt(d, r)["cpt"].to_numpy()
    plays, pff, pl = t["plays"], t["pffScoutingData"], t["players"]
    n_rush = (pff[pff.pff_role == "Pass Rush"].groupby(KEYS).size().rename("n_rushers").reset_index())
    n_block = (pff[pff.pff_role == "Pass Block"].groupby(KEYS).size().rename("n_blockers").reset_index())
    qbid = pff[pff.pff_role == "Pass"].drop_duplicates(KEYS)[KEYS + ["nflId"]].rename(columns={"nflId": "qbId"})
    pcols = ["gameId", "playId", "possessionTeam", "defensiveTeam", "down", "yardsToGo", "passResult",
             "playResult", "offenseFormation", "pff_passCoverage", "pff_passCoverageType",
             "pff_playAction", "dropBackType", "defendersInBox", "quarter"]
    tab = (base.merge(plays[pcols], on=KEYS, how="left").merge(n_rush, on=KEYS, how="left")
           .merge(n_block, on=KEYS, how="left").merge(qbid, on=KEYS, how="left"))
    # PFF pressure at the play level
    flags = (pff.groupby(KEYS)[["pff_hit", "pff_hurry", "pff_sack"]].sum(min_count=1).fillna(0))
    flags["pff_pressure"] = (flags.sum(axis=1) > 0)
    tab = tab.merge(flags[["pff_pressure"]].reset_index(), on=KEYS, how="left")
    tab = tab.merge(pl[["nflId", "displayName"]].rename(columns={"nflId": "first_rusherId", "displayName": "first_rusher"}),
                    on="first_rusherId", how="left")
    tab = tab.merge(pl[["nflId", "displayName"]].rename(columns={"nflId": "qbId", "displayName": "qb"}),
                    on="qbId", how="left")
    # --- duels: for each rusher, who was blocking him? (pff_nflIdBlockedPlayer)
    ent = rusher_entries(d, radius)
    blk = pff[(pff.pff_role == "Pass Block") & pff.pff_nflIdBlockedPlayer.notna()][
        KEYS + ["nflId", "pff_nflIdBlockedPlayer", "pff_positionLinedUp", "pff_beatenByDefender",
                "pff_hurryAllowed", "pff_sackAllowed", "pff_hitAllowed"]]
    blk = blk.rename(columns={"nflId": "blockerId", "pff_nflIdBlockedPlayer": "rusherId",
                              "pff_positionLinedUp": "blocker_pos"})
    blk["rusherId"] = blk["rusherId"].astype("int64")
    duels = ent.merge(blk, on=KEYS + ["rusherId"], how="left")
    duels = duels.merge(tab[KEYS + ["possessionTeam", "defensiveTeam", "cpt", "censored", "first_rusherId", "n_rushers"]],
                        on=KEYS, how="inner")
    duels["won_first"] = duels.rusherId == duels.first_rusherId
    nm = pl[["nflId", "displayName"]]
    duels = duels.merge(nm.rename(columns={"nflId": "rusherId", "displayName": "rusher"}), on="rusherId", how="left")
    duels = duels.merge(nm.rename(columns={"nflId": "blockerId", "displayName": "blocker"}), on="blockerId", how="left")
    # the first rusher's blocker, in the plays table
    fb = duels[duels.won_first][KEYS + ["blockerId", "blocker", "blocker_pos"]].drop_duplicates(KEYS)
    tab = tab.merge(fb.rename(columns={"blockerId": "first_blockerId", "blocker": "first_blocker",
                                       "blocker_pos": "first_blocker_pos"}), on=KEYS, how="left")
    n_total = t["plays"].shape[0]
    skipped = {"plays_total": n_total, "plays_computed": len(tab),
               "skipped_no_qb_rusher_or_snap": n_total - len(tab)}
    return tab, duels, skipped


def summary(tab: pd.DataFrame, skipped: dict) -> None:
    print(f"[cpt] radius={PRESSURE_RADIUS} yd | plays={len(tab)} (skipped: {skipped['skipped_no_qb_rusher_or_snap']}) | "
          f"median CPT={tab.cpt.median():.2f}s | censored={tab.censored.mean():.1%} | "
          f"CPT=0: {(tab.cpt == 0).mean():.1%}")


if __name__ == "__main__":
    t = load_all()
    tab, duels, sk = build_table(t)
    summary(tab, sk)
    print(tab.head(3).T)
