#!/usr/bin/env python3
"""Investment as a share of GDP for ref, suff and suff-nocdr.

Bus investment is the sum of annualised capital costs in
``nodal_costs.csv``. The share of GDP uses the same 27-year averaging
convention as the previous map: the 27-year factor cancels, so the plotted
value is mean annual investment divided by national GDP.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

import common


def investment_share(scenario: str) -> pd.Series:
    costs = common.read_csv(scenario, "nodal_costs")
    capital = costs.loc[(costs["cost"] == "capital") & (costs["location"] != "EU")]
    annual = capital.groupby("location")[[str(year) for year in common.HORIZONS]].sum().mean(axis=1)
    gdp = pd.Series(common.GDP_BEUR)
    share = annual / (gdp.reindex(annual.index) * 1e9) * 100
    return share.replace([pd.NA, float("inf")], pd.NA).dropna()


def main() -> None:
    regions = gpd.read_file(common.regions_path()).set_index("name")
    shares = {scenario: investment_share(scenario) for scenario in common.SCENARIOS}
    vmax = max(float(series.max()) for series in shares.values())
    fig = plt.figure(figsize=(7, 12))
    grid = fig.add_gridspec(len(common.SCENARIOS), 2, width_ratios=[1, 0.05], wspace=0.05, hspace=0.08)
    for row, scenario in enumerate(common.SCENARIOS):
        ax = fig.add_subplot(grid[row, 0])
        frame = regions.join(shares[scenario].rename("share"), how="left")
        frame.plot(
            ax=ax,
            column="share",
            cmap="OrRd",
            vmin=0,
            vmax=vmax,
            linewidth=0.3,
            edgecolor="grey",
            missing_kwds={"color": "lightgrey"},
        )
        ax.set_axis_off()
        ax.set_title(common.LABELS[scenario], fontsize=13)
    cax = fig.add_subplot(grid[:, 1])
    fig.colorbar(
        plt.cm.ScalarMappable(cmap="OrRd", norm=plt.Normalize(vmin=0, vmax=vmax)),
        cax=cax,
        label="Mean annual investment [% of GDP]",
    )
    print(common.savefig(fig, "investment_map"))


if __name__ == "__main__":
    main()
