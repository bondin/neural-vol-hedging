import pandas as pd


def test_basic_dataframe_ops():
    df = pd.DataFrame({"maturity": [7, 14], "strike": [100, 105], "iv": [0.2, 0.22]})
    assert not df.empty
    assert set(df.columns) == {"maturity", "strike", "iv"}
    df["moneyness"] = df["strike"] / 100.0
    assert df["moneyness"].iloc[0] == 1.0
