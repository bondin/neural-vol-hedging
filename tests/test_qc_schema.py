import pandas as pd

REQUIRED_COLS = [
    "slot_time_utc",
    "underlying",
    "expiry_utc",
    "strike",
    "option_type",
    "bid",
    "ask",
    "mid",
    "iv",
    "delta",
    "gamma",
    "vega",
    "theta",
    "rho",
    "S",
    "F",
]


def test_required_columns_present(df_proc: pd.DataFrame):
    missing = [c for c in REQUIRED_COLS if c not in df_proc.columns]
    assert not missing, f"Missing columns: {missing}"


def test_datetime_tz(df_proc: pd.DataFrame):
    for col in ["slot_time_utc", "expiry_utc"]:
        assert str(df_proc[col].dtype).endswith("UTC]"), f"{col} must be tz-aware UTC"


def test_numeric_types_nullable(df_proc: pd.DataFrame):
    numeric_cols = [
        "strike",
        "bid",
        "ask",
        "mid",
        "iv",
        "delta",
        "gamma",
        "vega",
        "theta",
        "rho",
        "S",
        "F",
    ]
    for c in numeric_cols:
        assert pd.api.types.is_numeric_dtype(df_proc[c]), f"{c} must be numeric dtype"
