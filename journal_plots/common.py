"""Shared paths and loaders for the journal figures.

Solved runs live in ``results/<scenario>/``. The third scenario in this
study is ``suff-nocdr`` (CLEVER demands, no CDR). Requests that say
``suff-npcdr`` refer to that run.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import xarray as xr
import yaml

ROOT = Path(__file__).resolve().parents[1]
PLOT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PLOT_DIR / "output"
CACHE_DIR = PLOT_DIR / ".cache"

SCENARIOS = ["ref", "suff", "suff-nocdr"]
HORIZONS = [2030, 2040, 2050]
LABELS = {
    "ref": "Ref",
    "suff": "Suff",
    "suff-nocdr": "suff-nocdr",
}
SCENARIO_COLORS = {
    "ref": "#4c4c4c",
    "suff": "#2ca02c",
    "suff-nocdr": "#1f77b4",
}

# Approximate 2023 GDP, billion EUR, carried over from the previous map script.
GDP_BEUR = {
    "AT": 520,
    "BE": 700,
    "BG": 95,
    "CH": 930,
    "CZ": 340,
    "DE": 4300,
    "DK": 400,
    "EE": 34,
    "ES": 1600,
    "FI": 290,
    "FR": 3300,
    "GB": 3100,
    "GR": 276,
    "HR": 70,
    "HU": 207,
    "IE": 522,
    "IT": 2300,
    "LT": 68,
    "LU": 92,
    "LV": 43,
    "NL": 936,
    "NO": 477,
    "PL": 774,
    "PT": 330,
    "RO": 340,
    "SE": 560,
    "SI": 62,
    "SK": 115,
}

VRE_GROUPS = {
    "solar": ("solar", "solar rooftop", "solar-hsat"),
    "onwind": ("onwind",),
    "offwind": ("offwind-ac", "offwind-dc", "offwind-float"),
}


def plotting_config() -> dict:
    path = ROOT / "config" / "plotting.default.yaml"
    with path.open() as handle:
        return yaml.safe_load(handle)


def tech_colors() -> dict:
    colors = dict(plotting_config()["plotting"]["tech_colors"])
    colors.update(
        {
            "Thermal Energy Storage": "#f3afa3",
            "Transmission lines": "green",
            "Grid-scale battery": "lightgreen",
            "home battery": "blue",
            "H2 pipeline": "slateblue",
            "gas pipeline": "grey",
            "BECCS": "#889717",
            "biogas CC": "#e51245",
            "Gas CC": "#f18959",
            "biomass techs": "#baa741",
            "process emissions CC": "#4f1745",
            "hydrogen techs/storage": "slateblue",
            "ammonia techs": "#46caf0",
            "gas pipeline/storage": "#4f1745",
            "thermal storage": "#f3afa3",
            "hydro": "#298c81",
            "oil techs/storage": "#c9c9c9",
            "gas-to-power/heat": "chocolate",
            "CCS": "#4f1745",
            "offshore wind": colors.get("offwind-ac", "#6895dd"),
            "onshore wind": colors.get("onwind", "#235ebc"),
            "solar PV": colors.get("solar", "#f9d002"),
        }
    )
    return colors


def csv_path(scenario: str, name: str) -> Path:
    return ROOT / "results" / scenario / "csvs" / f"{name}.csv"


def read_csv(scenario: str, name: str) -> pd.DataFrame:
    path = csv_path(scenario, name)
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def network_path(scenario: str, year: int) -> Path:
    return ROOT / "results" / scenario / "networks" / f"solved_{year}.nc"


def regions_path(scenario: str = "ref") -> Path:
    return ROOT / "resources" / scenario / "onshore_regions.geojson"


def population() -> pd.Series:
    pop = pd.read_csv(ROOT / "resources" / "ref" / "pop_layout.csv")
    # pop_layout stores thousands of people.
    return pop.groupby("ct")["total"].sum() * 1000


def savefig(fig: plt.Figure, name: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    png = OUTPUT_DIR / f"{name}.png"
    fig.savefig(png, dpi=150, bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    return png


def _country_vre_curtailment_twh(scenario: str, year: int) -> pd.DataFrame:
    """Curtailment by country and VRE group, in TWh.

    Snapshot weightings in these networks are 6 hours. Energy is
    ``(p_max_pu * p_nom_opt - p) * weight``.
    """
    path = network_path(scenario, year)
    with xr.open_dataset(path) as ds:
        carriers = pd.Series(ds["generators_carrier"].values, index=ds["generators_i"].values)
        buses = pd.Series(ds["generators_bus"].values, index=ds["generators_i"].values)
        countries = pd.Series(ds["buses_country"].values, index=ds["buses_i"].values)
        p_nom = pd.Series(ds["generators_p_nom_opt"].values, index=ds["generators_i"].values)
        weight = float(ds["snapshots_generators"].values[0])
        p = pd.DataFrame(ds["generators_t_p"].values, columns=list(ds["generators_t_p_i"].values))
        pu = pd.DataFrame(
            ds["generators_t_p_max_pu"].values,
            columns=list(ds["generators_t_p_max_pu_i"].values),
        )

    common = p.columns.intersection(pu.columns)
    rows = []
    for tech, names in VRE_GROUPS.items():
        gens = [g for g in common if carriers.get(g) in names]
        if not gens:
            continue
        available = pu[gens] * p_nom.reindex(gens).to_numpy()
        curtailed = (available - p[gens]).clip(lower=0).sum(axis=0) * weight / 1e6
        frame = curtailed.rename("twh").to_frame()
        frame["country"] = buses.reindex(frame.index).map(countries)
        frame["tech"] = tech
        rows.append(frame.groupby(["country", "tech"], as_index=False)["twh"].sum())
    if not rows:
        return pd.DataFrame(columns=["country", "tech", "twh"])
    out = pd.concat(rows, ignore_index=True)
    out["scenario"] = scenario
    out["year"] = year
    return out


def country_vre_curtailment(scenario: str, year: int) -> pd.DataFrame:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"curtailment_{scenario}_{year}.csv"
    if cache.exists():
        return pd.read_csv(cache)
    frame = _country_vre_curtailment_twh(scenario, year)
    frame.to_csv(cache, index=False)
    return frame


def _country_co2_tonnes(scenario: str, year: int) -> pd.Series:
    """Net CO2 injected onto the atmospheric CO2 bus, by plant country.

    The summary tables book every CO2 bus at ``EU``. This reads the link
    ports that connect to a ``co2`` bus and assigns the flow to the first
    real country on the link.
    """
    path = network_path(scenario, year)
    with xr.open_dataset(path) as ds:
        buses = list(ds["buses_i"].values)
        bus_carrier = pd.Series(ds["buses_carrier"].values, index=buses)
        country = pd.Series(ds["buses_country"].values, index=buses)
        links = list(ds["links_i"].values)
        weight = float(ds["snapshots_generators"].values[0])
        bus_cols = [
            pd.Series(ds[f"links_bus{port}"].values, index=links)
            for port in range(5)
            if f"links_bus{port}" in ds
        ]
        totals: dict[str, float] = {}
        for port in (1, 2, 3):
            time_name = f"links_t_p{port}"
            if time_name not in ds:
                continue
            names = list(ds[f"links_t_p{port}_i"].values)
            port_bus = pd.Series(ds[f"links_bus{port}"].values, index=links)
            co2_names = [name for name in names if bus_carrier.get(port_bus.get(name)) == "co2"]
            if not co2_names:
                continue
            columns = [names.index(name) for name in co2_names]
            injected = -pd.Series(ds[time_name].values[:, columns].sum(axis=0) * weight, index=co2_names)
            for name, value in injected.items():
                location = "EU"
                for column in bus_cols:
                    candidate = country.get(column.get(name))
                    if isinstance(candidate, str) and candidate not in {"EU", ""}:
                        location = candidate
                        break
                totals[location] = totals.get(location, 0.0) + float(value)
    series = pd.Series(totals, name=str(year))
    return series[series.index != "EU"]


def country_co2_tonnes(scenario: str, year: int) -> pd.Series:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"co2_{scenario}_{year}.csv"
    if cache.exists():
        frame = pd.read_csv(cache, index_col=0)
        return frame.iloc[:, 0]
    series = _country_co2_tonnes(scenario, year)
    series.to_csv(cache)
    return series


def co2_per_capita(scenario: str) -> pd.DataFrame:
    columns = [country_co2_tonnes(scenario, year).rename(str(year)) for year in HORIZONS]
    emitted = pd.concat(columns, axis=1)
    return emitted.div(population(), axis=0)


def system_curtailment_twh() -> pd.DataFrame:
    frames = []
    for scenario in SCENARIOS:
        for year in HORIZONS:
            part = country_vre_curtailment(scenario, year)
            total = part.groupby("tech")["twh"].sum()
            total = total.reindex(VRE_GROUPS.keys(), fill_value=0.0)
            frames.append(
                pd.DataFrame(
                    {
                        "scenario": scenario,
                        "year": year,
                        "tech": total.index,
                        "twh": total.values,
                    }
                )
            )
    return pd.concat(frames, ignore_index=True)
