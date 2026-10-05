#!/usr/bin/env python3
"""Multi-panel comparison of ref, suff and suff-nocdr."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm

import common
from self_sufficiency import fossil_self_sufficiency

VRE_COLORS = ["#f9d002", "#235ebc", "#6895dd"]
VRE_LABELS = ["Solar", "Onshore wind", "Offshore wind"]
PRICE_COLORS = {"AC": "#110d63", "H2": "#bf13a0", "urban central heat": "#e8beac"}
PRICE_NAMES = {"AC": "Electricity", "H2": "Hydrogen", "urban central heat": "District heating"}


def main() -> None:
    regions = gpd.read_file(common.regions_path()).set_index("name")
    curtailment = common.system_curtailment_twh()
    co2 = {}
    for scenario in common.SCENARIOS:
        annual = common.co2_per_capita(scenario)
        co2[scenario] = annual["2030"] * 5 + annual["2040"] * 10 + annual["2050"] * 10
    co2_max = float(co2["ref"].max())
    co2_bounds = [25, 40, 55, 70, 85, 100, 130, 180, co2_max]
    co2_cmap = plt.colormaps["Reds"].resampled(len(co2_bounds) - 1)
    co2_norm = BoundaryNorm(co2_bounds, co2_cmap.N, clip=True)
    prices = {scenario: common.read_csv(scenario, "prices").set_index("carrier") for scenario in common.SCENARIOS}

    price_values = []
    for scenario in common.SCENARIOS:
        for carrier in PRICE_COLORS:
            price_values.extend(
                prices[scenario].loc[carrier, [str(year) for year in common.HORIZONS]].astype(float).tolist()
            )
    price_max = max(price_values) * 1.08
    price_min = min(0.0, min(price_values))

    fig = plt.figure(figsize=(16, 23))
    outer = fig.add_gridspec(4, 1, height_ratios=[1.7, 1.55, 1.95, 1.7], hspace=0.48, left=0.11, right=0.94, top=0.98, bottom=0.03)
    row_names = [
        "(a) Gas and oil self-sufficiency",
        "(b) VRE curtailment",
        "(c) Cumulative CO2 per capita",
        "(d) Wholesale prices",
    ]

    ax = fig.add_subplot(outer[0].subgridspec(1, 5, width_ratios=[0.4, 1, 1, 1, 0.4], wspace=0)[0, 1:4])
    markers = {"ref": "o", "suff": "s", "suff-nocdr": "D"}
    years = ["2020", "2030", "2040", "2050"]
    for scenario in common.SCENARIOS:
        shares = fossil_self_sufficiency(scenario)
        ax.plot(
            years,
            [shares["gas"].get(int(year), np.nan) for year in years],
            color=common.SCENARIO_COLORS[scenario],
            marker=markers[scenario],
            linestyle="-",
            linewidth=1.15,
            markersize=5,
            label=f"{common.LABELS[scenario]} gas",
        )
        ax.plot(
            years,
            [shares["oil"].get(int(year), np.nan) for year in years],
            color=common.SCENARIO_COLORS[scenario],
            marker=markers[scenario],
            linestyle="--",
            linewidth=1.15,
            markersize=5,
            label=f"{common.LABELS[scenario]} oil",
        )
    ax.set_ylim(0, 105)
    ax.set_ylabel("Self-sufficiency [%]", fontsize=17)
    ax.tick_params(labelsize=16)
    ax.grid(True, linestyle="--", linewidth=0.4)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=6, frameon=False, fontsize=15)

    ax = fig.add_subplot(outer[1].subgridspec(1, 5, width_ratios=[0.4, 1, 1, 1, 0.4], wspace=0)[0, 1:4])
    techs = list(common.VRE_GROUPS)
    bar_width = 0.24
    group = 1.15
    tick_positions = []
    tick_labels = []
    year_positions = []
    for yi, year in enumerate(common.HORIZONS):
        group_positions = []
        for si, scenario in enumerate(common.SCENARIOS):
            pos = yi * group + (si - 1) * bar_width
            group_positions.append(pos)
            part = curtailment[(curtailment["scenario"] == scenario) & (curtailment["year"] == year)]
            bottom = 0.0
            for tech, color, label in zip(techs, VRE_COLORS, VRE_LABELS):
                height = float(part.loc[part["tech"] == tech, "twh"].sum())
                ax.bar(
                    pos,
                    height,
                    bar_width * 0.92,
                    bottom=bottom,
                    color=color,
                    edgecolor="0.2",
                    linewidth=0.3,
                    label=label if yi == 0 and si == 0 else None,
                )
                bottom += height
        tick_positions.extend(group_positions)
        tick_labels.extend(common.LABELS[scenario] for scenario in common.SCENARIOS)
        year_positions.append(sum(group_positions) / len(group_positions))
    ax.set_xticks(tick_positions, tick_labels, fontsize=14)
    ax.tick_params(axis="y", labelsize=16)
    ax.set_ylabel("Curtailment [TWh]", fontsize=17)
    ax.grid(True, axis="y", linestyle="--", linewidth=0.4)
    for pos, year in zip(year_positions, common.HORIZONS):
        ax.text(pos, 1.03, str(year), transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=16)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=False, fontsize=15)

    map_row = outer[2].subgridspec(2, 3, height_ratios=[1.4, 0.08], hspace=0.08, wspace=0.012)
    for col, scenario in enumerate(common.SCENARIOS):
        ax = fig.add_subplot(map_row[0, col])
        frame = regions.join(co2[scenario].rename("co2"), how="left")
        frame.plot(
            column="co2",
            ax=ax,
            cmap=co2_cmap,
            norm=co2_norm,
            linewidth=0.35,
            edgecolor="0.25",
            missing_kwds={"color": "0.85"},
        )
        ax.set_axis_off()
        ax.set_title(common.LABELS[scenario], fontsize=18)
    colorbar_row = map_row[1, :].subgridspec(1, 5, width_ratios=[1.1, 1, 1, 1, 1.1], wspace=0)
    cax = fig.add_subplot(colorbar_row[0, 1:4])
    colorbar = fig.colorbar(
        plt.cm.ScalarMappable(cmap=co2_cmap, norm=co2_norm),
        cax=cax,
        orientation="horizontal",
    )
    colorbar.set_label("t/capita to 2050", fontsize=17)
    colorbar.ax.tick_params(labelsize=15)

    ax = fig.add_subplot(outer[3].subgridspec(1, 5, width_ratios=[0.4, 1, 1, 1, 0.4], wspace=0)[0, 1:4])
    line_styles = {"ref": "-", "suff": "--", "suff-nocdr": ":"}
    for scenario in common.SCENARIOS:
        for carrier, marker in zip(PRICE_COLORS, ["o", "s", "v"]):
            series = prices[scenario].loc[carrier, [str(year) for year in common.HORIZONS]].astype(float)
            ax.plot(
                [str(year) for year in common.HORIZONS],
                series.values,
                color=PRICE_COLORS[carrier],
                marker=marker,
                linestyle=line_styles[scenario],
                linewidth=1.15,
                markersize=5,
                label=f"{common.LABELS[scenario]} {PRICE_NAMES[carrier].lower()}",
            )
    ax.set_ylim(price_min, price_max)
    ax.set_ylabel("Price [EUR/MWh]", fontsize=17)
    ax.tick_params(labelsize=16)
    ax.grid(True, linestyle="--", linewidth=0.4)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=3, frameon=False, fontsize=15)

    for name, slot in zip(row_names, outer):
        position = slot.get_position(fig)
        fig.text(
            0.012,
            position.y0 + position.height / 2,
            name,
            rotation=90,
            va="center",
            ha="center",
            fontsize=18,
            fontweight="bold",
        )

    print(common.savefig(fig, "multi"))


if __name__ == "__main__":
    main()
