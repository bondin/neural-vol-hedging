import pytest

from utils.qc import add_flags


@pytest.fixture(scope="module")
def df_flags(df_proc):
    return add_flags(df_proc)


def test_iv_range(df_flags):
    bad = df_flags[~df_flags["qc_iv"]]
    rate = len(bad) / max(1, len(df_flags))
    assert rate <= 0.10, f"Too many IV out of range: {len(bad)} rows ({rate:.2%})"


def test_delta_range(df_flags):
    bad = df_flags[~df_flags["qc_delta"]]
    rate = len(bad) / max(1, len(df_flags))
    assert rate <= 0.10, f"Too many delta out of [-1,1]: {rate:.2%}"


def test_prices_logic(df_flags):
    bad = df_flags[~df_flags["qc_prices"]]
    rate = len(bad) / max(1, len(df_flags))
    assert rate <= 0.05, f"ask>=bid>=0 violated in {rate:.2%}"


def test_strike_positive(df_flags):
    bad = df_flags[~df_flags["qc_strike"]]
    rate = len(bad) / max(1, len(df_flags))
    assert rate <= 0.01, f"Non-positive strikes in {rate:.2%}"


def test_expiry_not_past(df_flags):
    bad = df_flags[~df_flags["qc_expiry"]]
    rate = len(bad) / max(1, len(df_flags))
    assert rate <= 0.01, f"Expired rows: {rate:.2%}"


def test_overall_pass(df_flags):
    rate = (~df_flags["qc_pass"]).sum() / max(1, len(df_flags))
    assert rate <= 0.15, f"Too many rows failed overall QC: {rate:.2%}"
