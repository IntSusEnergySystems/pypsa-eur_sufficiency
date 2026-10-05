#!/usr/bin/env python3
"""2050 installed capacities for ref, suff and suff-nocdr.

Writes the original grouped bars plus a dot plot, a difference-from-Ref
plot, and a stacked system plot.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import pandas as pd

import common

GROUPS = [
    {
        "title": "Capacity for VRE technologies [GW]",
        "short": "VRE",
        "unit": "GW",
        "scale": 1e3,
        "techs": {
            "solar": ["solar", "solar rooftop", "solar-hsat"],
            "onshore wind": ["onwind"],
            "offshore wind": ["offwind-ac", "offwind-dc", "offwind-float"],
        },
    },
    {
        "title": "Capacity for dispatchable technologies [GW]",
        "short": "Dispatchable",
        "unit": "GW",
        "scale": 1e3,
        "techs": {
            "nuclear": ["nuclear"],
            "CCGT": ["CCGT"],
            "hydroelectricity": ["hydro", "ror"],
        },
    },
    {
        "title": "Capacity for conversion technologies [GW]",
        "short": "Conversion",
        "unit": "GW",
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
        "short": "Grid",
        "unit": "GW",
        "scale": 1e3,
        "techs": {
            "transmission lines": ["AC", "DC"],
            "H2 pipeline": ["H2 pipeline", "H2 pipeline retrofitted"],
            "gas pipeline": ["gas pipeline", "gas pipeline new"],
        },
    },
    {
        "title": "Capacity for storage technologies [GWh]",
        "short": "Storage",
        "unit": "GWh",
        "scale": 1e3,
        "techs": {
            "H2 Store": ["H2 Store"],
            "Grid-scale battery": ["battery"],
            "home battery": ["home battery"],
        },
    },
    {
        "title": "Carbon management nameplate capacity [GW]",
        "short": "Carbon management",
        "unit": "GW",
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


def captured_mt(scenario: str) -> pd.Series:
    """CO2 delivered to the stored-CO2 bus in 2050, in Mt/year."""
    balance = common.read_csv(scenario, "energy_balance")
    stored = balance.loc[balance["bus_carrier"] == "co2 stored"].groupby("carrier")["2050"].sum()
    group = next(item for item in GROUPS if item["short"] == "Carbon management")
    values = {}
    for label, carriers in group["techs"].items():
        tonnes = stored.reindex(carriers, fill_value=0.0).clip(lower=0).sum()
        values[label] = float(tonnes) / 1e6
    return pd.Series(values)


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


def capacity_frame(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One row per technology, one column per scenario, in group order."""
    base = tables[common.SCENARIOS[0]][["group", "tech", "value"]].rename(columns={"value": common.SCENARIOS[0]})
    frame = base
    for scenario in common.SCENARIOS[1:]:
        part = tables[scenario].set_index("tech")["value"].rename(scenario)
        frame = frame.join(part, on="tech")
    lookup = {group["title"]: group for group in GROUPS}
    frame["short"] = frame["group"].map(lambda title: lookup[title]["short"])
    frame["unit"] = frame["group"].map(lambda title: lookup[title]["unit"])
    return frame


def _tech_colors(techs) -> list[str]:
    colors = common.tech_colors()
    return [colors.get(tech, "grey") for tech in techs]


def plot_grouped(tables: dict[str, pd.DataFrame]) -> None:
    """Original six-panel grouped bars."""
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    for ax, group in zip(axes.flatten(), GROUPS):
        if group["short"] == "Carbon management":
            pieces = [captured_mt(scenario).rename(common.LABELS[scenario]) for scenario in common.SCENARIOS]
            ylabel = "Carbon management capacities [Mt/year]"
        else:
            pieces = []
            for scenario in common.SCENARIOS:
                part = tables[scenario]
                part = part.loc[part["group"] == group["title"]].set_index("tech")["value"]
                part.name = common.LABELS[scenario]
                pieces.append(part)
            ylabel = group["title"]
        data = pd.concat(pieces, axis=1).fillna(0.0)
        data.T.plot(kind="bar", ax=ax, color=_tech_colors(data.index), width=0.8)
        bottom, top = ax.get_ylim()
        visible = [float(tick) for tick in ax.get_yticks() if bottom - 1e-8 <= tick <= top + 1e-8]
        visible = sorted(visible)
        steps = max(len(visible) - 1, 1)
        new_top = visible[-1] * 1.25
        step = new_top / steps
        ax.set_ylim(bottom, new_top * 1.02)
        ax.set_yticks([index * step for index in range(steps + 1)])
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _pos: f"{value:g}"))
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_xlabel("")
        ax.tick_params(axis="x", labelrotation=0, labelsize=10)
        ax.tick_params(axis="y", labelsize=10)
        ax.grid(True, axis="y", linestyle="--", linewidth=0.3)
        legend = ax.get_legend()
        legend.set_title(None)
        plt.setp(legend.get_texts(), fontsize=13)
    fig.tight_layout()
    print(common.savefig(fig, "capacities"))


