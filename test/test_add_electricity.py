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
    nuclear_capacity_by_country,
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


def _powerplants_csv(path) -> str:
    plants = pd.DataFrame(
        {
            "Fueltype": ["Nuclear", "Nuclear", "Nuclear", "Nuclear", "Hard Coal"],
            "Country": ["BE", "CZ", "CZ", "FR", "CZ"],
            "Capacity": [1090.0, 2000.0, 2164.0, 1000.0, 400.0],
            "DateIn": [1985, 1985, 2002, 1980, 2000],
            "DateRetrofit": [np.nan, np.nan, np.nan, 2005, np.nan],
            "DateOut": [np.nan, 2037, np.nan, np.nan, 2040],
            "Name": ["Doel 4", "Dukovany", "Temelin", "retrofit", "coal"],
        }
    )
    plants.to_csv(path, index=False)
    return path.as_posix()


def test_nuclear_capacity_follows_decommissioning_date(tmp_path):
    """Missing DateOut is filled, then units retiring before the horizon drop.

    No retrofit: DateIn + 40. Retrofit: DateRetrofit + 20. A recorded DateOut
    is kept. A Belgian unit with no date is retired in 2035.
    """

    path = _powerplants_csv(tmp_path / "powerplants.csv")
    filled = pd.read_csv(path)
    online_2030 = nuclear_capacity_by_country(path, 2030)
    online_2040 = nuclear_capacity_by_country(path, 2040)
    online_2050 = nuclear_capacity_by_country(path, 2050)
    assert online_2030["BE"] == 1090
    assert "BE" not in online_2040.index
    assert "BE" not in online_2050.index
    # Dukovany keeps 2037; Temelin is 2002 + 40 = 2042.
    assert online_2030["CZ"] == 4164
    assert online_2040["CZ"] == 2164
    assert "CZ" not in online_2050.index
    # French unit: retrofit 2005 + 20 = 2025, retired before 2030.
    assert "FR" not in online_2030.index
    assert filled.loc[filled.Name == "coal", "DateOut"].iloc[0] == 2040


def test_apply_nuclear_capacity_replaces_powerplant_values(tmp_path):
    """Horizon filter overwrites generator MW and collapses duplicate units."""

    path = _powerplants_csv(tmp_path / "powerplants.csv")

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

    apply_nuclear_capacity(n, path, 2030)
    nuclear = n.generators.query("carrier == 'nuclear'")
    assert set(nuclear.index) == {"BE nuclear", "CZ nuclear"}
    assert nuclear.loc["BE nuclear", "p_nom"] == 1090
    assert nuclear.loc["BE nuclear", "p_nom_min"] == 1090
    assert bool(nuclear.loc["BE nuclear", "p_nom_extendable"])
    assert nuclear.loc["CZ nuclear", "p_nom"] == 4164

    previous = n.copy()
    previous.generators["p_nom_opt"] = previous.generators["p_nom"]
    previous.generators.loc["BE nuclear", "p_nom_opt"] = 2500

    apply_nuclear_capacity(n, path, 2040, n_previous=previous)
    # Existing Belgian capacity is zero after 2035; 1410 MW is the new build.
    assert n.generators.loc["BE nuclear", "p_nom_min"] == 1410
    # Temelin (2042) is still online, Dukovany (2037) is not.
    assert n.generators.loc["CZ nuclear", "p_nom_min"] == 2164
    assert "CZ nuclear-2037" not in n.generators.index
