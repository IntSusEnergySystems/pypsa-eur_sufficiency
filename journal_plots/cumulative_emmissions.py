#!/usr/bin/env python3
"""Cumulative CO2 by sector for ref, suff and suff-nocdr.

Annual flows come from the atmospheric ``co2`` bus. Each solved year stands
for a ten-year period, and the area chart is the running sum of those
periods through 2050.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

import common

SECTORS = {
    "Maritime bunkers": ["shipping oil", "shipping methanol"],
    "Agriculture": ["agriculture machinery oil"],
    "Transport": ["land transport oil"],
    "Residential and tertiary sectors": [
        "rural gas boiler",
        "rural oil boiler",
        "urban decentral gas boiler",
        "urban decentral oil boiler",
        "urban central gas boiler",
    ],
    "Heat and power production": [
        "CCGT",
        "OCGT",
        "coal",
        "lignite",
        "urban central gas CHP",
        "urban central gas CHP CC",
        "waste CHP",
        "waste CHP CC",
    ],
    "Aviation bunkers": ["kerosene for aviation"],
    "Industry": [
        "gas for industry",
        "gas for industry CC",
        "coal for industry",
        "process emissions",
        "process emissions CC",
        "HVC to air",
        "naphtha for industry",
        "SMR",
        "SMR CC",
    ],
    "Biogas": ["biogas to gas", "biogas to gas CC"],
    "Biomass": [
        "biomass to liquid",
        "biomass to liquid CC",
        "BioSNG",
        "BioSNG CC",
        "solid biomass for industry",
        "solid biomass for industry CC",
    ],
    "DACCS": ["DAC"],
    "Land use and forestry": [],
}

COLORS = {
    "Maritime bunkers": "#f18959",
    "Agriculture": "#008556",
    "Transport": "#a26643",
    "Residential and tertiary sectors": "#d60a51",
    "Heat and power production": "#75519c",
    "Aviation bunkers": "#ff4d00",
    "Industry": "#feda47",
    "Biogas": "#8a9a4a",
    "Biomass": "green",
    "DACCS": "#b1d1fc",
    "Land use and forestry": "#befdb7",
}

BAR_SECTORS = list(SECTORS)


def lulucf_emissions_gt(year: int) -> float:
    """Annual land-use CO2 in Gt from the CLEVER AFOLU file for that year.

    The same series is used for every scenario, including reference. Sources
    are set to zero and sinks are kept, so the series is negative and reduces
    cumulative CO2. CLEVER values are megatonnes.
    """
    clever = pd.read_csv(common.ROOT / "data" / f"clever_AFOLUB_{year}.csv", index_col=0)
    countries = pd.read_csv(common.ROOT / "resources" / "ref" / "co2_totals.csv", index_col=0).index
    lulucf = clever.reindex(countries)["Total CO2 emissions from the LULUCF sector"]
    return float(lulucf.fillna(0).clip(upper=0).sum()) * 0.001


def historic_2020_gt(scenario: str) -> pd.Series:
    """EU27 UNFCCC CO2 in 2020, from the JRC-IDEES comparison workbook.

    Values are kilotonnes in that sheet. Biogas, biomass and DACCS are not
    reported separately in the inventory. Land use comes from the same
    LULUCF sink used in the CO2 budget.
    """
    path = (
        common.ROOT
        / "data/jrc_idees/archive/2024-05-20/EU27/JRC-IDEES-2021_EmissionsComparison_UNFCCC.xlsx"
    )
    sheet = pd.read_excel(path, sheet_name="EU27", header=None)
    years = [int(float(value)) for value in sheet.iloc[0, 1:]]
    column = 1 + years.index(2020)

    def kt(row: int) -> float:
        return float(sheet.iloc[row, column])

    values = {
        "Maritime bunkers": kt(21) + kt(46),
        "Agriculture": kt(26) + kt(41),
        "Transport": kt(19) + kt(20) + kt(22),
        "Residential and tertiary sectors": kt(24) + kt(25),
        "Heat and power production": kt(6),
        "Aviation bunkers": kt(18) + kt(45),
        "Industry": kt(7) + kt(8) + kt(9) + kt(30) + kt(32) + kt(42),
        "Biogas": 0.0,
        "Biomass": 0.0,
        "DACCS": 0.0,
        "Land use and forestry": 0.0,
    }
    series = pd.Series(values).reindex(list(SECTORS)).fillna(0.0) / 1e6
    series["Land use and forestry"] = lulucf_emissions_gt(2020)
    return series


def annual_gt(scenario: str) -> pd.DataFrame:
    balance = common.read_csv(scenario, "energy_balance")
    co2 = balance.loc[balance["bus_carrier"] == "co2"]
    rows = {}
    for sector, carriers in SECTORS.items():
        if not carriers:
            rows[sector] = pd.Series(0.0, index=[str(year) for year in common.HORIZONS])
            continue
        selected = co2.loc[co2["carrier"].isin(carriers), [str(year) for year in common.HORIZONS]]
        rows[sector] = selected.sum()
    frame = pd.DataFrame(rows)
    frame.index = frame.index.astype(int)
    frame = frame.reindex(columns=list(SECTORS)) / 1e9
    frame["Land use and forestry"] = [lulucf_emissions_gt(year) for year in frame.index]
    return frame


def cumulative_gt(annual: pd.DataFrame, scenario: str) -> pd.DataFrame:
    """Cumulative CO2 from 2020, interpolating the solved years.

    2020 is the historical inventory. Later years are the solved energy
    balance. The path between snapshots is linear, and each calendar year
    is added once.
    """
    frame = annual.copy()
    frame.loc[2020] = historic_2020_gt(scenario)
    frame = frame.sort_index()
    yearly = frame.reindex(range(2020, 2051)).interpolate(method="index")
    return yearly.cumsum()


def main() -> None:
    series = {
        scenario: cumulative_gt(annual_gt(scenario), scenario) for scenario in common.SCENARIOS
    }
    area_high = max(frame.clip(lower=0).sum(axis=1).max() for frame in series.values())
    area_low = min(frame.clip(upper=0).sum(axis=1).min() for frame in series.values())
    area_pad = 0.08 * max(abs(area_high), abs(area_low), 1.0)
    bar_values = [frame.loc[2050, BAR_SECTORS] for frame in series.values()]
    bar_high = max(values.max() for values in bar_values)
    bar_low = min(values.min() for values in bar_values)
    bar_pad = 0.18 * max(abs(bar_high), abs(bar_low), 1.0)

    fig, axes = plt.subplots(
        len(common.SCENARIOS),
        2,
        figsize=(18, 16),
        gridspec_kw={"width_ratios": [1.6, 1]},
    )
    for row, scenario in enumerate(common.SCENARIOS):
        cumulative = series[scenario]
        colors = [COLORS[name] for name in cumulative.columns]
        cumulative.plot(kind="area", stacked=True, ax=axes[row, 0], color=colors, legend=False, alpha=0.7)
        total = cumulative.sum(axis=1)
        axes[row, 0].plot(total.index, total.values, color="black", linewidth=2.0, label="Total")
        axes[row, 0].axhline(0, color="black", linewidth=0.6)
        axes[row, 0].set_ylabel("Cumulative CO2 [Gt]", fontsize=14)
        axes[row, 0].set_title(f"{common.LABELS[scenario]}", fontsize=15, loc="left")
        axes[row, 0].set_xticks([2020, 2030, 2040, 2050])
        axes[row, 0].set_ylim(area_low - area_pad, area_high + area_pad)
        axes[row, 0].grid(True, axis="y", linestyle="--", linewidth=0.3)
        axes[row, 0].tick_params(labelsize=16)

        values = cumulative.loc[2050, BAR_SECTORS]
        bar_colors = [COLORS[name] for name in values.index]
        bars = axes[row, 1].bar(
            range(len(values)),
            values.values,
            color=bar_colors,
            alpha=0.9,
            width=0.55,
            edgecolor="0.3",
            linewidth=0.4,
        )
        axes[row, 1].set_xticks(range(len(values)))
        axes[row, 1].set_xticklabels([])
        axes[row, 1].set_xlim(-0.7, len(values) - 0.3)
        axes[row, 1].set_ylim(bar_low - bar_pad, bar_high + bar_pad)
        axes[row, 1].axhline(0, color="black", linewidth=0.6)
        axes[row, 1].grid(True, axis="y", linestyle="--", linewidth=0.3)
        axes[row, 1].set_title("Cumulative to 2050", fontsize=15)
        axes[row, 1].tick_params(labelsize=16)
        for bar in bars:
            height = bar.get_height()
            axes[row, 1].text(
                bar.get_x() + bar.get_width() / 2,
                height,
                f"{height:.2f}",
                ha="center",
                va="bottom" if height >= 0 else "top",
                fontsize=11,
            )

    handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[name]) for name in SECTORS]
    handles.append(Line2D([0], [0], color="black", linewidth=2))
    fig.legend(handles, list(SECTORS) + ["Total"], loc="lower center", ncol=4, frameon=False, fontsize=12)
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    print(common.savefig(fig, "cumulative_emissions"))


if __name__ == "__main__":
    main()
