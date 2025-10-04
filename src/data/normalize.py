# src/data/normalize.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd

# -----------------------------
# Time helpers
# -----------------------------


def to_utc_ms(ts: Any) -> int:
    """
    Convert various timestamp inputs to millisecond UTC epoch.
    Accepts ISO strings, pandas/np datetimes, seconds or milliseconds as int/float.
    """
    if ts is None or (isinstance(ts, float) and pd.isna(ts)):
        raise ValueError("timestamp is None/NaN")
    # numeric? assume seconds unless looks like ms
    if isinstance(ts, (int, float)) and not isinstance(ts, bool):
        return int(ts if ts > 10**12 else ts * 1000)
    # parse as datetime
    dt = pd.to_datetime(ts, utc=True)
    return int(dt.value // 10**6)


# -----------------------------
# Instrument parsing (Deribit-like)
# -----------------------------

_DERIBIT_OPT = re.compile(
    r"^(?P<underlying>[A-Z0-9]+)-(?P<day>\d{1,2})(?P<mon>[A-Z]{3})(?P<year>\d{2})-(?P<strike>\d+(?:\.\d+)*)-(?P<opt>[CP])$"
)
_DERIBIT_FUT = re.compile(
    r"^(?P<underlying>[A-Z0-9]+)-(?P<day>\d{1,2})(?P<mon>[A-Z]{3})(?P<year>\d{2})$"
)

_MON_MAP = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


@dataclass
class ParsedInstrument:
    kind: str  # 'option' | 'future'
    underlying: str
    maturity: str  # ISO date yyyy-mm-dd
    option_type: Optional[str] = None  # 'C'|'P'|None
    strike: Optional[float] = None


def parse_instrument_name(name: str) -> ParsedInstrument:
    """
    Parse Deribit-like instrument name, e.g. 'BTC-30DEC24-65000-P' or 'BTC-30DEC24'.
    """
    m = _DERIBIT_OPT.match(name)
    if m:
        d = m.groupdict()
        day = int(d["day"])
        mon = _MON_MAP[d["mon"].upper()]
        year = 2000 + int(d["year"])
        mat = f"{year:04d}-{mon:02d}-{day:02d}"
        return ParsedInstrument(
            kind="option",
            underlying=d["underlying"],
            maturity=mat,
            option_type=d["opt"],
            strike=float(d["strike"]),
        )
    m = _DERIBIT_FUT.match(name)
    if m:
        d = m.groupdict()
        day = int(d["day"])
        mon = _MON_MAP[d["mon"].upper()]
        year = 2000 + int(d["year"])
        mat = f"{year:04d}-{mon:02d}-{day:02d}"
        return ParsedInstrument(
            kind="future",
            underlying=d["underlying"],
            maturity=mat,
            option_type=None,
            strike=None,
        )
    # Fallback: unknown format
    return ParsedInstrument(
        kind="unknown", underlying="", maturity="", option_type=None, strike=None
    )


def add_parsed_columns(
    df: pd.DataFrame, instrument_col: str = "instrument_name"
) -> pd.DataFrame:
    """
    Derive `kind`, `maturity`, `option_type`, `strike`, `underlying` from instrument name if missing.
    """
    out = df.copy()
    if instrument_col not in out.columns:
        return out
    parsed = out[instrument_col].astype(str).map(parse_instrument_name)
    out["kind"] = out.get("kind", pd.Series([None] * len(out))).fillna(
        parsed.map(lambda p: p.kind)
    )
    out["maturity"] = out.get("maturity", pd.Series([None] * len(out))).fillna(
        parsed.map(lambda p: p.maturity)
    )
    out["option_type"] = out.get("option_type", pd.Series([None] * len(out))).fillna(
        parsed.map(lambda p: p.option_type)
    )
    out["strike"] = out.get("strike", pd.Series([None] * len(out))).fillna(
        parsed.map(lambda p: p.strike)
    )
    out["underlying"] = out.get("underlying", pd.Series([None] * len(out))).fillna(
        parsed.map(lambda p: p.underlying)
    )
    return out


# -----------------------------
# Column coalescing and typing
# -----------------------------

ALIASES = {
    "slot_time_utc": ["slot_time_utc"],
    "timestamp": ["timestamp_utc"],
    "instrument_name": ["instrument_name", "symbol", "inst"],
    "bid": ["best_bid_price", "bid_price", "bid"],
    "ask": ["best_ask_price", "ask_price", "ask"],
    "mark_price": ["mark_price", "mark", "last_price"],
    "iv": ["mark_iv", "iv", "implied_volatility"],
    "delta": ["delta"],
    "gamma": ["gamma"],
    "vega": ["vega"],
    "theta": ["theta"],
    "F": ["underlying_price"],
    "S": ["index_price"],
    "volume": ["volume", "volume_24h"],
    "open_interest": ["open_interest", "oi"],
    "maturity": [
        "maturity",
        "expiry_utc",
        "expiration",
        "expiration_date",
        "expiration_timestamp",
    ],
    "strike": ["strike", "k", "strike_price"],
    "option_type": ["option_type", "is_call", "call_put", "right"],
    "kind": ["kind", "instrument_type", "type"],
}

NUMERIC_TARGETS = {
    "bid": float,
    "ask": float,
    "mark_price": float,
    "iv": float,
    "delta": float,
    "gamma": float,
    "vega": float,
    "theta": float,
    "underlying_price": float,
    "strike": float,
    "volume": float,
    "open_interest": float,
    "S": float,
    "F": float,
}


def coalesce_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a normalized DataFrame with canonical columns by picking first existing alias.
    """
    out = df.copy()
    for target, candidates in ALIASES.items():
        if target in out.columns:
            continue
        for c in candidates:
            if c in out.columns:
                out[target] = out[c]
                break
    # timestamp → utc ms int64
    if "timestamp" in out.columns:
        out["timestamp"] = out["timestamp"].map(to_utc_ms)
    # option_type normalization to {'C','P', None}
    if "option_type" in out.columns:

        def _norm_opt(x):
            if pd.isna(x):
                return None
            s = str(x).upper().strip()
            if s in ("C", "CALL", "1", "TRUE"):
                return "C"
            if s in ("P", "PUT", "0", "FALSE"):
                return "P"
            return None

        out["option_type"] = out["option_type"].map(_norm_opt)
    # numeric casts
    for col, typ in NUMERIC_TARGETS.items():
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
            if col == "iv":
                out[col] = out[col] / 100.0
    return out


def standardize(
    df: pd.DataFrame, *, instrument_col: str = "instrument_name"
) -> pd.DataFrame:
    """
    Coalesce aliases, parse instrument name, add derived columns, and sort/deduplicate.
    """
    out = coalesce_columns(df)
    out = add_parsed_columns(out, instrument_col=instrument_col)
    # sort & dedup
    sort_cols = [c for c in ["instrument_name", "slot_time_utc"] if c in out.columns]
    if sort_cols:
        out = (
            out.sort_values(sort_cols)
            .drop_duplicates(sort_cols, keep="last")
            .reset_index(drop=True)
        )
    return out
