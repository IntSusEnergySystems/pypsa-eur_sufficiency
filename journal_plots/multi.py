#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 13 11:03:53 2025

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

# Initialize empty dictionaries to store results for each planning horizon
ref_solarn = {}
ref_onwindn = {}
ref_offwindn = {}
suff_solarn = {}
suff_onwindn = {}
suff_offwindn = {}

ref_ccgt = {}
ref_nuc = {}
suff_ccgt = {}
suff_nuc = {}

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
    
    ref_ccgt[planning_horizon] =  abs((n.links_t.p0.filter(like="CCGT").sum(axis=1).sum())/(8760* n.links.p_nom_opt.filter(like="CCGT").sum().sum()))
    ref_nuc[planning_horizon] =  abs((n.links_t.p0.filter(like="nuclear").sum(axis=1).sum())/(8760* n.links.p_nom_opt.filter(like="nuclear").sum().sum()))
    
    suff_ccgt[planning_horizon] =  abs((m.links_t.p0.filter(like="CCGT").sum(axis=1).sum())/(8760* m.links.p_nom_opt.filter(like="CCGT").sum().sum()))
    suff_nuc[planning_horizon] =  abs((m.links_t.p0.filter(like="nuclear").sum(axis=1).sum())/(8760*m.links.p_nom_opt.filter(like="nuclear").sum().sum()))

# Load data for self-sufficiency plots
bau_ss = pd.read_excel("../results/ref/htmls/ChartData_EU.xlsx", sheet_name="Chart 7", index_col=0)
new_index = bau_ss.iloc[1]
bau_ss.columns = new_index
bau_ss = bau_ss.drop(bau_ss.index[:2])
bau_ss = bau_ss.apply(pd.to_numeric, errors='coerce').fillna(0)
bau_gas = bau_ss["Natural gas"]
bau_pet = bau_ss["Petroleum"]

ncdr_ss = pd.read_excel("../results/suff/htmls/ChartData_EU.xlsx", sheet_name="Chart 7", index_col=0)
new_index = ncdr_ss.iloc[1]
ncdr_ss.columns = new_index
ncdr_ss = ncdr_ss.drop(ncdr_ss.index[:2])
ncdr_ss = ncdr_ss.apply(pd.to_numeric, errors='coerce').fillna(0)
ncdr_gas = ncdr_ss["Natural gas"]
ncdr_pet = ncdr_ss["Petroleum"]

def create_sparkline(ax, reference_data, sufficiency_data, color1, color2, x_label=None, y_label=None):
    ax.plot(reference_data, color=color1, marker='o',markersize=10, label='Gas')
    ax.plot(sufficiency_data, color=color2, marker='x',markersize=10, label='Oil')
    ax.set_xlabel(x_label, fontsize=8) if x_label else None
    ax.set_ylabel(y_label, fontsize=20) if y_label else None
    ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.7)
    ax.legend(fontsize=15),
    ax.tick_params(axis='x', labelsize=20)
    ax.tick_params(axis='y', labelsize=20)

labels = ['Solar', 'Onwind', 'Offwind']
colors = ['#f9d002', '#235ebc', '#6895dd']

fig = plt.figure(figsize=(18, 20))  # Larger size for better clarity

# Define grid layout with proper spacing

gs = GridSpec(6, 2, height_ratios=[1, 3, 1, 3, 3,1], hspace=0.3, wspace=0.4)

# Add column labels (Reference and Sufficiency)
fig.text(0.25, 0.98, "Reference Scenario", fontsize=20, weight='bold', ha='center')
fig.text(0.75, 0.98, "Sufficiency Scenario", fontsize=20, weight='bold', ha='center')

# Add row labels
fig.text(0.02, 0.87, "(a) Self-Sufficiency", fontsize=20, weight='bold', va='center', rotation='vertical')
fig.text(0.02, 0.68, "(b) Energy Curtailment", fontsize=20, weight='bold', va='center', rotation='vertical')
fig.text(0.02, 0.5, "(c) Capacity Factors", fontsize=20, weight='bold', va='center', rotation='vertical')
fig.text(0.02, 0.3, "(d) CO2 Emissions/Capita", fontsize=20, weight='bold', va='center', rotation='vertical')
fig.text(0.02, 0.09, "(e) Wholesale Prices", fontsize=20, weight='bold', va='center', rotation='vertical')

