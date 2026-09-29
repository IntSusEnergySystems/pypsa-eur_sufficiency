#!/usr/bin/env python3
"""Gas self-sufficiency maps and trajectories for the three scenarios.

Self-sufficiency is domestic renewable gas (BioSNG, biogas upgrading and
Sabatier) divided by total gas supply at each country. The previous ChartData
workbooks are not produced by the current workflow.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

import common

DOMESTIC = ["BioSNG", "BioSNG CC", "biogas to gas", "biogas to gas CC", "Sabatier"]
SUPPLY = DOMESTIC + ["gas"]


def country_self_sufficiency(scenario: str) -> pd.DataFrame:
    balance = common.read_csv(scenario, "nodal_energy_balance")
    gas = balance.loc[balance["bus_carrier"] == "gas"].copy()
    gas = gas.loc[gas["location"] != "EU"]
    rows = []
    for year in common.HORIZONS:
        year = str(year)
        grouped = gas.groupby(["location", "carrier"])[year].sum().unstack(fill_value=0.0)
        domestic = grouped.reindex(columns=DOMESTIC, fill_value=0.0).clip(lower=0).sum(axis=1)
        supply = grouped.reindex(columns=SUPPLY, fill_value=0.0).clip(lower=0).sum(axis=1)
        share = (domestic / supply.replace(0, pd.NA) * 100).fillna(0.0)
        rows.append(share.rename(year))
    return pd.concat(rows, axis=1)


def system_share(table: pd.DataFrame, scenario: str) -> pd.Series:
    balance = common.read_csv(scenario, "energy_balance")
    gas = balance.loc[balance["bus_carrier"] == "gas"]
    values = {}
    for year in common.HORIZONS:
        column = str(year)
        grouped = gas.groupby("carrier")[column].sum()
        domestic = float(grouped.reindex(DOMESTIC, fill_value=0.0).clip(lower=0).sum())
        supply = float(grouped.reindex(SUPPLY, fill_value=0.0).clip(lower=0).sum())
        values[year] = 100.0 * domestic / supply if supply else 0.0
    return pd.Series(values, name=common.LABELS[scenario])


def main() -> None:
    regions = gpd.read_file(common.regions_path("ref")).set_index("name")
    tables = {scenario: country_self_sufficiency(scenario) for scenario in common.SCENARIOS}

    fig = plt.figure(figsize=(14, 10))
    grid = fig.add_gridspec(
        len(common.SCENARIOS),
        len(common.HORIZONS) + 1,
        width_ratios=[1, 1, 1, 0.05],
        wspace=0.05,
        hspace=0.16,
        left=0.02,
        right=0.92,
        top=0.90,
        bottom=0.04,
    )
    for row, scenario in enumerate(common.SCENARIOS):
        data = tables[scenario]
        for col, year in enumerate(common.HORIZONS):
            ax = fig.add_subplot(grid[row, col])
            frame = regions.join(data[str(year)].rename("share"), how="left")
            frame.plot(ax=ax, column="share", cmap="RdYlGn", vmin=0, vmax=100, linewidth=0.2, edgecolor="grey")
            ax.set_axis_off()
            ax.set_title(f"{common.LABELS[scenario]} {year}", fontsize=11)
    cax = fig.add_subplot(grid[:, -1])
    fig.colorbar(
        plt.cm.ScalarMappable(cmap="RdYlGn", norm=plt.Normalize(vmin=0, vmax=100)),
        cax=cax,
        label="Self-sufficiency [%]",
    )
    fig.suptitle("Gas self-sufficiency [% of gas supply]", fontsize=14)
    print(common.savefig(fig, "self_sufficiency_maps"))

    fig, ax = plt.subplots(figsize=(8, 5))
    styles = {"ref": ("o", "-"), "suff": ("s", "--"), "suff-nocdr": ("D", ":")}
    for scenario in common.SCENARIOS:
        series = system_share(tables[scenario], scenario)
        marker, linestyle = styles[scenario]
        ax.plot(
            series.index.astype(str),
            series.values,
            label=common.LABELS[scenario],
            color=common.SCENARIO_COLORS[scenario],
            marker=marker,
            linestyle=linestyle,
            linewidth=2.5,
            markersize=8,
        )
    ax.set_ylabel("Gas self-sufficiency [%]")
    ax.set_ylim(0, 100)
    ax.grid(True, linestyle="--", linewidth=0.4)
    ax.legend()
    fig.tight_layout()
    print(common.savefig(fig, "self_sufficiency"))


if __name__ == "__main__":
    main()
