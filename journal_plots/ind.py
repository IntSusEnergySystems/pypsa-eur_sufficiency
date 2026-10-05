#!/usr/bin/env python3
"""VRE curtailment, CO2 per capita and wholesale prices for three scenarios."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

import common

PRICE_CARRIERS = ["AC", "H2", "urban central heat"]
PRICE_NAMES = {"AC": "Electricity", "H2": "Hydrogen", "urban central heat": "District heating"}
PRICE_COLORS = {"AC": "#110d63", "H2": "#bf13a0", "urban central heat": "#e8beac"}
VRE_COLORS = ["#f9d002", "#235ebc", "#6895dd"]
VRE_LABELS = ["Solar", "Onshore wind", "Offshore wind"]


def co2_per_capita(scenario: str) -> pd.DataFrame:
    return common.co2_per_capita(scenario)


def main() -> None:
    curtailment = common.system_curtailment_twh()
    regions = gpd.read_file(common.regions_path()).set_index("name")
    fig = plt.figure(figsize=(16, 12))

    for col, scenario in enumerate(common.SCENARIOS):
        for i, year in enumerate(common.HORIZONS):
            ax = fig.add_subplot(3, 9, col * 3 + i + 1)
            part = curtailment[(curtailment["scenario"] == scenario) & (curtailment["year"] == year)]
            values = [float(part.loc[part["tech"] == tech, "twh"].sum()) for tech in common.VRE_GROUPS]
            total = sum(values)
            radius = 0.6 + 0.4 * (total / max(curtailment.groupby(["scenario", "year"])["twh"].sum().max(), 1))
            ax.pie(values, startangle=90, colors=VRE_COLORS, radius=radius, wedgeprops={"width": 0.45})
            ax.set_title(f"{common.LABELS[scenario]}\n{year}", fontsize=9)
            ax.text(0, -1.35, f"{total:.0f} TWh", ha="center", fontsize=8)

    handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=color, markersize=10, label=label)
        for color, label in zip(VRE_COLORS, VRE_LABELS)
    ]
    fig.legend(handles=handles, loc="upper center", ncol=3, frameon=False)

    # CO2 per capita maps, one row.
    co2 = {scenario: co2_per_capita(scenario) for scenario in common.SCENARIOS}
    stacked = pd.concat(co2.values())
    values = stacked.to_numpy()
    limit = float(np.nanmax(values)) if np.isfinite(values).any() else 1.0
    if limit == 0:
        limit = 1.0
    map_fig = plt.figure(figsize=(12, 10))
    map_grid = map_fig.add_gridspec(
        len(common.SCENARIOS),
        len(common.HORIZONS) + 1,
        width_ratios=[1, 1, 1, 0.05],
        wspace=0.05,
        hspace=0.18,
        left=0.02,
        right=0.92,
    )
    for row, scenario in enumerate(common.SCENARIOS):
        for col, year in enumerate(common.HORIZONS):
            ax = map_fig.add_subplot(map_grid[row, col])
            frame = regions.join(co2[scenario][str(year)].rename("co2"), how="left")
            frame.plot(
                column="co2",
                ax=ax,
                cmap="YlOrRd",
                vmin=0,
                vmax=limit,
                linewidth=0.35,
                edgecolor="0.3",
            )
            ax.set_axis_off()
            ax.set_title(f"{common.LABELS[scenario]} {year}", fontsize=11)
    cax = map_fig.add_subplot(map_grid[:, -1])
    map_fig.colorbar(
        plt.cm.ScalarMappable(cmap="YlOrRd", norm=plt.Normalize(vmin=0, vmax=limit)),
        cax=cax,
        label="CO2 [t/capita]",
    )

    price_fig, price_ax = plt.subplots(figsize=(8, 5))
    markers = ["o", "s", "v"]
    for scenario in common.SCENARIOS:
        prices = common.read_csv(scenario, "prices").set_index("carrier")
        for carrier, marker in zip(PRICE_CARRIERS, markers):
            series = prices.loc[carrier, [str(year) for year in common.HORIZONS]].astype(float)
            price_ax.plot(
                [str(year) for year in common.HORIZONS],
                series.values,
                color=PRICE_COLORS[carrier],
                linestyle={"ref": "-", "suff": "--", "suff-nocdr": ":"}[scenario],
                marker=marker,
                label=f"{PRICE_NAMES[carrier]} ({common.LABELS[scenario]})",
            )
    price_ax.set_ylabel("Average price [EUR/MWh]")
    price_ax.grid(True, linestyle="--", alpha=0.4)
    price_ax.legend(fontsize=8, ncol=2)
    price_fig.tight_layout()

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    print(common.savefig(fig, "curtailment_pies"))
    print(common.savefig(map_fig, "co2_per_capita"))
    print(common.savefig(price_fig, "wholesale_prices"))


if __name__ == "__main__":
    main()
