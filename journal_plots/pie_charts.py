#!/usr/bin/env python3
"""Belgium carrier imports and local supply in 2050 for the three scenarios."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import json

import geopandas as gpd
import plotly.graph_objects as go
import plotly.offline as pyo
from plotly.subplots import make_subplots

import common

IMPORT_CARRIERS = {
    "gas": "Natural gas",
    "oil primary": "Petroleum",
    "coal": "Coal",
    "lignite": "Lignite",
    "uranium": "Uranium",
}
LOCAL_CARRIERS = [
    "solar",
    "solar rooftop",
    "solar-hsat",
    "onwind",
    "offwind-ac",
    "offwind-dc",
    "offwind-float",
    "hydro",
    "ror",
    "biogas",
]
CARRIER_COLORS = {
    "Natural gas": "#e05b09",
    "Petroleum": "#c9c9c9",
    "Coal": "#545454",
    "Lignite": "#333333",
    "Uranium": "orange",
    "Local production": "black",
    "Imports": "whitesmoke",
}


def belgium_2050(scenario: str) -> tuple[list[tuple[str, float]], float, float]:
    balance = common.read_csv(scenario, "nodal_energy_balance")
    be = balance.loc[balance["location"] == "BE"]
    imports = []
    for carrier, label in IMPORT_CARRIERS.items():
        value = be.loc[be["carrier"] == carrier, "2050"].clip(lower=0).sum()
        imports.append((label, float(value)))
    local = float(be.loc[be["carrier"].isin(LOCAL_CARRIERS), "2050"].clip(lower=0).sum())
    imported = float(sum(value for _, value in imports))
    return imports, imported, local


def main() -> None:
    regions = gpd.read_file(common.regions_path("ref"))
    europe = json.loads(regions.to_json())
    names = regions["name"].tolist()
    neighbours = {"BE": 3, "DE": 1, "FR": 1, "NL": 1, "GB": 1, "LU": 1}
    z_vals = [neighbours.get(name, 0) for name in names]

    columns = common.SCENARIOS
    fig = make_subplots(
        rows=2,
        cols=4,
        specs=[
            [{"type": "choropleth", "rowspan": 2}, {"type": "domain"}, {"type": "domain"}, {"type": "domain"}],
            [None, {"type": "domain"}, {"type": "domain"}, {"type": "domain"}],
        ],
        subplot_titles=["", *[f"{common.LABELS[s]} (2050)" for s in columns], "", "", "", ""],
    )
    fig.add_trace(
        go.Choropleth(
            geojson=europe,
            locations=names,
            z=z_vals,
            featureidkey="properties.name",
            colorscale=[[0, "gray"], [0.5, "whitesmoke"], [1, "black"]],
            zmin=0,
            zmax=2,
            showscale=False,
            marker_line_color="gray",
            hoverinfo="location",
        ),
        row=1,
        col=1,
    )
    fig.update_geos(
        scope="europe",
        center=dict(lat=50.85, lon=4.35),
        projection_scale=5,
        showland=True,
        landcolor="whitesmoke",
        showcountries=True,
    )

    for col, scenario in enumerate(columns, start=2):
        imports, imported, local = belgium_2050(scenario)
        labels = [label for label, _ in imports]
        values = [value for _, value in imports]
        fig.add_trace(
            go.Pie(
                labels=labels,
                values=values,
                hole=0.5,
                name=common.LABELS[scenario],
                scalegroup="imports",
                marker=dict(colors=[CARRIER_COLORS[label] for label in labels]),
            ),
            row=1,
            col=col,
        )
        fig.add_trace(
            go.Pie(
                labels=["Imports", "Local production"],
                values=[imported, local],
                hole=0.5,
                name="Total",
                scalegroup="totals",
                marker=dict(colors=[CARRIER_COLORS["Imports"], CARRIER_COLORS["Local production"]]),
            ),
            row=2,
            col=col,
        )

    out = common.OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    html = out / "belgium_map_with_scaled_pies.html"
    pyo.plot(fig, filename=str(html), auto_open=False)
    print(html)


if __name__ == "__main__":
    main()
