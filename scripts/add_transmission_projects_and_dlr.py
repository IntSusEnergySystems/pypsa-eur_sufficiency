# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""
Add transmission projects and DLR to the network.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import pypsa
import xarray as xr

from scripts._helpers import configure_logging, set_scenario_config

logger = logging.getLogger(__name__)


def _planned_tyndp_capacity(projects_dir: str = "data/transmission_projects") -> pd.Series:
    """Planned DC capacity (MW) from the transmission project tables, by project name."""
    planned = {}
    root = Path(projects_dir)
    if not root.is_dir():
        return pd.Series(dtype=float)
    for path in sorted(root.glob("*/new_links.csv")):
        if path.parent.name == "template":
            continue
        projects = pd.read_csv(path, index_col=0)
        if "p_nom" not in projects.columns:
            continue
        planned.update(projects["p_nom"].dropna().astype(float).to_dict())
    return pd.Series(planned, dtype=float)


def apply_tyndp_link_capacities(
    n: pypsa.Network,
    year: int,
    projects_dir: str = "data/transmission_projects",
) -> None:
    """
    Put the planned capacity on TYNDP DC links once their build year is reached.

    A project is part of planning horizon ``year`` when ``build_year <= year``.
    Later projects are removed. ``relation/...`` links are the existing grid and
    are left unchanged. Both directions of a project receive the same ``p_nom``.
    """
    if n.links.empty or "carrier" not in n.links.columns:
        return

    names = pd.Series(n.links.index.astype(str), index=n.links.index)
    tyndp = n.links.index[n.links.carrier.eq("DC") & names.str.startswith("TYNDP")]
    if tyndp.empty:
        logger.info("No TYNDP DC links to update for %s", year)
        return

    planned = _planned_tyndp_capacity(projects_dir)
    project = names[tyndp].str.replace(r"-reversed$", "", regex=True)
    project.index = tyndp
    capacity = project.map(planned)
    missing = capacity.index[capacity.isna()]
    if len(missing):
        logger.warning(
            "No planned capacity found for %d TYNDP links, leaving p_nom unchanged: %s",
            len(missing),
            ", ".join(map(str, missing[:8])),
        )

    build_year = n.links.loc[tyndp, "build_year"]
    # Projects with no build year are not commissioned on a horizon.
    future = tyndp[build_year.isna() | (build_year > year)]
    ready = tyndp.difference(future)
    known = ready[capacity.reindex(ready).notna()]
    if len(known):
        n.links.loc[known, "p_nom"] = capacity.loc[known].to_numpy()
        n.links.loc[known, "p_nom_min"] = capacity.loc[known].to_numpy()

    if len(future):
        logger.info(
            "Leaving out %d TYNDP DC links whose build year is after %s",
            len(future),
            year,
        )
        n.remove("Link", future)

    online = n.links.index.intersection(ready)
    project = pd.Index(online.astype(str)).str.replace(r"-reversed$", "", regex=True)
    installed = n.links.loc[online].groupby(project).p_nom.first().sum() / 1e3
    logger.info(
        "TYNDP DC capacity online in %s: %.2f GW across %d links",
        year,
        installed,
        len(online),
    )


def attach_transmission_projects(
    n: pypsa.Network, transmission_projects: list[str]
) -> None:
    logger.info("Adding transmission projects to network.")
    for path in transmission_projects:
        path = Path(path)
        df = pd.read_csv(path, index_col=0, dtype={"bus0": str, "bus1": str})
        if df.empty:
            continue
        if "new_buses" in path.name:
            n.add("Bus", df.index, **df)
        elif "new_lines" in path.name:
            n.add("Line", df.index, **df)
        elif "new_links" in path.name:
            n.add("Link", df.index, **df)
        elif "adjust_lines" in path.name:
            n.lines.update(df)
        elif "adjust_links" in path.name:
            n.links.update(df)


def attach_line_rating(
    n: pypsa.Network,
    rating: pd.DataFrame,
    s_max_pu: float,
    correction_factor: float,
    max_voltage_difference: float | bool,
    max_line_rating: float | bool,
) -> None:
    logger.info("Attaching dynamic line rating to network.")
    # TODO: Only considers overhead lines
    n.lines_t.s_max_pu = (rating / n.lines.s_nom[rating.columns]) * correction_factor
    if max_voltage_difference:
        x_pu = (
            n.lines.type.map(n.line_types["x_per_length"])
            * n.lines.length
            / (n.lines.v_nom**2)
        )
        # need to clip here as cap values might be below 1
        # -> would mean the line cannot be operated at actual given pessimistic ampacity
        s_max_pu_cap = (
            np.deg2rad(max_voltage_difference) / (x_pu * n.lines.s_nom)
        ).clip(lower=1)
        n.lines_t.s_max_pu = n.lines_t.s_max_pu.clip(
            lower=1, upper=s_max_pu_cap, axis=1
        )
    if max_line_rating:
        n.lines_t.s_max_pu = n.lines_t.s_max_pu.clip(upper=max_line_rating)
    n.lines_t.s_max_pu *= s_max_pu


if __name__ == "__main__":
    if "snakemake" not in globals():
        from scripts._helpers import mock_snakemake

        snakemake = mock_snakemake("add_transmission_projects_and_dlr")
    configure_logging(snakemake)  # pylint: disable=E0606
    set_scenario_config(snakemake)

    params = snakemake.params

    n = pypsa.Network(snakemake.input.network)

    if params["transmission_projects"]["enable"]:
        attach_transmission_projects(n, snakemake.input.transmission_projects)

    if params["dlr"]["activate"]:
        rating = xr.open_dataarray(snakemake.input.dlr).to_pandas().transpose()

        s_max_pu = params["s_max_pu"]
        correction_factor = params["dlr"]["correction_factor"]
        max_voltage_difference = params["dlr"]["max_voltage_difference"]
        max_line_rating = params["dlr"]["max_line_rating"]

        attach_line_rating(
            n,
            rating,
            s_max_pu,
            correction_factor,
            max_voltage_difference,
            max_line_rating,
        )

    n.export_to_netcdf(snakemake.output[0])
