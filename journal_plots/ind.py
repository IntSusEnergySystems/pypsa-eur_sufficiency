#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 31 14:04:53 2025

@author: umair
"""

import matplotlib.pyplot as plt
import numpy as np
import geopandas as gpd
import cartopy.crs as ccrs
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Patch
import pandas as pd
import pypsa

planning_horizons = [2030, 2040, 2050]
options = {}
for planning_horizon in planning_horizons:
 fn = f"../resources/ref/costs_{planning_horizon}_processed.csv"
 options[planning_horizon] = pd.read_csv(fn, index_col=[0, 1]).sort_index()
def build_filename_ref(planning_horizon):
    prefix=f"../results/ref/networks/"
    return prefix+"base_s_33___{planning_horizon}.nc".format(
        planning_horizon=planning_horizon
    )

def load_file_ref(filename):
    # Use pypsa.Network to load the network from the filename
    return pypsa.Network(filename)

def load_files_ref(planning_horizons):
    files = {}
    for planning_horizon in planning_horizons:
        filename = build_filename_ref(planning_horizon)
        files[planning_horizon] = load_file_ref(filename)
    return files

def build_filename_suff(planning_horizon):
    prefix=f"../results/suff/networks/"
    return prefix+"base_s_33___{planning_horizon}.nc".format(
        planning_horizon=planning_horizon
    )

def load_file_suff(filename):
    # Use pypsa.Network to load the network from the filename
    return pypsa.Network(filename)

def load_files_suff( planning_horizons):
    files = {}
    for planning_horizon in planning_horizons:
        filename = build_filename_suff(planning_horizon)
        files[planning_horizon] = load_file_suff(filename)
    return files
loaded_files_ref = load_files_ref(planning_horizons)
loaded_files_suff = load_files_suff(planning_horizons)

#%%
from matplotlib.lines import Line2D
# Initialize empty dictionaries to store results for each planning horizon
ref_solarn = {}
ref_onwindn = {}
ref_offwindn = {}
suff_solarn = {}
suff_onwindn = {}
suff_offwindn = {}

# Loop through each planning horizon to compute the curtailed energy
for planning_horizon in planning_horizons:
    n = loaded_files_ref[planning_horizon]
    m = loaded_files_suff[planning_horizon]
    
    ref_solarn[planning_horizon] = ((n.generators_t.p_max_pu * n.generators.p_nom_opt) - n.generators_t.p).filter(
        like="solar", axis=1
    ).sum(axis=1).sum() / 1e3

    ref_onwindn[planning_horizon] = ((n.generators_t.p_max_pu * n.generators.p_nom_opt) - n.generators_t.p).filter(
        like="onwind", axis=1
    ).sum(axis=1).sum() / 1e3

    ref_offwindn[planning_horizon] = ((n.generators_t.p_max_pu * n.generators.p_nom_opt) - n.generators_t.p).filter(
        like="offwind", axis=1
    ).sum(axis=1).sum() / 1e3

    suff_solarn[planning_horizon] = ((m.generators_t.p_max_pu * m.generators.p_nom_opt) - m.generators_t.p).filter(
        like="solar", axis=1
    ).sum(axis=1).sum() / 1e3

    suff_onwindn[planning_horizon] = ((m.generators_t.p_max_pu * m.generators.p_nom_opt) - m.generators_t.p).filter(
        like="onwind", axis=1
    ).sum(axis=1).sum() / 1e3

    suff_offwindn[planning_horizon] = ((m.generators_t.p_max_pu * m.generators.p_nom_opt) - m.generators_t.p).filter(
        like="offwind", axis=1
    ).sum(axis=1).sum() / 1e3
    
fig = plt.figure(figsize=(15, 6))  # Adjusted size for one row
gs = GridSpec(1, len(planning_horizons) * 2, figure=fig)  # 1 row, multiple columns (2 per planning horizon)

# Define colors and labels
colors = ['orange', 'blue', 'green']
labels = ['Solar', 'Onshore Wind', 'Offshore Wind']

# Loop for Reference Pie Charts (place all Ref pie charts in the first half of the row)
for i, planning_horizon in enumerate(planning_horizons):
    ref_total = sum([
        ref_solarn[planning_horizon],
        ref_onwindn[planning_horizon],
        ref_offwindn[planning_horizon],
    ])
    ref_radius = 0.5 + 0.5 * (ref_total / 70000)
    
    # Create subplot for Reference Pie chart in row 0, column i
    ax_ref_pie = fig.add_subplot(gs[0, i], aspect='equal')
    reference_data = [
        ref_solarn[planning_horizon],
        ref_onwindn[planning_horizon],
        ref_offwindn[planning_horizon],
    ]
    ax_ref_pie.pie(
        reference_data,
        startangle=90,
        colors=colors,
        radius=ref_radius,
        wedgeprops={'width': 0.5}
    )
    ax_ref_pie.set_title(
    f'{planning_horizon}',
    fontsize=15,
    # fontweight='bold',
    pad=40  # increase spacing above plot
)
    
    ax_ref_pie.text(
    0.5, -0.75,   # x=center, y=below pie
    f"{int(ref_total/1000)} TWh",
    transform=ax_ref_pie.transAxes,  # KEY LINE
    ha='center', va='center',
    fontsize=15, weight='bold'
)
reference_legend_handles = [Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markersize=15, label=label) 
                            for color, label in zip(colors, labels)]
fig.legend(handles=reference_legend_handles, bbox_to_anchor=(0.5, 0.2), fontsize=15,ncol=1)
# Loop for Sufficiency Pie Charts (place all Sufficiency pie charts in the second half of the row)
for i, planning_horizon in enumerate(planning_horizons):
    suff_total = sum([
        suff_solarn[planning_horizon],
        suff_onwindn[planning_horizon],
        suff_offwindn[planning_horizon],
    ])
    suff_radius = 0.5 + 0.5 * (suff_total / 70000)
    
    # Create subplot for Sufficiency Pie chart in row 0, column i + len(planning_horizons)
    ax_suff_pie = fig.add_subplot(gs[0, i + len(planning_horizons)], aspect='equal')
    sufficiency_data = [
        suff_solarn[planning_horizon],
        suff_onwindn[planning_horizon],
        suff_offwindn[planning_horizon],
    ]
    ax_suff_pie.pie(
        sufficiency_data,
        startangle=90,
        colors=colors,
        radius=suff_radius,
        wedgeprops={'width': 0.5},
    )
    ax_suff_pie.set_title(
    f'{planning_horizon}',
    fontsize=15,
    # fontweight='bold',
    pad=40  # increase spacing above plot
)
    
    ax_suff_pie.text(
    0.5, -0.75,   # x=center, y=below pie
    f"{int(suff_total/1000)} TWh",
    transform=ax_suff_pie.transAxes,  # KEY LINE
    ha='center', va='center',
    fontsize=15, weight='bold'
)


fig.text(0.05, 0.8,'(a) VRE curtailment in reference scenario', fontsize=16, weight='bold')
fig.text(0.55, 0.8, '(b) VRE curtailment in sufficiency scenario', fontsize=16, weight='bold')

plt.tight_layout()
plt.show()

#%%

regions = gpd.read_file("../resources/ref/regions_onshore_base_s_33.geojson").set_index("name")
regions['country_code'] = regions.index.str[:2]
regions = regions.set_index('country_code')

regions_suff = gpd.read_file("../resources/suff/regions_onshore_base_s_33.geojson").set_index("name")
regions_suff['country_code'] = regions_suff.index.str[:2]
regions_suff = regions_suff.set_index('country_code')
countries= ['AT', 'BE', 'BG', 'CH', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GB', 'GR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'NL', 'NO', 'PL', 'PT', 'SE', 'SI', 'SK', 'RO']
population = pd.read_csv("../resources/ref/pop_layout_base_s_33.csv", index_col=4)
population = population.drop(['name','fraction','urban','rural'], axis=1)
population = population.groupby(population.index).sum()
population = population.sum(axis=1) * 1000
ref={}
for country in countries:
 df = pd.read_excel(f"../results/ref/htmls/ChartData_{country}.xlsx",sheet_name="Chart 2", index_col=0)
 df.columns = df.iloc[1]
 df = df.drop(df.index[1])
 df = df.drop(df.index[0])
 df = df.apply(pd.to_numeric, errors='coerce')
 df = df.drop('2020', axis=0)
 df = df.drop(['biogas', 'biomass to liquid','Biomass','DAC','Land use and forestry'], axis=1)
 df = df.sum(axis=1)
 ref[country] = df * 1e6
 ref[country] = ref[country] /population[country]
 
for country in ref:
    ref[country] = ref[country].rename(int)
 
for planning_horizon in planning_horizons:
    regions[f'CO2_capita_{planning_horizon}'] = regions.index.map(
        lambda code: ref[code][planning_horizon] if code in ref and planning_horizon in ref[code] else None)
    
                                  
suff={}
for country in countries:
  cf = pd.read_excel(f"../results/suff/htmls/ChartData_{country}.xlsx",sheet_name="Chart 2", index_col=0)
  cf.columns = cf.iloc[1]
  cf = cf.drop(cf.index[1])
  cf = cf.drop(cf.index[0])
  cf = cf.apply(pd.to_numeric, errors='coerce')
  cf = cf.drop('2020', axis=0)
  cf = cf.drop(['biogas', 'biomass to liquid','Biomass','DAC','Land use and forestry'], axis=1)
  cf = cf.sum(axis=1)
  suff[country] = cf * 1e6
  suff[country] = suff[country] /population[country]
 
for country in suff:
    suff[country] = suff[country].rename(int)
 
for planning_horizon in planning_horizons:
    regions_suff[f'CO2_capita_{planning_horizon}'] = regions_suff.index.map(
        lambda code: suff[code][planning_horizon] if code in suff and planning_horizon in suff[code] else None)
import matplotlib as mpl
cmap = "Oranges"
norm = mpl.colors.Normalize(vmin=0, vmax=6)
fig_ref = plt.figure(figsize=(15, 6))  # Decreased figure size
gs_ref = fig_ref.add_gridspec(1, len(planning_horizons), wspace=0.3)

for idx, planning_horizon in enumerate(planning_horizons):
    ax_ref_map = fig_ref.add_subplot(gs_ref[0, idx], projection=ccrs.EqualEarth())

    # Manually adjust map size
    ax_ref_map.set_position([
        0.15 + idx * 0.2,  # Move maps horizontally
        0.2,             # Lower value moves it downward
        0.18,             # Width (decrease this to make maps smaller)
        0.7              # Height (decrease this to make maps smaller)
    ])

    regions.plot(
        ax=ax_ref_map,
        column=f'CO2_capita_{planning_horizon}',
        cmap=cmap,
        linewidth=0,
        legend=False,
        vmax=6,
        vmin=0,
    )
    ax_ref_map.set_title(f"{planning_horizon}", fontsize=20)
    ax_ref_map.axis("off")

cbar_ax_ref = fig_ref.add_axes([0.18, 0.15, 0.52, 0.05])  # Adjust position
cbar_ref = mpl.colorbar.ColorbarBase(
    cbar_ax_ref, cmap=cmap, norm=norm, orientation="horizontal"
)
cbar_ref.set_label("Mean CO2 Emissions [Tons/Capita]", fontsize=20)
cbar_ref.ax.tick_params(labelsize=15)
plt.show()


fig_suff = plt.figure(figsize=(15, 6))
gs_suff = fig_suff.add_gridspec(1, len(planning_horizons), wspace=0.3)

# Loop for Sufficiency maps
for idx, planning_horizon in enumerate(planning_horizons):
    ax_suff_map = fig_suff.add_subplot(gs_suff[0, idx], projection=ccrs.EqualEarth())
    ax_suff_map.set_position([
        0.15 + idx * 0.2,  # Move maps horizontally
        0.2,             # Lower value moves it downward
        0.18,             # Width (decrease this to make maps smaller)
        0.7              # Height (decrease this to make maps smaller)
    ])
    regions_suff.plot(
        ax=ax_suff_map,
        column=f'CO2_capita_{planning_horizon}',
        cmap=cmap,
        linewidth=0,
        legend=False,
        vmax=6,
        vmin=0,
    )
    ax_suff_map.set_title(f"{planning_horizon}", fontsize=20)
    ax_suff_map.axis("off")

# Colorbar for Sufficiency maps
cbar_ax_suff = fig_suff.add_axes([0.18, 0.15, 0.52, 0.05])  # Adjust position
cbar_suff = mpl.colorbar.ColorbarBase(
    cbar_ax_suff, cmap=cmap, norm=norm, orientation="horizontal"
)
cbar_suff.set_label("Mean CO2 Emissions [Tons/Capita]", fontsize=20)
cbar_suff.ax.tick_params(labelsize=15)


plt.show()

#%%
carriers = [
    "AC",
    "H2",
    "urban central heat",
]
# Initialize dictionaries to store aggregated prices
prices_ref_dict = {carrier: [] for carrier in carriers}
prices_suff_dict = {carrier: [] for carrier in carriers}

# Aggregate prices for each carrier and planning horizon
for carrier in carriers:
    for planning_horizon in planning_horizons:
        n = loaded_files_ref[planning_horizon]
        m = loaded_files_suff[planning_horizon]

        # Calculate prices for Reference and Sufficiency
        prices_ref = n.buses_t.marginal_price.loc[:, n.buses.carrier == carrier]
        prices_suff = m.buses_t.marginal_price.loc[:, m.buses.carrier == carrier]

        # Aggregate and normalize
        avg_price_ref = prices_ref.sum(axis=1).sum() / 8760 / 32
        avg_price_suff = prices_suff.sum(axis=1).sum() / 8760 / 32

        # Append to respective dictionaries
        prices_ref_dict[carrier].append(avg_price_ref)
        prices_suff_dict[carrier].append(avg_price_suff)

# Convert planning horizons to string format for labeling
planning_horizons_str = [str(ph) for ph in planning_horizons]

# Define carrier names and colors
carrier_name_map = {
    "AC": "Electricity",
    "H2": "Hydrogen",
    "urban central heat": "District Heating",
}
carrier_colors = {
    "AC": "#110d63",
    "H2": "#bf13a0",
    "urban central heat": "orange",
}

marker_styles = ['o', 's', 'v']  # Different markers for each carrier
marker_size = 10  # Reduce marker size for better readability

# --- PLOT FOR REFERENCE PRICES ---
fig_ref, ax_ref_price = plt.subplots(figsize=(8, 5))  # Create a figure for Reference prices

for carrier, marker in zip(carriers, marker_styles):
    display_name = carrier_name_map.get(carrier, carrier)
    color = carrier_colors.get(carrier, "black")
    
    ax_ref_price.plot(
        planning_horizons_str,
        prices_ref_dict[carrier],
        label=display_name,
        marker=marker,
        markersize=marker_size,
        color=color
    )

ax_ref_price.set_ylabel("Average Price [EUR/MWh]", fontsize=15)
ax_ref_price.legend(fontsize=15, ncol=1, loc="upper left")
ax_ref_price.grid(True, linestyle="--", alpha=0.3)
ax_ref_price.set_ylim(0, 100)
ax_ref_price.tick_params(axis='x', labelsize=15)
ax_ref_price.tick_params(axis='y', labelsize=15)

plt.tight_layout()
plt.show()

# --- PLOT FOR SUFFICIENCY PRICES ---
fig_suff, ax_suff_price = plt.subplots(figsize=(8, 5))  # Create a figure for Sufficiency prices

for carrier, marker in zip(carriers, marker_styles):
    display_name = carrier_name_map.get(carrier, carrier)
    color = carrier_colors.get(carrier, "black")
    
    ax_suff_price.plot(
        planning_horizons_str,
        prices_suff_dict[carrier],
        label=display_name,
        marker=marker,
        markersize=marker_size,
        color=color
    )

ax_suff_price.set_ylabel("Average Price [EUR/MWh]", fontsize=15)
ax_suff_price.legend(fontsize=15, ncol=1, loc="upper left")
ax_suff_price.grid(True, linestyle="--", alpha=0.3)
ax_suff_price.set_ylim(0, 100)
ax_suff_price.tick_params(axis='x', labelsize=15)
ax_suff_price.tick_params(axis='y', labelsize=15)

plt.tight_layout()
plt.show()