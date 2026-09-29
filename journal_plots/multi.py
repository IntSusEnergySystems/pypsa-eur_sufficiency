#!/usr/bin/env python3
"""Multi-panel comparison of ref, suff and suff-nocdr."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

import common
from self_sufficiency import system_share

VRE_COLORS = ["#f9d002", "#235ebc", "#6895dd"]
VRE_LABELS = ["Solar", "Onshore wind", "Offshore wind"]
PRICE_COLORS = {"AC": "#110d63", "H2": "#bf13a0", "urban central heat": "#e8beac"}
PRICE_NAMES = {"AC": "Electricity", "H2": "Hydrogen", "urban central heat": "District heating"}


def capacity_factors(scenario: str) -> dict[str, list[float]]:
    factors = common.read_csv(scenario, "capacity_factors")
    nuclear_row = factors.loc[factors["carrier"] == "nuclear", [str(year) for year in common.HORIZONS]]
    caps = common.read_csv(scenario, "capacities")
    energy = common.read_csv(scenario, "energy_balance")
    ccgt_cap = caps.loc[caps["carrier"] == "CCGT", [str(year) for year in common.HORIZONS]].sum()
    ccgt_mwh = energy.loc[
        (energy["carrier"] == "CCGT") & (energy["bus_carrier"] == "AC"),
        [str(year) for year in common.HORIZONS],
    ].sum()
    ccgt = (ccgt_mwh / (ccgt_cap * 8760).replace(0, np.nan)).fillna(0.0)
    nuclear = nuclear_row.sum() if not nuclear_row.empty else ccgt * 0.0
    return {
        "nuclear": [float(nuclear[str(year)]) for year in common.HORIZONS],
        "CCGT": [float(ccgt[str(year)]) for year in common.HORIZONS],
    }


def main() -> None:
    regions = gpd.read_file(common.regions_path()).set_index("name")
    curtailment = common.system_curtailment_twh()
    co2 = {scenario: common.co2_per_capita(scenario) for scenario in common.SCENARIOS}
    finite = np.concatenate([frame.to_numpy().ravel() for frame in co2.values()])
    limit = float(np.nanmax(np.abs(finite))) if np.isfinite(finite).any() else 1.0
    prices = {scenario: common.read_csv(scenario, "prices").set_index("carrier") for scenario in common.SCENARIOS}

    price_values = []
    for scenario in common.SCENARIOS:
        for carrier in PRICE_COLORS:
            price_values.extend(
                prices[scenario].loc[carrier, [str(year) for year in common.HORIZONS]].astype(float).tolist()
            )
    price_max = max(price_values) * 1.08
    price_min = min(0.0, min(price_values))

    fig = plt.figure(figsize=(16, 18))
    outer = fig.add_gridspec(5, 1, height_ratios=[1, 1.15, 1, 1.25, 1], hspace=0.42, left=0.10, right=0.94, top=0.97, bottom=0.03)
    row_names = [
        "(a) Gas self-sufficiency",
        "(b) VRE curtailment",
        "(c) Capacity factors",
        "(d) Net CO2 per capita",
        "(e) Wholesale prices",
    ]

    top = outer[0].subgridspec(1, 3, wspace=0.25)
    ss_axes = []
    for col, scenario in enumerate(common.SCENARIOS):
        ax = fig.add_subplot(top[0, col], sharey=ss_axes[0] if ss_axes else None)
        ss_axes.append(ax)
        series = system_share(None, scenario)
        ax.plot(series.index.astype(str), series.values, color=common.SCENARIO_COLORS[scenario], marker="o", linewidth=2)
        ax.set_ylim(0, 105)
        ax.set_title(common.LABELS[scenario], fontsize=16)
        ax.tick_params(labelsize=13)
        if col == 0:
            ax.set_ylabel("Self-sufficiency [%]", fontsize=14)
        ax.grid(True, linestyle="--", linewidth=0.4)

    pie_row = outer[1].subgridspec(1, 9, wspace=0.35)
    for col, scenario in enumerate(common.SCENARIOS):
        for i, year in enumerate(common.HORIZONS):
            ax = fig.add_subplot(pie_row[0, col * 3 + i])
            part = curtailment[(curtailment["scenario"] == scenario) & (curtailment["year"] == year)]
            values = [float(part.loc[part["tech"] == tech, "twh"].sum()) for tech in common.VRE_GROUPS]
            total = sum(values)
            ax.pie(
                [value if value > 0 else 1e-9 for value in values],
                colors=VRE_COLORS,
                startangle=90,
                wedgeprops={"width": 0.45},
            )
            ax.set_title(f"{year}\n{total:.0f} TWh", fontsize=12)
    pie_handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=color, markersize=8, label=label)
        for color, label in zip(VRE_COLORS, VRE_LABELS)
    ]
    pie_position = outer[1].get_position(fig)
    fig.legend(
        handles=pie_handles,
        loc="upper center",
        bbox_to_anchor=(0.52, pie_position.y0 - 0.005),
        ncol=3,
        frameon=False,
        fontsize=13,
    )

    cf_row = outer[2].subgridspec(1, 3, wspace=0.25)
    cf_axes = []
    for col, scenario in enumerate(common.SCENARIOS):
        ax = fig.add_subplot(cf_row[0, col], sharey=cf_axes[0] if cf_axes else None)
        cf_axes.append(ax)
        factors = capacity_factors(scenario)
        x = np.arange(len(common.HORIZONS))
        width = 0.35
        ax.bar(x - width / 2, factors["nuclear"], width, color="#ff8c00", label="Nuclear")
        ax.bar(x + width / 2, factors["CCGT"], width, color="#a85522", label="CCGT")
        ax.set_xticks(x, [str(year) for year in common.HORIZONS])
        ax.set_ylim(0, 1)
        ax.tick_params(labelsize=13)
        if col == 0:
            ax.set_ylabel("Capacity factor", fontsize=14)
        ax.grid(True, axis="y", linestyle="--", linewidth=0.4)
        if col == 2:
            ax.legend(fontsize=12)

    map_row = outer[3].subgridspec(1, 10, width_ratios=[1] * 9 + [0.08], wspace=0.12)
    for col, scenario in enumerate(common.SCENARIOS):
        for i, year in enumerate(common.HORIZONS):
            ax = fig.add_subplot(map_row[0, col * 3 + i])
            frame = regions.join(co2[scenario][str(year)].rename("co2"), how="left")
            frame.plot(
                column="co2",
                ax=ax,
                cmap="RdBu_r",
                vmin=-limit,
                vmax=limit,
                linewidth=0.35,
                edgecolor="0.25",
            )
            ax.set_axis_off()
            ax.set_title(str(year), fontsize=13)
    cax = fig.add_subplot(map_row[0, -1])
    fig.colorbar(
        plt.cm.ScalarMappable(cmap="RdBu_r", norm=plt.Normalize(vmin=-limit, vmax=limit)),
        cax=cax,
        label="t/capita",
    )

    price_row = outer[4].subgridspec(1, 3, wspace=0.25)
    price_axes = []
    for col, scenario in enumerate(common.SCENARIOS):
        ax = fig.add_subplot(price_row[0, col], sharey=price_axes[0] if price_axes else None)
        price_axes.append(ax)
        for carrier, marker in zip(PRICE_COLORS, ["o", "s", "v"]):
            series = prices[scenario].loc[carrier, [str(year) for year in common.HORIZONS]].astype(float)
            ax.plot(
                [str(year) for year in common.HORIZONS],
                series.values,
                color=PRICE_COLORS[carrier],
                marker=marker,
                label=PRICE_NAMES[carrier],
            )
        ax.set_ylim(price_min, price_max)
        ax.tick_params(labelsize=13)
        if col == 0:
            ax.set_ylabel("Price [EUR/MWh]", fontsize=14)
        ax.grid(True, linestyle="--", linewidth=0.4)
        if col == 2:
            ax.legend(fontsize=12)

    for name, slot in zip(row_names, outer):
        position = slot.get_position(fig)
        fig.text(0.012, position.y0 + position.height / 2, name, rotation=90, va="center", ha="center", fontsize=14)

    print(common.savefig(fig, "multi"))


if __name__ == "__main__":
    main()
