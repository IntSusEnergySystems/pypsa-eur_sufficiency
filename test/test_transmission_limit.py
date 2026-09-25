"""Transmission expansion is capped from each asset's own rating."""

import pandas as pd
import pypsa

from scripts.add_transmission_projects_and_dlr import apply_tyndp_link_capacities
from scripts.prepare_network import cap_transmission_capacity, set_transmission_limit


def _costs() -> pd.DataFrame:
    return pd.DataFrame(
        {"capital_cost": [1.0, 2.0, 3.0, 4.0]},
        index=[
            "HVAC overhead",
            "HVDC overhead",
            "HVDC submarine",
            "HVDC inverter pair",
        ],
    )


def test_transmission_limit_scales_existing_ratings():
    n = pypsa.Network()
    n.add("Bus", ["A", "B"], v_nom=380)
    n.add(
        "Line",
        "ac",
        bus0="A",
        bus1="B",
        carrier="AC",
        s_nom=1000,
        length=100,
        s_nom_max=float("inf"),
    )
    n.add(
        "Link",
        "dc",
        bus0="A",
        bus1="B",
        carrier="DC",
        p_nom=400,
        length=100,
        underwater_fraction=0,
        p_nom_max=float("inf"),
    )

    set_transmission_limit(n, "v", "1.5", _costs())
    cap_transmission_capacity(
        n,
        line_max=float("inf"),
        link_max=float("inf"),
        line_max_extension=20000,
        link_max_extension=30000,
    )

    assert n.lines.loc["ac", "s_nom_min"] == 1000
    assert n.lines.loc["ac", "s_nom_max"] == 1500
    assert n.links.loc["dc", "p_nom_min"] == 400
    assert n.links.loc["dc", "p_nom_max"] == 600
    assert n.global_constraints.loc["lv_limit", "constant"] == 1.5 * (1000 * 100 + 400 * 100)


def _tyndp_network() -> pypsa.Network:
    n = pypsa.Network()
    n.add("Bus", ["A", "B"])
    n.add(
        "Link",
        "relation/1-DC",
        bus0="A",
        bus1="B",
        carrier="DC",
        p_nom=1000,
        build_year=0,
    )
    n.add(
        "Link",
        ["TYNDP2020_17", "TYNDP2020_17-reversed", "TYNDP2020_late"],
        bus0=["A", "B", "A"],
        bus1=["B", "A", "B"],
        carrier="DC",
        p_nom=0,
        build_year=[2026, 2026, 2035],
    )
    return n


def test_tyndp_capacity_follows_build_year(tmp_path):
    folder = tmp_path / "tyndp2020"
    folder.mkdir()
    pd.DataFrame(
        {"p_nom": [700.0, 1000.0], "build_year": [2026, 2035]},
        index=["TYNDP2020_17", "TYNDP2020_late"],
    ).to_csv(folder / "new_links.csv")

    early = _tyndp_network()
    apply_tyndp_link_capacities(early, 2030, projects_dir=tmp_path.as_posix())
    assert early.links.loc["relation/1-DC", "p_nom"] == 1000
    assert early.links.loc["TYNDP2020_17", "p_nom"] == 700
    assert early.links.loc["TYNDP2020_17-reversed", "p_nom"] == 700
    assert "TYNDP2020_late" not in early.links.index

    later = _tyndp_network()
    apply_tyndp_link_capacities(later, 2035, projects_dir=tmp_path.as_posix())
    assert later.links.loc["TYNDP2020_late", "p_nom"] == 1000