# First row: Line plots for self-sufficiency
ax_ref_ss = fig.add_subplot(gs[0, 0])
ax_suff_ss = fig.add_subplot(gs[0, 1])
ax_ref_ss.set_position([0.1, 0.8, 0.35, 0.15])  # [left, bottom, width, height]
ax_suff_ss.set_position([0.55, 0.8, 0.35, 0.15])
# Reference line plot for self-sufficiency
create_sparkline(
    ax_ref_ss,
    bau_gas,
    bau_pet,
    '#e05b09',
    '#c9c9c9',
    y_label='Annual Self-Sufficiency [%]',
    # legend_loc='upper left'
)

# Sufficiency line plot for self-sufficiency
create_sparkline(
    ax_suff_ss,
    ncdr_gas,
    ncdr_pet,
    '#e05b09',
    '#c9c9c9',
    y_label='Annual Self-Sufficiency [%]',
    # legend_loc='upper left'
)

# Second row: Pie charts for Reference and Sufficiency
# Reference Pie Charts
for i, planning_horizon in enumerate(planning_horizons):
    ref_total = sum([
        ref_solarn[planning_horizon],
        ref_onwindn[planning_horizon],
        ref_offwindn[planning_horizon],
    ])
    ref_radius = 0.5 + 0.5 * (ref_total / 200000)
    
    # Dynamic positioning for Reference pie charts
    ax_ref_pie = fig.add_subplot(gs[1, 0], aspect='equal')  # Place in Reference column
    ax_ref_pie.set_position([
        0.05 + i * 0.12,  # Adjust horizontal spacing
        0.6,             # Vertical alignment remains constant for all Reference pies
        0.15,            # Fixed width for each pie
        0.15,            # Fixed height for each pie
    ])
    reference_data = [
        ref_solarn[planning_horizon],
        ref_onwindn[planning_horizon],
        ref_offwindn[planning_horizon],
    ]
    ax_ref_pie.pie(
        reference_data,
        # autopct='%1.1f%%',
        startangle=90,
        colors=colors,
        radius=ref_radius,
        wedgeprops={'width': 0.2}
    )
    ax_ref_pie.set_title(planning_horizon, fontsize=20)
    
    ax_ref_pie.text(
        0, 0,  # Center of the plot
        f"{int(ref_total/1000)} TWh",  # Format the total with commas
        ha='center', va='center', fontsize=18, weight='bold'
    )

reference_legend_handles = [Patch(color=color, label=label) for color, label in zip(colors, labels)]
fig.legend(handles=reference_legend_handles, bbox_to_anchor=(0.56, 0.72), fontsize=18,ncol=1)
# Sufficiency Pie Charts
for i, planning_horizon in enumerate(planning_horizons):
    suff_total = sum([
        suff_solarn[planning_horizon],
        suff_onwindn[planning_horizon],
        suff_offwindn[planning_horizon],
    ])
    suff_radius = 0.5 + 0.5 * (suff_total / 200000)
    
    # Dynamic positioning for Sufficiency pie charts
    ax_suff_pie = fig.add_subplot(gs[1, 1], aspect='equal')  # Place in Sufficiency column
    ax_suff_pie.set_position([
        0.55 + i * 0.12,  # Adjust horizontal spacing
        0.6,              # Vertical alignment remains constant for all Sufficiency pies
        0.15,             # Fixed width for each pie
        0.15,             # Fixed height for each pie
    ])
    sufficiency_data = [
        suff_solarn[planning_horizon],
        suff_onwindn[planning_horizon],
        suff_offwindn[planning_horizon],
    ]
    ax_suff_pie.pie(
        sufficiency_data,
        # autopct='%1.1f%%',
        startangle=90,
        colors=colors,
        radius=suff_radius,
        wedgeprops={'width': 0.2}
    )
    ax_suff_pie.set_title(planning_horizon, fontsize=20)
    
    ax_suff_pie.text(
        0, 0,  # Center of the plot
        f"{int(suff_total/1000)} TWh",  # Format the total with commas
        ha='center', va='center', fontsize=18, weight='bold'
    )


