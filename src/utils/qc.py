from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd

IV_MIN, IV_MAX = 0.1, 500.0
DELTA_MIN, DELTA_MAX = -1.0, 1.0


def clip_iv(
    df: pd.DataFrame, vmin: float = IV_MIN, vmax: float = IV_MAX
) -> pd.DataFrame:
    d = df.copy()
    if "iv" in d.columns:
        d["iv_clipped"] = d["iv"].clip(lower=vmin, upper=vmax)
    return d


def add_flags(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    for col in ["bid", "ask", "iv", "delta", "strike", "expiry_utc", "slot_time_utc"]:
        if col not in d.columns:
            d[col] = pd.NA

    d["qc_iv"] = d["iv"].between(IV_MIN, IV_MAX, inclusive="both")
    d["qc_delta"] = d["delta"].between(DELTA_MIN, DELTA_MAX, inclusive="both")
    d["qc_prices"] = (d["ask"].fillna(-1) >= d["bid"].fillna(-1)) & (
        d["bid"].fillna(0) >= 0
    )
    d["qc_strike"] = d["strike"].fillna(-1) > 0
    d["qc_expiry"] = pd.to_datetime(d["expiry_utc"], utc=True) >= pd.to_datetime(
        d["slot_time_utc"], utc=True
    )

    d["qc_pass"] = d[["qc_iv", "qc_delta", "qc_prices", "qc_strike", "qc_expiry"]].all(
        axis=1
    )
    return d


def qc_report(df: pd.DataFrame) -> Dict[str, Tuple[int, float]]:
    n = len(df)
    if n == 0:
        return {}
    rep: Dict[str, Tuple[int, float]] = {}
    for col in ["qc_iv", "qc_delta", "qc_prices", "qc_strike", "qc_expiry", "qc_pass"]:
        if col in df.columns:
            bad = (~df[col]).sum() if col != "qc_pass" else (~df[col]).sum()
            rep[col] = (int(bad), float(bad) / n)
    return rep
