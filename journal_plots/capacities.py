#!/usr/bin/env python3
"""2050 installed capacities for ref, suff and suff-nocdr."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import pandas as pd

import common

GROUPS = [
    {
        "title": "Capacity for VRE technologies [GW]",
        "scale": 1e3,
        "techs": {
            "solar": ["solar", "solar rooftop", "solar-hsat"],
            "onshore wind": ["onwind"],
            "offshore wind": ["offwind-ac", "offwind-dc", "offwind-float"],
        },
    },
    {
        "title": "Capacity for dispatchable technologies [GW]",
        "scale": 1e3,
        "techs": {
            "nuclear": ["nuclear"],
            "CCGT": ["CCGT"],
            "hydroelectricity": ["hydro", "ror"],
        },
    },
    {
        "title": "Capacity for conversion technologies [GW]",
        "scale": 1e3,
        "techs": {
            "power-to-gas": ["H2 Electrolysis", "Sabatier", "methanolisation"],
            "power-to-heat": [
                "rural air heat pump",
                "rural ground heat pump",
                "urban central air heat pump",
                "urban decentral air heat pump",
                "rural resistive heater",
            ],
            "power-to-liquid": ["Fischer-Tropsch", "biomass to liquid", "biomass to liquid CC"],
        },
    },
    {
        "title": "Capacity for grid infrastructure [GW]",
        "scale": 1e3,
        "techs": {
            "transmission lines": ["AC", "DC"],
            "H2 pipeline": ["H2 pipeline", "H2 pipeline retrofitted"],
            "gas pipeline": ["gas pipeline", "gas pipeline new"],
        },
    },
    {
        "title": "Capacity for storage technologies [GWh]",
        "scale": 1e3,
        "techs": {
            "H2 Store": ["H2 Store"],
            "Grid-scale battery": ["battery"],
            "home battery": ["home battery"],
        },
    },
    {
        "title": "Carbon management nameplate capacity [GW]",
        "scale": 1e3,
        "techs": {
            # BECCS is capture on solid biomass that is only extendable when
            # sequestration is allowed. suff-nocdr sets those to zero.
            # Biogas upgrading with capture stays on: its CO2 goes to
            # co2 stored and is used by Fischer-Tropsch, with no sequestration.
            "DAC": ["DAC"],
            "BECCS": [
                "biomass to liquid CC",
                "BioSNG CC",
                "urban central solid biomass CHP CC",
                "solid biomass for industry CC",
            ],
            "Gas CC": ["SMR CC", "gas for industry CC"],
        },
    },
]


def _sum_carriers(frame: pd.DataFrame, carriers: list[str]) -> float:
    selected = frame.loc[frame["carrier"].isin(carriers), "2050"]
    if selected.empty:
        return 0.0
    return float(selected.sum())


def scenario_table(scenario: str) -> pd.DataFrame:
    caps = common.read_csv(scenario, "capacities")
    rows = []
    for group in GROUPS:
        for label, carriers in group["techs"].items():
            rows.append(
                {
                    "group": group["title"],
                    "tech": label,
                    "value": _sum_carriers(caps, carriers) / group["scale"],
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    colors = common.tech_colors()
    tables = {scenario: scenario_table(scenario) for scenario in common.SCENARIOS}
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    for ax, group in zip(axes.flatten(), GROUPS):
        pieces = []
        for scenario in common.SCENARIOS:
            part = tables[scenario]
            part = part.loc[part["group"] == group["title"]].set_index("tech")["value"]
            part.name = common.LABELS[scenario]
            pieces.append(part)
        data = pd.concat(pieces, axis=1).fillna(0.0)
        data.T.plot(
            kind="bar",
            ax=ax,
            color=[colors.get(tech, "grey") for tech in data.index],
            width=0.8,
        )
        ax.set_ylabel(group["title"], fontsize=11)
        ax.set_xlabel("")
        ax.tick_params(axis="x", labelrotation=0, labelsize=10)
        ax.tick_params(axis="y", labelsize=10)
        ax.grid(True, axis="y", linestyle="--", linewidth=0.3)
        legend = ax.get_legend()
        legend.set_title(None)
        plt.setp(legend.get_texts(), fontsize=9)
    fig.tight_layout()
    print(common.savefig(fig, "capacities"))


if __name__ == "__main__":
    main()