ax_ref_bar = fig.add_subplot(gs[2, 0])  # Place in Reference column

# Data preparation for Reference
ref_nuc_values = [ref_nuc[ph] for ph in planning_horizons]
ref_ccgt_values = [ref_ccgt[ph] for ph in planning_horizons]
x_positions = np.arange(len(planning_horizons))  # x positions for groups of bars
bar_width = 0.25

# Plotting Reference bars
ax_ref_bar.bar(x_positions - bar_width / 2, ref_nuc_values, color='#ff8c00', width=bar_width, label='Nuclear')
ax_ref_bar.bar(x_positions + bar_width / 2, ref_ccgt_values, color='#a85522', width=bar_width, label='CCGT')

# Formatting Reference plot
ax_ref_bar.set_xticks(x_positions)
ax_ref_bar.set_xticklabels(planning_horizons)
ax_ref_bar.set_ylabel('Average Capacity Factor', fontsize=20)
ax_ref_bar.set_ylim(0, 1)  # Assuming capacity factors are fractions between 0 and 1
ax_ref_bar.tick_params(axis='x', labelsize=20)
ax_ref_bar.tick_params(axis='y', labelsize=20)
ax_ref_bar.grid(
    axis='both',  # Add gridlines along the y-axis
    linestyle='--',  # Dashed line style
    linewidth=0.5,   # Thin grid lines
    alpha=0.7        # Slightly transparent grid
)
ax_ref_bar.set_axisbelow(True)
ax_ref_bar.legend(fontsize=18, loc='upper left', bbox_to_anchor=(1.0, 1.0))
ax_ref_bar.set_position([0.1, 0.425, 0.3, 0.15])

# Bar plot for Sufficiency (Capacity Factors by Planning Horizon)
ax_suff_bar = fig.add_subplot(gs[2, 1])  # Place in Sufficiency column

# Data preparation for Sufficiency
suff_nuc_values = [suff_nuc[ph] for ph in planning_horizons]
suff_ccgt_values = [suff_ccgt[ph] for ph in planning_horizons]

# Plotting Sufficiency bars
ax_suff_bar.bar(x_positions - bar_width / 2, suff_nuc_values, color='#ff8c00', width=bar_width, label='Nuclear')
ax_suff_bar.bar(x_positions + bar_width / 2, suff_ccgt_values, color='#a85522', width=bar_width, label='CCGT')

# Formatting Sufficiency plot
ax_suff_bar.set_xticks(x_positions)
ax_suff_bar.set_xticklabels(planning_horizons)
ax_suff_bar.set_ylabel('Average Capacity Factor', fontsize=20)
ax_suff_bar.set_ylim(0, 1)  # Assuming capacity factors are fractions between 0 and 1
ax_suff_bar.tick_params(axis='x', labelsize=20)
ax_suff_bar.tick_params(axis='y', labelsize=20)
ax_suff_bar.grid(
    axis='both',  # Add gridlines along the y-axis
    linestyle='--',  # Dashed line style
    linewidth=0.5,   # Thin grid lines
    alpha=0.7        # Slightly transparent grid
)
ax_suff_bar.set_axisbelow(True)
ax_suff_bar.legend(fontsize=18, loc='upper left', bbox_to_anchor=(1.0, 1.0))
ax_suff_bar.set_position([0.58, 0.425, 0.3, 0.15])

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
cmap = "OrRd"
norm = mpl.colors.Normalize(vmin=0, vmax=6)
for idx, planning_horizon in enumerate(planning_horizons):
    ax_ref_map = fig.add_subplot(gs[4, 0], projection=ccrs.EqualEarth())
    ax_ref_map.set_position([
        0.08 + idx * 0.12,  # Adjust horizontal spacing for Reference maps
        0.22,               # Fixed vertical position for all Reference maps
        0.12,              # Width of each map
        0.15,              # Height of each map
    ])
    regions.plot(
        ax=ax_ref_map,
        column=f'CO2_capita_{planning_horizon}',
        cmap="OrRd",
        linewidth=0,
        legend=False,
        vmax=6,
        vmin=0,
    )
    ax_ref_map.set_title(f"{planning_horizon}", fontsize=20)
    ax_ref_map.axis("off") 
