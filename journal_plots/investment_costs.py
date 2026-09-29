#!/usr/bin/env python3
"""Annual and period-average investment costs for the three scenarios."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import pandas as pd

import common

GROUP_COLORS = {
    "Wind": "#235ebc",
    "Solar": "#f9d002",
    "Nuclear": "#ff8c00",
    "Hydro": "#298c81",
    "Hydrogen": "#bf13a0",
    "E-fuels": "#46caf0",
    "Heat pumps and boilers": "#e8beac",
    "Batteries": "#7dcea0",
    "Electricity grid": "#110d63",
    "Fossil supply": "#545454",
    "CCS and DAC": "#4f1745",
    "Biomass": "#baa741",
    "Gas and oil plant": "#a85522",
    "Ammonia": "#17becf",
    "Thermal storage": "#f3afa3",
    "Other": "#333333",
}

GROUPS = {
    "Wind": ["onwind", "offwind-ac", "offwind-dc", "offwind-float"],
    "Solar": ["solar", "solar rooftop", "solar-hsat", "rural solar thermal", "urban central solar thermal", "urban decentral solar thermal"],
    "Nuclear": ["nuclear", "uranium"],
    "Hydro": ["hydro", "ror", "PHS"],
    "Hydrogen": [
        "H2 Electrolysis",
        "H2 Fuel Cell",
        "H2 Store",
        "H2 pipeline",
        "H2 pipeline retrofitted",
        "H2 turbine",
        "SMR",
        "SMR CC",
    ],
    "E-fuels": ["Fischer-Tropsch", "methanolisation", "Sabatier", "methanol"],
    "Heat pumps and boilers": [
        "rural air heat pump",
        "rural ground heat pump",
        "urban central air heat pump",
        "urban decentral air heat pump",
        "rural resistive heater",
        "urban central resistive heater",
        "urban decentral resistive heater",
        "rural gas boiler",
        "rural oil boiler",
        "urban central gas boiler",
        "urban decentral gas boiler",
        "urban decentral oil boiler",
    ],
    "Batteries": [
        "battery",
        "battery charger",
        "battery discharger",
        "home battery",
        "home battery charger",
        "home battery discharger",
    ],
    "Electricity grid": ["AC", "DC", "electricity distribution grid"],
    "Fossil supply": ["gas", "coal", "lignite", "oil", "oil primary"],
    "CCS and DAC": [
        "DAC",
        "CO2 pipeline",
        "co2 sequestered",
        "co2 stored",
        "process emissions CC",
        "gas for industry CC",
        "solid biomass for industry CC",
    ],
    "Biomass": [
        "BioSNG",
        "BioSNG CC",
        "biogas",
        "biogas to gas",
        "biogas to gas CC",
        "biomass to liquid",
        "biomass to liquid CC",
        "solid biomass",
        "solid biomass transport",
        "urban decentral biomass boiler",
        "rural biomass boiler",
        "urban central solid biomass CHP",
        "urban central solid biomass CHP CC",
        "waste CHP",
        "waste CHP CC",
    ],
    "Gas and oil plant": ["CCGT", "OCGT", "urban central gas CHP", "urban central gas CHP CC"],
    "Ammonia": ["Haber-Bosch", "ammonia cracker", "ammonia store"],
    "Thermal storage": [
        "urban central water pits",
        "urban central water pits charger",
        "urban central water pits discharger",
        "urban central water tanks",
        "urban central water tanks charger",
        "urban central water tanks discharger",
        "urban decentral water tanks",
        "urban decentral water tanks charger",
        "urban decentral water tanks discharger",
        "rural water tanks",
        "rural water tanks charger",
        "rural water tanks discharger",
    ],
}

REPLACEMENT = {carrier: group for group, carriers in GROUPS.items() for carrier in carriers}


def capital_by_tech(scenario: str) -> pd.DataFrame:
    costs = common.read_csv(scenario, "costs")
    capital = costs.loc[costs["cost"] == "capital", ["carrier", "2030", "2040", "2050"]].copy()
    capital["tech"] = capital["carrier"].map(REPLACEMENT).fillna("Other")
    return capital.groupby("tech", as_index=False)[["2030", "2040", "2050"]].sum()


def main() -> None:
    annual = []
    totals = {}
    for scenario in common.SCENARIOS:
        table = capital_by_tech(scenario)
        # Each solved year is an annualised cost. The period total follows the
        # previous convention: the mean of the three snapshot years, held for 27 years.
        mean_annual = table.set_index("tech")[["2030", "2040", "2050"]].mean(axis=1)
        totals[common.LABELS[scenario]] = float(mean_annual.sum() * 27)
        wide = table.melt(id_vars="tech", var_name="year", value_name="eur")
        wide["column"] = wide["year"] + "\n" + common.LABELS[scenario]
        annual.append(wide)

    combined = pd.concat(annual, ignore_index=True)
    order = [
        f"{year}\n{common.LABELS[scenario]}"
        for year in ("2030", "2040", "2050")
        for scenario in common.SCENARIOS
    ]
    tick_labels = [common.LABELS[scenario] for _year in ("2030", "2040", "2050") for scenario in common.SCENARIOS]
    pivot = (
        combined.pivot_table(index="column", columns="tech", values="eur", aggfunc="sum")
        .reindex(order)
        .fillna(0.0)
        / 1e9
    )
    # Drop tiny technology groups so the legend stays readable.
    pivot = pivot.loc[:, pivot.sum() > 1.0]

    fig, axes = plt.subplots(
        nrows=1, ncols=2, figsize=(16, 8), gridspec_kw={"width_ratios": [0.35, 1]}
    )
    total_series = pd.Series(totals) / 1e12
    total_series.plot(
        kind="bar",
        ax=axes[0],
        color=[common.SCENARIO_COLORS[s] for s in common.SCENARIOS],
        legend=False,
    )
    axes[0].set_ylabel("Period investment [trillion EUR]", fontsize=12)
    axes[0].tick_params(axis="both", labelsize=11)
    axes[0].grid(True, axis="y", linestyle="--", linewidth=0.3)
    for bar in axes[0].patches:
        height = bar.get_height()
        axes[0].text(
            bar.get_x() + bar.get_width() / 2,
            height,
            f"{height:.1f}",
            ha="center",
            va="bottom",
            fontsize=11,
        )

    ordered = [name for name in GROUP_COLORS if name in pivot.columns]
    pivot = pivot.reindex(columns=ordered)
    bar_colors = [GROUP_COLORS[tech] for tech in pivot.columns]
    pivot.plot(kind="bar", stacked=True, ax=axes[1], color=bar_colors, legend=False)
    axes[1].set_ylabel("Investment costs [billion EUR/year]", fontsize=12)
    axes[1].set_xticklabels(tick_labels, rotation=0, fontsize=10)
    axes[1].tick_params(axis="y", labelsize=11)
    axes[1].grid(True, axis="y", linestyle="--", linewidth=0.3)
    axes[1].set_xlabel("")
    for index, year in enumerate(("2030", "2040", "2050")):
        axes[1].text(
            index * 3 + 1,
            1.02,
            year,
            transform=axes[1].get_xaxis_transform(),
            ha="center",
            va="bottom",
            fontsize=13,
            fontweight="bold",
        )
    totals_by_bar = pivot.sum(axis=1)
    for x, total in enumerate(totals_by_bar):
        axes[1].text(x, total, f"{total:.0f}", ha="center", va="bottom", fontsize=8)

    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.62, -0.02),
        ncol=4,
        fontsize=9,
        frameon=False,
    )
    fig.tight_layout(rect=[0, 0.14, 1, 0.96])
    print(common.savefig(fig, "investment_costs"))


if __name__ == "__main__":
    main()
