#!/usr/bin/env python3
"""Annual and period-average investment costs for the three scenarios."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import pandas as pd

import common

# Copies of scripts/_helpers.rename_techs and
# scripts/plot_power_network.rename_techs_tyndp. The journal scripts run on
# a Python that cannot import the model package.
def rename_techs(label: str) -> str:
    prefix_to_remove = [
        "residential ",
        "services ",
        "urban ",
        "rural ",
        "central ",
        "decentral ",
    ]
    rename_if_contains = [
        "CHP",
        "gas boiler",
        "biogas",
        "solar thermal",
        "air heat pump",
        "ground heat pump",
        "resistive heater",
        "Fischer-Tropsch",
    ]
    rename_if_contains_dict = {
        "water tanks": "hot water storage",
        "retrofitting": "building retrofitting",
        "battery": "battery storage",
        "H2 for industry": "H2 for industry",
        "land transport fuel cell": "land transport fuel cell",
        "land transport oil": "land transport oil",
        "oil shipping": "shipping oil",
    }
    rename = {
        "solar": "solar PV",
        "Sabatier": "methanation",
        "offwind": "offshore wind",
        "offwind-ac": "offshore wind (AC)",
        "offwind-dc": "offshore wind (DC)",
        "offwind-float": "offshore wind (Float)",
        "onwind": "onshore wind",
        "ror": "hydroelectricity",
        "hydro": "hydroelectricity",
        "PHS": "hydroelectricity",
        "NH3": "ammonia",
        "co2 Store": "DAC",
        "co2 stored": "CO2 sequestration",
        "AC": "transmission lines",
        "DC": "transmission lines",
        "B2B": "transmission lines",
    }
    for ptr in prefix_to_remove:
        if label[: len(ptr)] == ptr:
            label = label[len(ptr) :]
    for rif in rename_if_contains:
        if rif in label:
            label = rif
    for old, new in rename_if_contains_dict.items():
        if old in label:
            label = new
    for old, new in rename.items():
        if old == label:
            label = new
    return label


def rename_techs_tyndp(tech):
    tech = rename_techs(tech)
    if "heat pump" in tech or "resistive heater" in tech:
        return "power-to-heat"
    elif tech in ["H2 Electrolysis", "methanation", "H2 liquefaction"]:
        return "power-to-gas"
    elif tech in ["coal", "lignite"]:
        return "coal"
    elif tech == "H2":
        return "H2 storage"
    elif tech in ["NH3", "Haber-Bosch", "ammonia cracker", "ammonia store"]:
        return "ammonia"
    elif tech in ["OCGT", "CHP", "H2 Fuel Cell","H2 turbine","CCGT"]:
        return "gas-to-power/heat"
    elif tech in ["oil boiler", "gas", "gas boiler", "biomass boiler"]:
        return "boiler"
    elif tech in ["Fischer-Tropsch", "methanolisation"]:
        return "power-to-liquid"
    elif tech in ["water pits"]:
        return "thermal energy storage"
    elif tech in ["H2 pipeline", "H2 pipeline retrofitted", "H2 Store", "SMR"]:
        return "H2 infrastructure"
    elif tech in ["biogas", "BioSNG", "BioSNG CC","solid biomass transport","biomass to liquid","biomass to liquid CC"]:
        return "bio-fuels"
    elif "offshore wind" in tech:
        return "offshore wind"
    elif tech in ["sequestration", "process emissions CC", "solid biomass for industry CC", "gas for industry CC",
                  "DAC","CO2 pipeline"]:
        return "CCS"
    else:
        return tech


# Applied after the TYNDP names. Keys that the TYNDP step already rewrites
# are listed under the rewritten name as well.
REPLACEMENT = {
    "solar PV": "solar PV",
    "solar rooftop": "solar PV",
    "solar-hsat": "solar PV",
    "onshore wind": "wind",
    "offshore wind": "wind",
    "transmission lines": "electricity grid",
    "electricity distribution grid": "electricity grid",
    "battery storage": "electricity grid",
    "ammonia": "power-to-liquid",
}

# Group labels that are not themselves keys in plotting.default.yaml.
COLOR_KEYS = {
    "wind": "offshore wind",
    "electricity grid": "electricity",
    "boiler": "CCGT",
    "H2 infrastructure": "SMR",
    "bio-fuels": "solid biomass transport",
    "hydroelectricity": "battery storage",
    "thermal energy storage": "DAC",
    "power-to-liquid": "ammonia"
}


def color_for(name: str, colors: dict) -> str:
    key = COLOR_KEYS.get(name, name)
    if key in colors:
        return colors[key]
    folded = {label.lower(): value for label, value in colors.items()}
    return folded.get(key.lower(), colors.get("other", "#000000"))


def group_carrier(carrier: str) -> str:
    renamed = rename_techs_tyndp(str(carrier))
    return REPLACEMENT.get(renamed, renamed)


def capital_by_tech(scenario: str) -> pd.DataFrame:
    costs = common.read_csv(scenario, "costs")
    capital = costs.loc[costs["cost"] == "capital", ["carrier", "2030", "2040", "2050"]].copy()
    capital["tech"] = capital["carrier"].map(group_carrier)
    return capital.groupby("tech", as_index=False)[["2030", "2040", "2050"]].sum()


def main() -> None:
    annual = []
    totals = {}
    for scenario in common.SCENARIOS:
        table = capital_by_tech(scenario)
        # Annualised capital cost held over 2025–2050 (25 years). 2030 covers
        # the five years from 2025; 2040 and 2050 each cover the following decade.
        by_year = table.set_index("tech")[["2030", "2040", "2050"]].sum()
        period = by_year["2030"] * 5 + by_year["2040"] * 10 + by_year["2050"] * 10
        totals[common.LABELS[scenario]] = float(period)
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
        nrows=1, ncols=2, figsize=(16, 12), gridspec_kw={"width_ratios": [0.35, 1]}
    )
    # Default pandas bar width is 0.5, so the gap between bars is 0.5.
    # A 25% smaller gap is 0.375, which leaves a bar width of 0.625.
    bar_width = 0.625
    total_series = pd.Series(totals) / 1e12
    total_series.plot(
        kind="bar",
        ax=axes[0],
        color="black",
        width=bar_width,
        legend=False,
    )
    axes[0].set_ylabel("Cumulative investments [trillion EUR]", fontsize=12)
    axes[0].tick_params(axis="both", labelsize=13)
    axes[0].grid(True, axis="y", linestyle="--", linewidth=0.3)
    for bar in axes[0].patches:
        height = bar.get_height()
        axes[0].text(
            bar.get_x() + bar.get_width() / 2,
            height,
            f"{height:.1f}",
            ha="center",
            va="bottom",
            fontsize=13,
        )

    colors = common.plotting_config()["plotting"]["tech_colors"]
    preferred = [
        "onshore wind",
        "offshore wind",
        "solar PV",
        "solar thermal",
        "solar rooftop",
        "nuclear",
        "hydro",
        "power-to-heat",
        "gas-to-power/heat",
        "hydrogen techs/storage",
        "power-to-gas",
        "power-to-liquid",
        "biomass techs",
        "ammonia techs",
        "battery storage",
        "transmission lines",
        "electricity distribution grid",
        "CCS",
        "DAC",
        "thermal storage",
        "gas pipeline/storage",
        "oil techs/storage",
    ]
    ordered = [name for name in preferred if name in pivot.columns]
    ordered += [name for name in pivot.columns if name not in ordered]
    pivot = pivot.reindex(columns=ordered)
    bar_colors = [color_for(tech, colors) for tech in pivot.columns]
    pivot.plot(kind="bar", stacked=True, ax=axes[1], color=bar_colors, width=bar_width, legend=False)
    axes[1].set_ylabel("Investment costs [billion EUR/year]", fontsize=12)
    axes[1].set_xticklabels(tick_labels, rotation=90, fontsize=14)
    axes[1].tick_params(axis="y", labelsize=11)
    axes[1].grid(True, axis="y", linestyle="--", linewidth=0.3)
    axes[1].set_xlabel("")
    for boundary in (2.5, 5.5):
        axes[1].axvline(boundary, color="black", linestyle=":", linewidth=1.0, zorder=3)
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
        axes[1].text(x, total, f"{total:.0f}", ha="center", va="bottom", fontsize=12)

    handles, labels = axes[1].get_legend_handles_labels()
    fig.tight_layout(rect=[0, 0.3, 1, 0.96])
    axes[1].legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.0, -0.3, 1.0, 0.12),
        bbox_transform=axes[1].transAxes,
        mode="expand",
        ncol=4,
        fontsize=13,
        frameon=False,
        borderaxespad=0,
    )
    print(common.savefig(fig, "investment_costs"))


if __name__ == "__main__":
    main()