cbar_ax_ref = fig.add_axes([0.08, 0.22, 0.35, 0.01])  # [left, bottom, width, height]
cbar_ref = mpl.colorbar.ColorbarBase(
    cbar_ax_ref,
    cmap=cmap,
    norm=norm,
    orientation="horizontal",
)
cbar_ref.set_label("Mean CO2 Emissions [Tons/Capita]", fontsize=18) 
cbar_ref.ax.tick_params(labelsize=18)   
for idx, planning_horizon in enumerate(planning_horizons):
    ax_suff_map = fig.add_subplot(gs[4, 1], projection=ccrs.EqualEarth())
    ax_suff_map.set_position([
        0.55 + idx * 0.12,  # Adjust horizontal spacing for Sufficiency maps
        0.22,               # Fixed vertical position for all Sufficiency maps
        0.12,              # Width of each map
        0.15,              # Height of each map
    ])
    regions_suff.plot(
        ax=ax_suff_map,
        column=f'CO2_capita_{planning_horizon}',
        cmap="OrRd",
        linewidth=0,
        legend=False,
        vmax=6,
        vmin=0,
    )
    ax_suff_map.set_title(f"{planning_horizon}", fontsize=20)
    ax_suff_map.axis("off")
cbar_ax_suff = fig.add_axes([0.55, 0.22, 0.35, 0.01])  # [left, bottom, width, height]
cbar_suff = mpl.colorbar.ColorbarBase(
    cbar_ax_suff,
    cmap=cmap,
    norm=norm,
    orientation="horizontal",
)
cbar_suff.set_label("Mean CO2 Emissions [Tons/Capita]", fontsize=18)
cbar_suff.ax.tick_params(labelsize=18)

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
        avg_price_ref = prices_ref.sum(axis=1).sum() / 8760 / 33
        avg_price_suff = prices_suff.sum(axis=1).sum() / 8760 / 33

        # Append to respective dictionaries
        prices_ref_dict[carrier].append(avg_price_ref)
        prices_suff_dict[carrier].append(avg_price_suff)

planning_horizons_str = [str(ph) for ph in planning_horizons]
# Plot Reference prices
carrier_name_map = {
    "AC": "Electricity",
    "H2": "Hydrogen",
    "urban central heat": "District Heating",
}
carrier_colors = {
    "AC": "#110d63",
    "H2": "#bf13a0",
    "urban central heat": "#e8beac",
    # Add more carriers and their colors as needed
}
marker_styles = ['o', 's', 'v']
marker_size = 10  # Set marker size
ax_ref_price = fig.add_subplot(gs[5, 0])  # Reference column
ax_suff_price = fig.add_subplot(gs[5, 1])  # Sufficiency column

# Positioning the plots within the grid
ax_ref_price.set_position([0.1, 0.02, 0.35, 0.15])
ax_suff_price.set_position([0.55, 0.02, 0.35, 0.15])

# Plot Reference prices
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

ax_ref_price.set_ylabel("Average Price [EUR/MWh]", fontsize=20)
ax_ref_price.legend(fontsize=18,ncol=2)
ax_ref_price.grid(True)
ax_ref_price.set_ylim(0, 100)
ax_ref_price.tick_params(axis='x', labelsize=20)
ax_ref_price.tick_params(axis='y', labelsize=20)

# Plot Sufficiency prices
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

ax_suff_price.set_ylabel("Average Price [EUR/MWh]", fontsize=20)
ax_suff_price.legend(fontsize=18, ncol=2)
ax_suff_price.grid(True)
ax_suff_price.set_ylim(0, 100)
ax_suff_price.tick_params(axis='x', labelsize=20)
ax_suff_price.tick_params(axis='y', labelsize=20)
plt.show()
