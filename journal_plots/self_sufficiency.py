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
OIL_DOMESTIC = ["Fischer-Tropsch", "biomass to liquid", "biomass to liquid CC"]
OIL_SUPPLY = OIL_DOMESTIC + ["oil refining"]


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


def _system_share(scenario: str, bus: str, domestic: list[str], supply: list[str]) -> pd.Series:
    balance = common.read_csv(scenario, "energy_balance")
    flows = balance.loc[balance["bus_carrier"] == bus]
    values = {}
    for year in common.HORIZONS:
        column = str(year)
        grouped = flows.groupby("carrier")[column].sum()
        made = float(grouped.reindex(domestic, fill_value=0.0).clip(lower=0).sum())
        total = float(grouped.reindex(supply, fill_value=0.0).clip(lower=0).sum())
        values[year] = 100.0 * made / total if total else 0.0
    return pd.Series(values, name=common.LABELS[scenario])


def system_share(table: pd.DataFrame, scenario: str) -> pd.Series:
    """Domestic renewable gas as a share of gas supply."""
    return _system_share(scenario, "gas", DOMESTIC, SUPPLY)


def system_oil_share(scenario: str) -> pd.Series:
    """Domestic renewable liquids as a share of oil-product supply."""
    return _system_share(scenario, "oil", OIL_DOMESTIC, OIL_SUPPLY)


# Eurostat energy balances, 2020, TWh. Natural gas and crude oil.
# Switzerland is not in the Eurostat file.
_EUROSTAT = {
    "gas": "G3000",
    "oil": "O4100_TOT",
}


def _study_countries() -> list[str]:
    import yaml

    with open(common.ROOT / "config" / "study.yaml", encoding="utf-8") as handle:
        return list(yaml.safe_load(handle)["countries"])


_PRODUCTION_2020 = None


def production_2020_twh() -> dict[str, dict[str, float]]:
    """2020 production, imports and exports of gas and crude oil, in TWh.

    Summed over the study countries. Exports are kept so trade between
    those countries cancels when self-sufficiency is formed.
    """
    global _PRODUCTION_2020
    if _PRODUCTION_2020 is not None:
        return _PRODUCTION_2020
    countries = set(_study_countries())
    wanted = set(_EUROSTAT.values())
    parts = []
    path = common.ROOT / "resources" / "ref" / "eurostat_energy_balances.csv"
    for chunk in pd.read_csv(path, chunksize=400_000):
        part = chunk.loc[
            (chunk["year"] == 2020)
            & chunk["country"].isin(countries)
            & chunk["siec"].isin(wanted)
            & chunk["nrg_bal"].isin(["PPRD", "IMP", "EXP"])
        ]
        if len(part):
            parts.append(part)
    table = pd.concat(parts, ignore_index=True)
    totals = table.groupby(["siec", "nrg_bal"])["value"].sum()
    out = {}
    for fuel, code in _EUROSTAT.items():
        out[fuel] = {
            "production": float(totals.get((code, "PPRD"), 0.0)),
            "imports": float(totals.get((code, "IMP"), 0.0)),
            "exports": float(totals.get((code, "EXP"), 0.0)),
        }
    _PRODUCTION_2020 = out
    return out


def fossil_use_twh(scenario: str) -> dict[str, pd.Series]:
    """Fossil gas and crude oil entering the system, in TWh."""
    balance = common.read_csv(scenario, "energy_balance")
    specs = {
        "gas": ("gas", "gas"),
        "oil": ("oil primary", "oil primary"),
    }
    out = {}
    for fuel, (bus, carrier) in specs.items():
        flows = balance.loc[
            (balance["bus_carrier"] == bus) & (balance["carrier"] == carrier)
        ]
        values = {}
        for year in common.HORIZONS:
            column = str(year)
            values[year] = float(flows[column].clip(lower=0).sum()) / 1e6
        out[fuel] = pd.Series(values)
    return out


def fossil_self_sufficiency(scenario: str) -> dict[str, pd.Series]:
    """Self-sufficiency against gas and oil produced in the study countries now.

    2020 uses Eurostat: production / (production + imports - exports).
    2030, 2040 and 2050 keep that 2020 production and divide it by fossil
    use in the scenario. When production covers all of that use, the
    value is 100%.
    """
    history = production_2020_twh()
    use = fossil_use_twh(scenario)
    series = {}
    for fuel in ("gas", "oil"):
        produced = history[fuel]["production"]
        net_supply = produced + history[fuel]["imports"] - history[fuel]["exports"]
        values = {2020: min(100.0, 100.0 * produced / net_supply)}
        for year, consumed in use[fuel].items():
            if consumed <= produced:
                values[int(year)] = 100.0
            else:
                values[int(year)] = 100.0 * produced / consumed
        series[fuel] = pd.Series(values)
    return series


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
