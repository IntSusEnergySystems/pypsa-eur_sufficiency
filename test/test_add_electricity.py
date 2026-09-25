# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT

"""Tests for selected helpers in scripts/add_electricity.py."""

import numpy as np
import pandas as pd
import pypsa
import xarray as xr

from scripts.add_electricity import (
    apply_nuclear_capacity,
    attach_conventional_generators,
    attach_load,
    load_and_aggregate_powerplants,
)


def test_attach_load(tmp_path):
    """Clustered demand is attached per bus with scaling applied."""

    times = pd.date_range("2000-01-01", periods=2, freq="h")
    buses = ["zone_1", "zone_2"]
    values = np.array([[1.0, 2.0], [3.0, 4.0]])

    data = xr.DataArray(
        values,
        coords={"time": times, "bus": buses},
        dims=["time", "bus"],
        name="electricity demand (MW)",
    )
    load_path = tmp_path / "electricity_demand.nc"
    data.to_netcdf(load_path)

    n = pypsa.Network()
    n.set_snapshots(times)
    n.add("Bus", buses)

    attach_load(n, load_path.as_posix(), scaling=2.0)

    assert sorted(n.loads.index) == buses
    assert sorted(n.loads_t.p_set.columns) == buses
    np.testing.assert_allclose(n.loads_t.p_set[buses].values, 2.0 * values)


def _nuclear_costs() -> pd.DataFrame:
    index = ["nuclear", "coal"]
    return pd.DataFrame(
        {
            "VOM": [1.0, 2.0],
            "FOM": [1.0, 2.0],
            "efficiency": [0.33, 0.4],
            "capital_cost": [100.0, 50.0],
            "marginal_cost": [10.0, 20.0],
            "fuel": [3.0, 8.0],
            "lifetime": [40.0, 40.0],
            "CO2 intensity": [0.0, 0.3],
        },
        index=index,
    )


def test_nuclear_aggregated_once_per_bus(tmp_path):
    """Dated and undated plants at one bus become a single generator."""

    plants = pd.DataFrame(
        {
            "Fueltype": ["Nuclear", "Nuclear", "Hard Coal"],
            "Technology": ["Steam Turbine"] * 3,
            "Capacity": [2000.0, 2164.0, 400.0],
            "DateIn": [1985, 2002, 2000],
            "DateOut": [2037, np.nan, 2040],
            "Efficiency": [0.33, 0.33, 0.4],
            "bus": ["CZ", "CZ", "CZ"],
            "Country": ["CZ", "CZ", "CZ"],
            "Name": ["Dukovany", "Temelin", "coal"],
        }
    )
    path = tmp_path / "powerplants.csv"
    plants.to_csv(path)

    ppl = load_and_aggregate_powerplants(path.as_posix(), _nuclear_costs())
    nuclear = ppl[ppl.carrier == "nuclear"]
    assert list(nuclear.index) == ["CZ nuclear"]
    assert nuclear.loc["CZ nuclear", "p_nom"] == 4164
    assert ppl.loc["CZ coal", "p_nom"] == 400


def test_apply_nuclear_capacity_replaces_powerplant_values(tmp_path):
    """Horizon table overwrites generator MW and collapses duplicate units."""

    table = tmp_path / "nuclear_capacity.csv"
    table.write_text(
        "# comment\ncountry,2030,2040,2050\nBE,2000,0,0\nCZ,4164,2164,2164\n"
    )

    n = pypsa.Network()
    n.set_snapshots(pd.date_range("2030-01-01", periods=1, freq="h"))
    n.add("Bus", ["BE", "CZ"], country=["BE", "CZ"])
    n.add(
        "Generator",
        ["BE nuclear", "CZ nuclear", "CZ nuclear-2037"],
        bus=["BE", "CZ", "CZ"],
        carrier="nuclear",
        p_nom=[4096, 2164, 2000],
        p_nom_min=[4096, 2164, 2000],
        p_nom_extendable=False,
        capital_cost=100,
    )

    apply_nuclear_capacity(n, table.as_posix(), 2030)
    nuclear = n.generators.query("carrier == 'nuclear'")
    assert set(nuclear.index) == {"BE nuclear", "CZ nuclear"}
    assert nuclear.loc["BE nuclear", "p_nom"] == 2000
    assert nuclear.loc["BE nuclear", "p_nom_min"] == 2000
    assert bool(nuclear.loc["BE nuclear", "p_nom_extendable"])
    assert nuclear.loc["CZ nuclear", "p_nom"] == 4164

    previous = n.copy()
    previous.generators["p_nom_opt"] = previous.generators["p_nom"]
    previous.generators.loc["BE nuclear", "p_nom_opt"] = 2500

    apply_nuclear_capacity(n, table.as_posix(), 2040, n_previous=previous)
    assert n.generators.loc["BE nuclear", "p_nom_min"] == 500
    assert n.generators.loc["CZ nuclear", "p_nom_min"] == 2164
    assert "CZ nuclear-2037" not in n.generators.index
