#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  3 16:07:14 2025

@author: umair
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.offline as pyo
from plotly.subplots import make_subplots
import json

with open("../data/europe.geojson") as f:
    europe_geojson = json.load(f)
visible_countries = {
    "Belgium": 3,  # Black
    "Germany": 1,  # Gray
    "France": 1,
    "Netherlands": 1,
    "United Kingdom": 1,
}

# Extract all country names
country_names = [feature["properties"]["NAME"] for feature in europe_geojson["features"]]

# Prepare values: assign each country a value or None
z_vals = [visible_countries.get(name, None) for name in country_names]

imports_ref = pd.read_csv("../results/ref/country_csvs/total_imports_BE.csv",index_col=0).clip(lower=0)
imports_suff = pd.read_csv("../results/suff/country_csvs/total_imports_BE.csv",index_col=0).clip(lower=0)
local_ref = pd.read_csv("../results/ref/country_csvs/local_product_BE.csv",index_col=0).clip(lower=0)
local_suff = pd.read_csv("../results/suff/country_csvs/local_product_BE.csv",index_col=0).clip(lower=0)
base_cols = {
    'imp_gaz_pe': 'Natural gas',
    'imp_pet_pe': 'Petroleum',
    'imp_elc_se': 'Electricity',
    'imp_cms_pe': 'Coal',
    'imp_hyd_se': 'Hydrogen',
    'imp_enc_pe': 'Solid biomass',
    'imp_amm_fe': 'Ammonia',
    'imp_met_fe': 'Methanol',
    'ura_pe_elc_se': 'Uranium'
}
carrier_colors = {
    'Natural gas': '#e05b09',
    'Petroleum': '#c9c9c9',
    'Electricity': '#110d63',
    'Coal': '#545454',
    'Hydrogen': '#bf13a0',
    'Solid biomass': '#baa741',
    'Ammonia': '#46caf0',
    'Methanol': '#468c8b',
    'Local production': 'black',
    'Imports': 'whitesmoke',
    'Uranium': 'orange'
}
ref_renamed = {k: f"{v}" for k, v in base_cols.items()}
suff_renamed = {k: f"{v}" for k, v in base_cols.items()}
imports_ref.rename(columns=ref_renamed, inplace=True)
imports_suff.rename(columns=suff_renamed, inplace=True)
imports_ref_2050 = imports_ref.loc[2050]
imports_suff_2050 = imports_suff.loc[2050]
imports_2020 = imports_ref.loc[2020]

imports_ref_2050_sum = imports_ref.loc[2050].sum()
imports_suff_2050_sum = imports_suff.loc[2050].sum()
imports_2020_sum = imports_ref.loc[2020].sum()
local_ref_2050_sum = local_ref.loc[2050].sum()
local_suff_2050_sum = local_suff.loc[2050].sum()
local_2020_sum = local_ref.loc[2020].sum()

num_pies= 3
fig = make_subplots(
    rows=2, cols=4,
    specs=[
        [{"type": "choropleth", "rowspan": 2}, {"type": "domain"}, {"type": "domain"}, {"type": "domain"}],
        [None, {"type": "domain"}, {"type": "domain"}, {"type": "domain"}]
    ],
    column_widths=[0.5] + [0.5/num_pies]*num_pies,
    row_heights=[0.5] + [0.5],
    vertical_spacing=0.01,
    horizontal_spacing=0.01,
    subplot_titles=(
        "", "2020", "Ref (2050)", "Suff (2050)",
        "", "", "", ""
    )
)

# --- Row 1 ---
fig.add_trace(go.Choropleth(
    geojson=europe_geojson,
    locations=country_names,
    z=z_vals,
    featureidkey="properties.NAME",
    colorscale=[
        [0, "gray"],
        [0.5, "whitesmoke"],
        [1, "black"]
    ],
    zmin=0,
    zmax=2,
    showscale=False,
    marker_line_color='gray',
    hoverinfo="location"
), row=1, col=1)

fig.update_geos(
    scope="europe",
    center=dict(lat=50.85, lon=4.35),
    projection_scale=5,
    showland=True,
    landcolor="whitesmoke",
    showcountries=True,
    # fitbounds="locations"
)
labels = imports_2020.index
values = imports_2020.values
colors = [carrier_colors[label] for label in labels]
fig.add_trace(go.Pie(
    labels=labels,
    values=values,
    hole=0.5,
    name="2020",
    scalegroup='group1',
    marker=dict(colors=colors)
), row=1, col=2)
labels = imports_ref_2050.index
values = imports_ref_2050.values
colors = [carrier_colors[label] for label in labels]
fig.add_trace(go.Pie(
    labels=labels,
    values=values,
    hole=0.5,
    name="Ref 2050",
    scalegroup='group1',
    marker=dict(colors=colors)
), row=1, col=3)
labels = imports_suff_2050.index
values = imports_suff_2050.values
colors = [carrier_colors[label] for label in labels]
fig.add_trace(go.Pie(
    labels=labels,
    values=values,
    hole=0.5,
    name="Suff 2050",
    scalegroup='group1',
    marker=dict(colors=colors)
), row=1, col=4)

# --- Row 2: Total Sums as 1-slice pies ---
fig.add_trace(go.Pie(
    labels=["Imports", "Local production"],
    values=[imports_2020_sum,local_2020_sum],
    hole=0.5,
    name="Total",
    # textinfo='percent+value',
    scalegroup='group2',
    marker=dict(colors=[carrier_colors["Imports"], carrier_colors["Local production"]])
), row=2, col=2)

fig.add_trace(go.Pie(
    labels=["Imports", "Local production"],
    values=[imports_ref_2050_sum,local_ref_2050_sum],
    hole=0.5,
    name="Total",
    # textinfo='label+value',
    scalegroup='group2',
    marker=dict(colors=[carrier_colors["Imports"], carrier_colors["Local production"]])
), row=2, col=3)

fig.add_trace(go.Pie(
    labels=["Imports", "Local production"],
    values=[imports_suff_2050_sum,local_suff_2050_sum],
    hole=0.5,
    name="Total",
    # textinfo='label+value',
    scalegroup='group2',
    marker=dict(colors=[carrier_colors["Imports"], carrier_colors["Local production"]])
), row=2, col=4)

pyo.plot(fig, filename="belgium_map_with_scaled_pies.html")