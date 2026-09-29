#!/usr/bin/env python3
"""Final energy by sector for ref, suff and suff-nocdr.

Delivered energy is taken from the solved energy balance, using the carrier
on its own bus so conversion inputs are not counted twice.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch

import common

SECTORS = {
    "Transport": [
        "land transport oil",
        "land transport EV",
        "land transport fuel cell",
        "kerosene for aviation",
        "shipping oil",
        "shipping methanol",
        "agriculture machinery oil",
    ],
    "Industry": [
        "industry electricity",
        "gas for industry",
        "coal for industry",
        "naphtha for industry",
        "solid biomass for industry",
        "industry methanol",
    ],
    "Residential and tertiary": [
        "urban central heat",
        "urban decentral heat",
        "rural heat",
        "electricity",
    ],
}

CARRIER_COLORS = {
    "land transport oil": "#c9c9c9",
    "land transport EV": "#110d63",
    "land transport fuel cell": "#bf13a0",
    "kerosene for aviation": "#ff4d00",
    "shipping oil": "#f18959",
    "shipping methanol": "#468c8b",
    "agriculture machinery oil": "#008556",
    "industry electricity": "#110d63",
    "gas for industry": "#e05b09",
    "coal for industry": "#545454",
    "naphtha for industry": "#4f1745",
    "solid biomass for industry": "#baa741",
    "industry methanol": "#46caf0",
    "urban central heat": "#e8beac",
    "urban decentral heat": "#f3afa3",
    "rural heat": "#d60a51",
    "electricity": "#235ebc",
}


def delivered_twh(scenario: str) -> pd.DataFrame:
    balance = common.read_csv(scenario, "energy_balance")
    rows = []
    years = [str(year) for year in common.HORIZONS]
    for sector, carriers in SECTORS.items():
        selected = balance.loc[(balance["component"] == "Load") & balance["carrier"].isin(carriers)]
        if selected.empty:
            totals = pd.DataFrame(0.0, index=carriers, columns=years)
        else:
            totals = selected.groupby("carrier")[years].sum().abs() / 1e6
            totals = totals.reindex(carriers).fillna(0.0)
        for carrier in carriers:
            rows.append({"sector": sector, "carrier": carrier, **totals.loc[carrier].to_dict()})
    return pd.DataFrame(rows)


def main() -> None:
    tables = {scenario: delivered_twh(scenario) for scenario in common.SCENARIOS}
    fig, axes = plt.subplots(len(SECTORS), 1, figsize=(13, 12))
    years = [str(year) for year in common.HORIZONS]
    totals = []
    for sector, carriers in SECTORS.items():
        for year in years:
            for scenario in common.SCENARIOS:
                part = tables[scenario]
                part = part.loc[part["sector"] == sector, year]
                totals.append(float(part.sum()))
    xlim = max(totals) * 1.08

    for ax, (sector, carriers) in zip(axes, SECTORS.items()):
        y_pos = 0
        yticks = []
        ylabels = []
        for year in years:
            for scenario in common.SCENARIOS:
                part = tables[scenario]
                part = part.loc[part["sector"] == sector].set_index("carrier").reindex(carriers).fillna(0.0)
                left = 0.0
                for carrier in carriers:
                    value = float(part.loc[carrier, year])
                    ax.barh(y_pos, value, left=left, height=0.8, color=CARRIER_COLORS[carrier])
                    left += value
                yticks.append(y_pos)
                ylabels.append(f"{year} {common.LABELS[scenario]}")
                y_pos += 1
            y_pos += 0.4
        ax.set_yticks(yticks)
        ax.set_yticklabels(ylabels, fontsize=8)
        ax.set_xlim(0, xlim)
        ax.set_xlabel("Delivered energy [TWh]")
        ax.set_title(sector, loc="left", fontsize=12)
        ax.invert_yaxis()
        handles = [Patch(facecolor=CARRIER_COLORS[carrier], label=carrier) for carrier in carriers]
        ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8, frameon=False)

    fig.tight_layout(rect=[0, 0, 0.78, 1])
    print(common.savefig(fig, "final_energy_sectors"))


if __name__ == "__main__":
    main()
