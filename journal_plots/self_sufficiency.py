#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 12 10:58:55 2024

@author: umair
"""

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs

regions = gpd.read_file("../resources/ref/regions_onshore_base_s_33.geojson").set_index("name")

bau_ss = pd.read_excel("../results/ref/htmls/ChartData_EU.xlsx", sheet_name="Chart 7", index_col=0)
new_index = bau_ss.iloc[1]
bau_ss.columns = new_index
bau_ss = bau_ss.drop(bau_ss.index[:2])
bau_ss = bau_ss.apply(pd.to_numeric, errors='coerce').fillna(0)
bau_gas = bau_ss["Natural gas"]
bau_pet = bau_ss["Petroleum"]

regions_bau = regions.copy()
bau_gas_df = pd.DataFrame({
    '2020': bau_gas.loc["2020"],
    '2030': bau_gas.loc["2030"],
    '2040': bau_gas.loc["2040"],
    '2050': bau_gas.loc["2050"]
}, index=regions_bau.index)

# Assign the new columns to regions_bau
regions_bau[['2020', '2030', '2040', '2050']] = bau_gas_df

ncdr_ss = pd.read_excel("../results/suff/htmls/ChartData_EU.xlsx", sheet_name="Chart 7", index_col=0)
new_index = ncdr_ss.iloc[1]
ncdr_ss.columns = new_index
ncdr_ss = ncdr_ss.drop(ncdr_ss.index[:2])
ncdr_ss = ncdr_ss.apply(pd.to_numeric, errors='coerce').fillna(0)
ncdr_gas = ncdr_ss["Natural gas"]
ncdr_pet = ncdr_ss["Petroleum"]

regions_ncdr = regions.copy()
ncdr_gas_df = pd.DataFrame({
    '2020': bau_gas.loc["2020"],
    '2030': ncdr_gas.loc["2030"],
    '2040': ncdr_gas.loc["2040"],
    '2050': ncdr_gas.loc["2050"]
}, index=regions_ncdr.index)

# Assign the new columns to regions_bau
regions_ncdr[['2020', '2030', '2040', '2050']] = ncdr_gas_df

fig, axes = plt.subplots(nrows=2, ncols=4, figsize=(15, 10), subplot_kw={"projection": ccrs.EqualEarth()}, constrained_layout=True)
plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.15, wspace=0.1, hspace=0.3)

years = ['2020', '2030', '2040', '2050']
cmap = "RdYlGn"
vmin = 0
vmax = 100

# Plot regions_bau in the first row
for i, (ax, year) in enumerate(zip(axes[0], years)):
    regions_bau.plot(
        ax=ax,
        column=year,
        cmap=cmap,
        linewidths=0,
        legend=False,
        vmin=vmin,
        vmax=vmax,
    )
    if year == '2020':
        ax.set_title(f'{year}', fontsize=15)  # Just the year for 2020
    else:
        ax.set_title(f'Ref-{year}', fontsize=15)
    ax.gridlines(draw_labels=False,linewidth=0.2, color='grey')

# Plot regions_ncdr in the second row
for i, (ax, year) in enumerate(zip(axes[1], years)):
    regions_ncdr.plot(
        ax=ax,
        column=year,
        cmap=cmap,
        linewidths=0,
        legend=False,
        vmin=vmin,
        vmax=vmax,
    )
    if year == '2020':
        ax.set_title(f'{year}', fontsize=15)  # Just the year for 2020
    else:
        ax.set_title(f'Suff-{year}', fontsize=15)
    ax.gridlines(draw_labels=False,linewidth=0.2, color='grey')
    

# Add a common colorbar for all plots
sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
sm._A = []
cbar = fig.colorbar(sm, ax=axes, orientation="vertical", shrink=1, pad=0.02)
cbar.set_label("Self-Sufficiency Level [Gas] [%]", fontsize=15)
plt.rcParams.update({'font.size': 15})


#%%
bau_gas.loc['2020'] = ncdr_gas.loc['2020']
plt.figure(figsize=(15, 10))

# Plot the data from bau_gas
plt.plot(bau_gas.index, bau_gas.values, label='Reference', color='red', linestyle='--', marker='o',linewidth=4, markersize=12)

# Plot the data from ncdr_gas
plt.plot(ncdr_gas.index, ncdr_gas.values, label='Sufficiency', color='green', linestyle='--', marker='s', linewidth=4, markersize=12)

# plt.plot(bau_pet.index, bau_pet.values, label='BAU [Oil]', color='red', linestyle='--', marker='s',linewidth=4, markersize=12)

# # Plot the data from ncdr_gas
# plt.plot(ncdr_pet.index, ncdr_pet.values, label='Sufficeincy [Oil]', color='green', linestyle='--', marker='s', linewidth=4, markersize=12)

# Adding titles and labels
# plt.title('Natural Gas Values Comparison')
# plt.xlabel('Year')
plt.ylabel('Self-Sufficiency Level [Gas] [%]')
plt.legend()

# Display the plot
plt.grid(True)
plt.rcParams.update({'font.size': 15})
plt.show()

#%%

