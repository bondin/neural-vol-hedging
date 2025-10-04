import holoviews as hv
import numpy as np
import pandas as pd
from IPython.display import display
from pandas.api.types import CategoricalDtype

hv.extension("bokeh")

renderer = hv.renderer("bokeh")
renderer.theme = "dark_minimal"


def ivplot(df):
    df = df.sort_values(["expiry", "moneyness"])

    p1 = df.hvplot.line(
        x="moneyness",
        xlabel="Moneyness",
        y="iv",
        ylabel="IV",
        clabel="Expiry",
        by="expiry",
        width=700,
        height=450,
    )

    bins = np.arange(-0.4, 0.401, 0.02)
    labels = np.round((bins[:-1] + bins[1:]) / 2, 3)
    df["mny_bin"] = pd.cut(
        df["moneyness"], bins=bins, labels=labels, include_lowest=True
    )

    df["expiry_d"] = pd.to_datetime(df["expiry"]).dt.strftime("%Y-%m-%d")
    y_order = sorted(df["expiry_d"].unique())
    df["expiry_cat"] = df["expiry_d"].astype(
        CategoricalDtype(categories=y_order, ordered=True)
    )

    agg = (
        df.dropna(subset=["mny_bin", "expiry_cat"])
        .groupby(["expiry_cat", "mny_bin"], as_index=False, observed=True)["iv"]
        .mean()
    )

    agg = agg.pivot(index="expiry_cat", columns="mny_bin", values="iv")
    agg = agg.fillna(-1)
    hm = agg.stack().reset_index().rename(columns={0: "iv"})
    p2 = hm.hvplot.heatmap(
        x="mny_bin",
        xlabel="Moneyness",
        y="expiry_cat",
        ylabel="Expiry",
        C="iv",
        clabel="IV",
        cmap="turbo",
        clim=(0, 1),
        width=700,
        height=450,
    )

    display(p1 + p2)
