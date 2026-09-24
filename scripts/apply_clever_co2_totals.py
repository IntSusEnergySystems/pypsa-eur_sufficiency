# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""Overlay CLEVER LULUCF values onto CO2 totals for one horizon."""

from pathlib import Path

import pandas as pd

from scripts._helpers import configure_logging, set_scenario_config

if __name__ == "__main__":
    if "snakemake" not in globals():
        from scripts._helpers import mock_snakemake

        snakemake = mock_snakemake("apply_clever_co2_totals", horizon=2030)

    configure_logging(snakemake)
    set_scenario_config(snakemake)

    co2 = pd.read_csv(snakemake.input.co2_totals, index_col=0)
    clever_path = dict(snakemake.input).get("clever_afolub")
    if clever_path:
        clever = pd.read_csv(clever_path, index_col=0)
        for country in snakemake.params.countries:
            if country in co2.index and country in clever.index:
                co2.loc[country, "LULUCF"] = clever.loc[
                    country, "Total CO2 emissions from the LULUCF sector"
                ]
    co2.fillna(0, inplace=True)
    Path(snakemake.output.co2_totals).parent.mkdir(parents=True, exist_ok=True)
    co2.to_csv(snakemake.output.co2_totals)