def _mark_groups(ax, labels: list[str], shorts: list[str]) -> None:
    """Draw a light line between technology groups."""
    for index in range(1, len(shorts)):
        if shorts[index] != shorts[index - 1]:
            ax.axhline(index - 0.5, color="0.85", linewidth=0.6, zorder=0)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_ylim(-0.5, len(labels) - 0.5)


def plot_dots(frame: pd.DataFrame) -> None:
    """One dot per scenario, technologies grouped on a shared scale per unit."""
    units = ["GW", "GWh"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 9), gridspec_kw={"width_ratios": [1.6, 1]})
    for ax, unit in zip(axes, units):
        part = frame.loc[frame["unit"] == unit].reset_index(drop=True)
        labels = [f"{row.short}: {row.tech}" for row in part.itertuples()]
        for position, row in part.iterrows():
            for scenario in common.SCENARIOS:
                ax.scatter(
                    row[scenario],
                    position,
                    s=140,
                    color=common.SCENARIO_COLORS[scenario],
                    zorder=3,
                )
        _mark_groups(ax, labels, part["short"].tolist())
        ax.set_xlabel(f"2050 capacity [{unit}]")
        ax.grid(True, axis="x", linestyle="--", linewidth=0.3)
        ax.invert_yaxis()
    handles = [
        plt.Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markersize=14,
            markerfacecolor=common.SCENARIO_COLORS[scenario],
            markeredgecolor=common.SCENARIO_COLORS[scenario],
            label=common.LABELS[scenario],
        )
        for scenario in common.SCENARIOS
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=16, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    print(common.savefig(fig, "capacities_dots"))


def plot_difference(frame: pd.DataFrame) -> None:
    """Suff and suff-nocdr minus Ref."""
    units = ["GW", "GWh"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 9), gridspec_kw={"width_ratios": [1.6, 1]})
    others = [scenario for scenario in common.SCENARIOS if scenario != "ref"]
    for ax, unit in zip(axes, units):
        part = frame.loc[frame["unit"] == unit].reset_index(drop=True)
        labels = [f"{row.short}: {row.tech}" for row in part.itertuples()]
        offset = 0.16
        for shift, scenario in zip((-offset, offset), others):
            delta = part[scenario] - part["ref"]
            ax.barh(
                [position + shift for position in range(len(part))],
                delta,
                height=0.3,
                color=common.SCENARIO_COLORS[scenario],
                label=f"{common.LABELS[scenario]} − Ref",
            )
        _mark_groups(ax, labels, part["short"].tolist())
        ax.axvline(0, color="0.3", linewidth=0.6)
        ax.set_xlabel(f"2050 capacity relative to Ref [{unit}]")
        ax.grid(True, axis="x", linestyle="--", linewidth=0.3)
        ax.invert_yaxis()
    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=common.SCENARIO_COLORS[scenario], edgecolor="none", label=f"{common.LABELS[scenario]} − Ref")
        for scenario in others
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False, fontsize=16, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    print(common.savefig(fig, "capacities_difference"))


def plot_stacked(frame: pd.DataFrame) -> None:
    """System mix: plants, grid, and storage as separate stacks."""
    blocks = [
        ("Plants and conversion", ["VRE", "Dispatchable", "Conversion", "Carbon management"], "GW"),
        ("Grid", ["Grid"], "GW"),
        ("Storage", ["Storage"], "GWh"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(15, 6))
    scenarios = [common.LABELS[scenario] for scenario in common.SCENARIOS]
    for ax, (title, shorts, unit) in zip(axes, blocks):
        part = frame.loc[frame["short"].isin(shorts)].set_index("tech")
        values = part[list(common.SCENARIOS)].T
        values.index = scenarios
        values.plot(kind="bar", stacked=True, ax=ax, color=_tech_colors(values.columns), width=0.72)
        ax.set_title(title, fontsize=13)
        ax.set_ylabel(f"2050 capacity [{unit}]")
        ax.set_xlabel("")
        ax.tick_params(axis="x", labelrotation=0)
        ax.grid(True, axis="y", linestyle="--", linewidth=0.3)
        ax.legend(frameon=False, fontsize=8, loc="upper right")
    fig.tight_layout()
    print(common.savefig(fig, "capacities_stacked"))


def main() -> None:
    tables = {scenario: scenario_table(scenario) for scenario in common.SCENARIOS}
    frame = capacity_frame(tables)
    plot_grouped(tables)
    plot_dots(frame)
    plot_difference(frame)
    plot_stacked(frame)


if __name__ == "__main__":
    main()
