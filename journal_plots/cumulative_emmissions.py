#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Aug  3 17:16:45 2024

@author: umair
"""

import pandas as pd
import matplotlib.pyplot as plt


# Load configuration data
config = pd.read_excel("../SEPIA/SEPIA_config.xlsx", sheet_name="NODES", index_col=0)
config = config[config['Type'] == 'GHG_SECTORS']

code_to_label = config['Label'].to_dict()

# Load and preprocess data
bau = pd.read_csv("../results/ref/country_csvs/ghg_sector_cum_EU.csv", index_col=0)
ncdr = pd.read_csv("../results/suff/country_csvs/ghg_sector_cum_EU.csv", index_col=0)

# Rename columns and preprocess bau
bau.rename(columns=code_to_label, inplace=True)
bau['Industry'] = bau[['Other energy industry', 'Industrial processes', 'Fuel usage - industry']].sum(axis=1)
bau = bau.drop(columns=['Other energy industry', 'Industrial processes', 'Fuel usage - industry'])
bau = bau.rename(columns={"Fuel combustion - agriculture": "Agriculture", "Fuel combustion - transport": "Transport", "Fuel combustion - aviation bunkers": "Aviation bunkers", "DAC":"DACCS","Fuel combustion - maritime bunkers":"Maritime bunkers","biogas": "Biogas","Fuel combustion – residential and tertiary":"Residential and tertiary sectors"})
bau["Biomass"] = bau["biomass to liquid"] + bau["Biomass"]
bau = bau.drop(columns=["biomass to liquid"])
bau = bau.loc[:, (bau != 0).any(axis=0)]
bau['Total'] = bau.sum(axis=1)
bau_cumulative = bau.drop(columns='Total').cumsum() / 1000

# Rename columns and preprocess ncdr
ncdr.rename(columns=code_to_label, inplace=True)
ncdr['Industry'] =ncdr[['Other energy industry', 'Industrial processes', 'Fuel usage - industry']].sum(axis=1)
ncdr = ncdr.drop(columns=['Other energy industry', 'Industrial processes', 'Fuel usage - industry'])
ncdr = ncdr.rename(columns={"Fuel combustion - agriculture": "Agriculture", "Fuel combustion - transport": "Transport", "Fuel combustion - aviation bunkers": "Aviation bunkers", "DAC":"DACCS","Fuel combustion - maritime bunkers":"Maritime bunkers","biogas": "Biogas","Fuel combustion – residential and tertiary":"Residential and tertiary sectors"})
ncdr["Biomass"] = ncdr["biomass to liquid"] + ncdr["Biomass"]
ncdr = ncdr.drop(columns=["biomass to liquid"])
ncdr = ncdr.loc[:, (ncdr != 0).any(axis=0)]
ncdr['Total'] = ncdr.sum(axis=1)
ncdr_cumulative = ncdr.drop(columns='Total').cumsum() / 1000

# Extract colors for the plot
# colors = [config.set_index('Label').loc[label, 'Color'] for label in bau.columns if label in config['Label'].values]
colors = {
    "Agriculture": "#008556",
    "Industry": "#feda47",
    "Transport": "#a26643",
    "Residential and tertiary sectors": "#d60a51",
    "Maritime bunkers": "#f18959",
    "Aviation bunkers": "#ff4d00",
    "BECCS": "#889717",
    "Biogas": "#dfeac2",
    "Biomass": "green",
    "DACCS": "#b1d1fc",
    "Heat and power production ": "#75519c",
    "Land use and forestry": "#befdb7",
    
    
}
preferred_order = ['Maritime bunkers', 'Agriculture', 'Transport', 'Residential and tertiary sectors','Heat and power production ','Aviation bunkers', 'Industry','Biogas','Biomass','BECCS','DACCS','Land use and forestry']
actual_order_bau = [col for col in preferred_order if col in bau_cumulative.columns]
actual_order_ncdr = [col for col in preferred_order if col in ncdr_cumulative.columns]
bau_cumulative = bau_cumulative[actual_order_bau]
ncdr_cumulative = ncdr_cumulative[actual_order_ncdr]
# Create subplots (2x2 grid)
fig, axs = plt.subplots(nrows=2, ncols=2, figsize=(15, 10), gridspec_kw={'width_ratios': [1.6, 1]})
# Plot the area chart for bau on the first subplot (axs[0, 0])
bau_cumulative.plot(kind='area', stacked=True, alpha=0.5, color=colors, ax=axs[0, 0])
bau_cumulative['Total'] = bau_cumulative.sum(axis=1)
bau_cumulative['Total'].plot(kind='line', color='black', linewidth=2, ax=axs[0, 0])
axs[0, 0].set_xticks([2020, 2030, 2040, 2050])
axs[0, 0].set_xlim(2020, 2050)
axs[0, 0].set_ylim(-40, 60)
axs[0, 0].set_ylabel('Cumulative Emissions [GtCO2 eq]', fontsize=15)
axs[0, 0].grid(True)
axs[0, 0].tick_params(axis='both', labelsize=15)
axs[0, 0].get_legend().remove()

# Plot the bar chart for bau on the second subplot (axs[0, 1])
values_2050_bau = bau_cumulative.loc[2050]
# colors_2050_bau = [config.set_index('Label').loc[label, 'Color'] for label in values_2050_bau.index if label in config['Label'].values]
bar_colors_bau = [colors.get(label, "#000000") for label in values_2050_bau.index]
bars_bau = axs[0, 1].bar(values_2050_bau.index, values_2050_bau,alpha=0.5, color=bar_colors_bau)
# axs[0, 1].set_ylabel('Cumulative Emissions [GtCO2 eq]', fontsize=15)
axs[0, 1].tick_params(axis='x', rotation=90)
axs[0, 1].grid(True)
axs[0, 1].set_xticks([])
axs[0, 1].set_ylim(-15, 35)
axs[0, 1].tick_params(axis='both', labelsize=15)
for bar in bars_bau:
    height = bar.get_height()
    axs[0, 1].text(bar.get_x() + bar.get_width() / 2, height, f'{height:.1f}', 
                    ha='center', va='bottom', fontsize=12, color='black')

# Plot the area chart for ncdr on the third subplot (axs[1, 0])
# colors_ncdr = [config.set_index('Label').loc[label, 'Color'] for label in ncdr.columns if label in config['Label'].values]
ncdr_cumulative.plot(kind='area', stacked=True, alpha=0.5, color=colors, ax=axs[1, 0])
ncdr_cumulative['Total'] = ncdr_cumulative.sum(axis=1)
ncdr_cumulative['Total'].plot(kind='line', color='black', linewidth=2, ax=axs[1, 0])
axs[1, 0].set_xticks([2020, 2030, 2040, 2050])
axs[1, 0].set_xlim(2020, 2050)
axs[1, 0].set_ylim(-40, 60)
axs[1, 0].set_ylabel('Cumulative Emissions [GtCO2 eq]', fontsize=15)
axs[1, 0].grid(True)
axs[1, 0].tick_params(axis='both', labelsize=15)
axs[1, 0].get_legend().remove()

# Plot the bar chart for ncdr on the fourth subplot (axs[1, 1])
values_2050_ncdr = ncdr_cumulative.loc[2050]
bar_colors_ncdr = [colors.get(label, "#000000") for label in values_2050_ncdr.index]
# colors_2050_ncdr = [config.set_index('Label').loc[label, 'Color'] for label in values_2050_ncdr.index if label in config['Label'].values]
bars_ncdr = axs[1, 1].bar(values_2050_ncdr.index, values_2050_ncdr,alpha=0.5, color=bar_colors_ncdr)
# axs[1, 1].set_ylabel('Cumulative Emissions [GtCO2 eq]', fontsize=15)
axs[1, 1].tick_params(axis='x', rotation=90)
axs[1, 1].grid(True)
axs[1, 1].set_xticks([])
axs[1, 1].set_ylim(-15, 35)
axs[1, 1].tick_params(axis='both', labelsize=15)
for bar in bars_ncdr:
    height = bar.get_height()
    axs[1, 1].text(bar.get_x() + bar.get_width() / 2, height, f'{height:.1f}', 
                    ha='center', va='bottom', fontsize=12, color='black')

handles, labels = axs[0, 0].get_legend_handles_labels()
# Create a separate axis for the legend
ax_legend = fig.add_axes([0.5, 0.05, 0.8, 0.2], frameon=False)
fig.legend(handles, labels, loc='center', bbox_to_anchor=(0.52, 0.09), ncol=5, fontsize=15, labelspacing=1, handletextpad=1.0)

# Hide the legend axis
ax_legend.axis('off')

axs[0, 0].set_title('(a)   Cumulative CO2 Emissions by Sector in Reference Scenario', fontsize=15)
axs[1, 0].set_title('(b)   Cumulative CO2 Emissions by Sector in Sufficiency Scenario', fontsize=15)
# Adjust layout to fit all plots and the legend
plt.tight_layout(rect=[0, 0.15, 1, 1])  # Adjust the space to fit all plots and the legend

plt.show()
