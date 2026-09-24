# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""Overlay CLEVER scenario demands onto historical energy totals for one horizon."""

from pathlib import Path

import pandas as pd

from scripts._helpers import (
    configure_logging,
    is_sufficiency_run,
    set_scenario_config,
)

CLEVER_COLUMNS = {
    "clever_transport": {
        "total road": "Total_Road",
        "electricity road": "Electricity_Road",
        "total passenger cars": "Total final energy consumption in passenger road mobility",
        "electricity passenger cars": "Final electricity consumption for passenger road mobility",
        "total rail": "Total_rail",
        "electricity rail": "Electricity_rail",
        "total rail passenger": "Total final energy consumption in rail passenger transport",
        "electricity rail passenger": "Final electricity consumption in rail passenger transport",
        "total rail freight": "Total final energy consumption in rail freight transport",
        "electricity rail freight": "Final electricity consumption in rail freight transport",
        "total aviation passenger": "Total final energy consumption for air travel",
        "total international aviation": "Total final energy consumption for air travel",
        "total domestic navigation": "Final energy consumption from liquid fuels in national water freight transport",
        "total international navigation": "Final energy consumption from liquid fuels in international water freight transport",
    },
    "clever_residential": {
        "total residential space": "Total final energy consumption for space heating in the residential sector",
        "total residential water": "Total final energy consumption for domestic hot water",
        "total residential cooking": "Total final energy consumption for domestic cooking",
        "electricity residential cooking": "Final electricity consumption for domestic cooking",
        "total residential": "Total final energy consumption in the residential sector",
        "electricity residential": "Final electricity consumption in the residential sector",
        "distributed heat residential": "Final energy consumption from heating networks in the residential sector",
        "thermal uses residential": "Thermal_uses_residential",
    },
    "clever_tertiary": {
        "total services space": "Total final energy consumption for space heating in the tertiary sector (with climatic corrections) ",
        "total services water": "Total final energy consumption for hot water in the tertiary sector",
        "total services cooking": "Total Final energy consumption for cooking in the tertiary sector",
        "electricity services cooking": "Final electricity consumption for cooking in the tertiary sector",
        "total services": "Total final energy consumption in the tertiary sector",
        "electricity services": "Final electricity consumption in the tertiary sector",
        "distributed heat services": "Final energy consumption from heating networks in the tertiary sector",
        "thermal uses services": "Thermal_uses_tertiary",
    },
    "clever_agriculture": {
        "total agriculture": "Total Final energy consumption in agriculture",
        "total agriculture electricity": "Final electricity consumption in agriculture",
        "total agriculture machinery": "Final oil consumption in agriculture",
        "total agriculture heat": "Total_agriculture_heat",
    },
}


if __name__ == "__main__":
    if "snakemake" not in globals():
        from scripts._helpers import mock_snakemake

        snakemake = mock_snakemake("apply_clever_energy_totals", horizon=2030)

    configure_logging(snakemake)
    set_scenario_config(snakemake)

    energy = pd.read_csv(snakemake.input.energy_totals, index_col=[0, 1])
    year = int(snakemake.params.energy_totals_year)
    countries = snakemake.params.countries

    if is_sufficiency_run(snakemake.config):
        clever = {
            key: pd.read_csv(path, index_col=0)
            for key, path in dict(snakemake.input).items()
            if key.startswith("clever_") and path
        }
        for country in countries:
            idx = (country, year)
            if idx not in energy.index:
                continue
            if "clever_transport" in clever:
                energy.loc[idx, "total domestic aviation"] = 0.0
            for source, mapping in CLEVER_COLUMNS.items():
                if source not in clever:
                    continue
                row = clever[source].loc[country]
                for dest, src in mapping.items():
                    if dest in energy.columns and src in row.index:
                        energy.loc[idx, dest] = row[src]

    energy.fillna(0, inplace=True)
    Path(snakemake.output.energy_totals).parent.mkdir(parents=True, exist_ok=True)
    energy.to_csv(snakemake.output.energy_totals)
