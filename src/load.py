"""Loads the Big Data Bowl 2023 data (NFL 2021 season, weeks 1-8) with a parquet cache.

Quick usage:  python -m src.load   (DEBUG=1 for 5 games only)
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CACHE_DIR = ROOT / "cache"
FPS = 10                                   # 10 frames/s: frameId +1 = 0.1 s
DEBUG = os.environ.get("DEBUG", "0") == "1"  # DEBUG=1 -> 5 games
N_DEBUG_GAMES = 5

SNAP_EVENTS = ("ball_snap", "autoevent_ballsnap")
THROW_EVENTS = ("pass_forward", "autoevent_passforward")
# end of play: throw, sack, or (failing that) last frame. We take whichever comes first.
END_EVENTS = THROW_EVENTS + ("qb_sack", "qb_strip_sack", "pass_shovel", "run")

TRACK_COLS = ["gameId", "playId", "nflId", "frameId", "team", "playDirection",
              "x", "y", "s", "a", "o", "dir", "event"]
TRACK_DTYPES = {"gameId": "int64", "playId": "int32", "frameId": "int16",
                "x": "float32", "y": "float32", "s": "float32", "a": "float32",
                "o": "float32", "dir": "float32", "team": "category",
                "playDirection": "category", "event": "category"}


def _suffix() -> str:
    return "_debug" if DEBUG else ""


def load_tables() -> dict:
    """Loads games, plays, players, pff (small files, no cache needed)."""
    t = {n: pd.read_csv(DATA_DIR / f"{n}.csv", na_values=["NA"])
         for n in ("games", "plays", "players", "pffScoutingData")}
    t["players"]["nflId"] = t["players"]["nflId"].astype("int64")
    return t


def normalize_direction(df: pd.DataFrame) -> pd.DataFrame:
    """Offense always moves right: if playDirection == 'left', x=120-x, y=53.3-y, o/dir+180."""
    left = (df["playDirection"] == "left").to_numpy()
    df["x"] = np.where(left, 120 - df["x"], df["x"]).astype("float32")
    df["y"] = np.where(left, 53.3 - df["y"], df["y"]).astype("float32")
    for c in ("o", "dir"):
        df[c] = np.where(left, (df[c] + 180) % 360, df[c]).astype("float32")
    return df.drop(columns="playDirection")


def _first_event_frame(g: pd.DataFrame, names) -> pd.Series:
    """Per play: frame of the first event among `names` (NaN if none)."""
    ev = g[g["event"].isin(names)]
    return ev.groupby("playId")["frameId"].min()


def _read_game(path: Path) -> pd.DataFrame:
    """Reads one game, normalizes it, keeps the snap -> end-of-play frames. Returns an empty DF if nothing."""
    df = pd.read_csv(path, usecols=TRACK_COLS, dtype=TRACK_DTYPES, na_values=["NA"])
    df["event"] = df["event"].astype("object").replace("None", np.nan)
    df = normalize_direction(df)
    snap = _first_event_frame(df, SNAP_EVENTS).rename("snap_frame")
    end = _first_event_frame(df, END_EVENTS).rename("end_event_frame")
    last = df.groupby("playId")["frameId"].max().rename("last_frame")
    throw = _first_event_frame(df, THROW_EVENTS).rename("throw_frame")
    sack = _first_event_frame(df, ("qb_sack", "qb_strip_sack")).rename("sack_frame")
    meta = pd.concat([snap, end, last, throw, sack], axis=1)
    meta["end_frame"] = meta["end_event_frame"].fillna(meta["last_frame"])
    meta = meta.dropna(subset=["snap_frame"])  # no snap -> skip (counted in load_tracking)
    df = df.merge(meta[["snap_frame", "end_frame"]], left_on="playId", right_index=True)
    df = df[(df["frameId"] >= df["snap_frame"]) & (df["frameId"] <= df["end_frame"])]
    df["event"] = df["event"].astype("category")
    return df


def load_tracking(force: bool = False) -> pd.DataFrame:
    """Normalized tracking, restricted to [snap, end of play], cached as parquet.

    Added columns: snap_frame, end_frame, t = (frameId - snap_frame)/FPS (seconds since the snap).
    """
    CACHE_DIR.mkdir(exist_ok=True)
    cache = CACHE_DIR / f"tracking{_suffix()}.parquet"
    if cache.exists() and not force:
        return pd.read_parquet(cache)
    files = sorted((DATA_DIR / "tracking").glob("tracking_*.csv"))
    if DEBUG:
        files = files[:N_DEBUG_GAMES]
    parts = [p for p in (_read_game(f) for f in tqdm(files, desc="tracking")) if len(p)]
    out = pd.concat(parts, ignore_index=True)
    out["t"] = ((out["frameId"] - out["snap_frame"]) / FPS).astype("float32")
    out.to_parquet(cache, index=False)
    return out


def load_all(force: bool = False) -> dict:
    """Tables + tracking."""
    t = load_tables()
    trk = load_tracking(force)
    if DEBUG:  # restrict the tables to the loaded games
        gids = trk["gameId"].unique()
        for n in ("plays", "pffScoutingData"):
            t[n] = t[n][t[n]["gameId"].isin(gids)]
    t["tracking"] = trk
    return t


def summary(t: dict) -> None:
    trk = t["tracking"]
    n_tr = trk.groupby(["gameId", "playId"]).ngroups
    n_pl = len(t["plays"])
    print(f"[load] mode={'DEBUG' if DEBUG else 'FULL'} | games={trk.gameId.nunique()} | "
          f"plays.csv plays={n_pl} | tracked plays (with snap)={n_tr} | "
          f"skipped (no snap)={n_pl - n_tr} | tracking rows={len(trk):,}")


if __name__ == "__main__":
    summary(load_all())
