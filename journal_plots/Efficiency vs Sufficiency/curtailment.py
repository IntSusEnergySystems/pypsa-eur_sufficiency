#!/usr/bin/env python3
"""Country maps of VRE curtailment for ref, suff and suff-nocdr."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

import common

TECHS = ["solar", "onwind", "offwind"]
TECH_LABELS = {"solar": "Solar PV", "onwind": "Onshore wind", "offwind": "Offshore wind"}
CMAPS = {"solar": "OrRd", "onwind": "Blues", "offwind": "Greens"}


def main() -> None:
    regions = gpd.read_file(common.regions_path()).set_index("name")
    frames = [
        common.country_vre_curtailment(scenario, year)
        for scenario in common.SCENARIOS
        for year in common.HORIZONS
    ]
    data = pd.concat(frames, ignore_index=True)
    n_maps = len(common.SCENARIOS) * len(common.HORIZONS)
    fig = plt.figure(figsize=(16, 10))
    grid = fig.add_gridspec(
        len(TECHS),
        n_maps + 1,
        width_ratios=[1] * n_maps + [0.06],
        wspace=0.05,
        hspace=0.12,
        left=0.06,
        right=0.96,
        top=0.90,
        bottom=0.04,
    )
    for row, tech in enumerate(TECHS):
        vmax = float(data.loc[data["tech"] == tech, "twh"].max())
        vmax = max(vmax, 1e-6)
        for s_i, scenario in enumerate(common.SCENARIOS):
            for y_i, year in enumerate(common.HORIZONS):
                ax = fig.add_subplot(grid[row, s_i * len(common.HORIZONS) + y_i])
                subset = data[
                    (data["scenario"] == scenario) & (data["year"] == year) & (data["tech"] == tech)
                ].set_index("country")["twh"]
                frame = regions.join(subset.rename("twh"), how="left")
                frame.plot(
                    ax=ax,
                    column="twh",
                    cmap=CMAPS[tech],
                    vmin=0,
                    vmax=vmax,
                    linewidth=0.3,
                    edgecolor="0.35",
                    missing_kwds={"color": "whitesmoke"},
                )
                ax.set_axis_off()
                if row == 0:
                    ax.set_title(f"{common.LABELS[scenario]}\n{year}", fontsize=9)
        cax = fig.add_subplot(grid[row, -1])
        fig.colorbar(
            plt.cm.ScalarMappable(cmap=CMAPS[tech], norm=plt.Normalize(vmin=0, vmax=vmax)),
            cax=cax,
            label="TWh" if row == 1 else "",
        )
        fig.text(
            0.015,
            grid[row, 0].get_position(fig).y0 + grid[row, 0].get_position(fig).height / 2,
            TECH_LABELS[tech],
            rotation=90,
            va="center",
            ha="center",
            fontsize=11,
        )
    fig.suptitle("VRE curtailment", fontsize=14)
    print(common.savefig(fig, "curtailment_maps"))


if __name__ == "__main__":
    main()
