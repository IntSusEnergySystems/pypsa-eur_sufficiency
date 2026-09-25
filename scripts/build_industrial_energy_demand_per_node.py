# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""
Build industrial energy demand per model region.

Description
-------
This rule aggregates the energy demand of the industrial sectors per model region.
For each bus, the following carriers are considered:
- electricity
- coal
- coke
- solid biomass
- methane
- hydrogen
- low-temperature heat
- naphtha
- ammonia
- process emission
- process emission from feedstock

which can later be used as values for the industry load.
"""

import logging

import pandas as pd

from scripts._helpers import (
    configure_logging,
    is_reference_run,
    is_sufficiency_run,
    set_scenario_config,
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    if "snakemake" not in globals():
        from scripts._helpers import mock_snakemake

        snakemake = mock_snakemake(
            "build_industrial_energy_demand_per_node",
            horizon=2030,
        )
    configure_logging(snakemake)
    set_scenario_config(snakemake)

    # import ratios
    fn = snakemake.input.industry_sector_ratios
    sector_ratios = pd.read_csv(fn, header=[0, 1], index_col=0)

    # material demand per node and industry (Mton/a)
    fn = snakemake.input.industrial_production_per_node
    nodal_production = pd.read_csv(fn, index_col=0) / 1e3

    # energy demand today to get current electricity
    fn = snakemake.input.industrial_energy_demand_per_node_today
    nodal_today = pd.read_csv(fn, index_col=0)

    nodal_sector_ratios = pd.concat(
        {node: sector_ratios[node[:2]] for node in nodal_production.index}, axis=1
    )

    nodal_production_stacked = nodal_production.stack()
    nodal_production_stacked.index.names = [None, None]

    # final energy consumption per node and industry (TWh/a)
    nodal_df = (
        (nodal_sector_ratios.multiply(nodal_production_stacked))
        .T.groupby(level=0)
        .sum()
    )

    rename_sectors = {
        "elec": "electricity",
        "biomass": "solid biomass",
        "heat": "low-temperature heat",
    }
    nodal_df.rename(columns=rename_sectors, inplace=True)

    nodal_df["current electricity"] = nodal_today["electricity"]

    nodal_df.index.name = "TWh/a (MtCO2/a)"

    config = snakemake.config
    if is_sufficiency_run(config) and dict(snakemake.input).get("clever_industry"):
        clever_industry = pd.read_csv(snakemake.input.clever_industry, index_col=0)
        for country in config["countries"]:
            if country not in clever_industry.index:
                continue
            country_energy = nodal_df[nodal_df.index.str.startswith(country)]
            if country_energy.empty:
                continue
            # CLEVER values are national totals. Split them by the industry
            # already allocated to each node so a country with several buses
            # is not given the full national demand on every bus.
            weights = country_energy["electricity"].clip(lower=0)
            if float(weights.sum()) <= 0:
                weights = pd.Series(1.0, index=country_energy.index)
            share = weights / weights.sum()
            src = clever_industry.loc[country]
            totals = {
                "ammonia": src[
                    "Total Final Energy Consumption of the ammonia industry"
                ],
                "electricity": src[
                    "Total Final electricity consumption in industry"
                ],
                "coal": src[
                    "Total Final energy consumption from solid fossil fuels (coal ...) in industry"
                ],
                "solid biomass": src[
                    "Total Final energy consumption from solid biomass in industry"
                ],
                "methane": src[
                    "Total Final energy consumption from gas grid / gas consumed locally in industry"
                ],
                "low-temperature heat": src[
                    "Total Final heat consumption in industry"
                ],
                "hydrogen": src["Total Final hydrogen consumption in industry"]
                + src[
                    "Non-energy consumption of hydrogen for the feedstock production"
                ],
                "naphtha": src[
                    "Non-energy consumption of oil for the feedstock production"
                ]
                + src["Total Final oil consumption in industry"],
            }
            for column, total in totals.items():
                nodal_df.loc[country_energy.index, column] = share * float(total)
    if is_reference_run(config) and "BE0 0" in nodal_df.index:
        nodal_df.loc["BE0 0", "naphtha"] = 84.4

    fn = snakemake.output.industrial_energy_demand_per_node
    nodal_df.to_csv(fn, float_format="%.2f")
