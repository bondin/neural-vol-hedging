from __future__ import annotations

import glob
import os

import pandas as pd
import pytest


def _find_latest_parquet(default_glob: str) -> str:
    files = glob.glob(default_glob, recursive=True)
    if not files:
        raise FileNotFoundError(
            "No parquet files found. "
            "Set DATA_GLOB env var or generate processed data before tests."
        )
    return max(files, key=os.path.getmtime)


@pytest.fixture(scope="session")
def df_proc() -> pd.DataFrame:
    pat = os.environ.get(
        "DATA_GLOB",
        "data/processed/deribit/date=*/underlying=*/smile_*.parquet",
    )
    path = _find_latest_parquet(pat)
    df = pd.read_parquet(path)
    df["slot_time_utc"] = pd.to_datetime(df["slot_time_utc"], utc=True)
    df["expiry_utc"] = pd.to_datetime(df["expiry_utc"], utc=True)
    return df
