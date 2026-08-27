#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  8 19:23:22 2024

@author: umair
"""

import pandas as pd
import matplotlib.pyplot as plt
import yaml
import numpy as np
with open("/home/umair/pypsa-eur/config/plotting.default.yaml") as file:
    config = yaml.safe_load(file)
country = 'EU'

caps_reff = pd.read_csv("/home/umair/28 countries_previous/results/ref/country_csvs/EU_capacities.csv")
caps_reff["tech"] = caps_reff["tech"].replace({
    # "AC Transmission lines": "Transmission lines",
    # "DC Transmission lines": "TTransmission lines",
    # "solar": "solar PV",
    # "transmission lines": "Transmission lines"
})
# caps_reff = caps_reff.groupby("tech", as_index=False)["2020"].sum()
caps_suff = pd.read_csv(f"../results/suff/country_csvs/{country}_capacities.csv")
caps_bau = pd.read_csv(f"../results/ref/country_csvs/{country}_capacities.csv")
caps_reff = caps_reff[['tech', '2020']]
caps_bau = caps_bau[['tech', '2030', '2040', '2050']]
caps_suff = caps_suff[['tech', '2030', '2040', '2050']]
caps_bau = caps_bau[['tech', '2050']]
caps_bau = caps_bau.rename(columns={'2050': 'Ref'})
caps_suff = caps_suff[['tech', '2050']]
caps_suff = caps_suff.rename(columns={'2050': 'Suff'})
combined_df = pd.merge(caps_reff, caps_bau, on='tech', how='outer', suffixes=('_baseline', '_ref'))
combined_df = pd.merge(combined_df, caps_suff, on='tech', how='outer')
combined_df = combined_df.fillna(0)
combined_df = combined_df.set_index('tech')
combined_df = combined_df/1000
combined_df = combined_df.drop("DAC")

caps_ref_st = pd.read_csv("/home/umair/28 countries_previous/results/ref/country_csvs/EU_storage_capacities.csv")
caps_bau_st = pd.read_csv(f"../results/ref/country_csvs/{country}_storage_capacities.csv")
caps_suff_st = pd.read_csv(f"../results/suff/country_csvs/{country}_storage_capacities.csv")
# if "2020" not in caps_bau_st.columns:
#     # create a 2020 column with zeros
#     caps_bau_st["2020"] = 0
caps_reff_st = caps_ref_st[['tech', '2020']]
caps_bau_st = caps_bau_st[['tech', '2030', '2040', '2050']]
caps_suff_st = caps_suff_st[['tech', '2030', '2040', '2050']]
caps_bau_st = caps_bau_st[['tech', '2050']]
caps_bau_st = caps_bau_st.rename(columns={'2050': 'Ref'})
caps_suff_st = caps_suff_st[['tech', '2050']]
caps_suff_st = caps_suff_st.rename(columns={'2050': 'Suff'})
combined_df_st = pd.merge(caps_reff_st, caps_bau_st, on='tech', how='outer', suffixes=('_baseline', '_bau'))
combined_df_st = pd.merge(combined_df_st, caps_suff_st, on='tech', how='outer')
combined_df_st = combined_df_st.fillna(0)
combined_df_st = combined_df_st.set_index('tech')
combined_df_st = combined_df_st/1000
# combined_df_st = combined_df_st.drop("H2")

combined_total_df = pd.concat([combined_df, combined_df_st])
new_entries = {
    'DAC': {'2020':0,'Ref': 20, 'Suff': 0},
    'BECCS': {'2020':0,'Ref': 119, 'Suff': 0},
    'Gas CC': {'2020':0,'Ref': 31, 'Suff': 0}
}

# Convert the dictionary to a DataFrame
new_df = pd.DataFrame(new_entries).T
combined_total_df = pd.concat([combined_total_df, new_df])
combined_total_df = combined_total_df.rename(index={
    "gas pipeline new": "gas pipeline"
})
combined_total_df = combined_total_df.groupby(combined_total_df.index).sum()

tech_colors = config["plotting"]["tech_colors"]
colors = config["plotting"]["tech_colors"]
colors["Thermal Energy Storage"] = '#f3afa3'
colors["Transmission lines"] = 'green'
colors["Grid-scale battery"] = 'lightgreen'
colors["home battery"] = 'blue'
colors["H2 pipeline"] = 'slateblue'
colors["gas pipeline"] = 'grey'
colors["BECCS"] = '#889717'
colors["Gas CC"] = '#f18959'

groups = [
    ["solar","onshore wind", "offshore wind"],
    ["nuclear", "CCGT", "hydroelectricity"],
    ["power-to-gas", "power-to-heat", "power-to-liquid"],
    ["transmission lines", "H2 & gas pipelines", "CO2 pipeline"],
    ["H2 Store","Grid-scale battery", "Thermal Energy Storage"],
    ["DAC","BECCS", "Gas CC"],
    
]


y_labels = [
    "Capacity for VRE Technologies [GW]",
    "Capacity for Disptachable Technologies [GW]",
    "Capacity for Conversion Technologies [GW]",
    "Capacity for Grid Infrastructure [GW]",
    "Capacity for Storage Technologies [GWh]",
    "Capacity for CC Technologies [Mtons/year]",
]
y_limits = [
    (0, 2700),  # For Renewable Energy
    (0, 300),  # For Conventional Energy
    (0, 1000),   # For Energy Conversion
    (0, 1000),  # For Grid Infrastructure
    (0, 27000),  # For Grid Infrastructure
    (0, 150),  # For Grid Infrastructure
]
fig, axes = plt.subplots(2, 3, figsize=(15, 11))

# Flatten axes array for easier indexing
axes = axes.flatten()

# Iterate over each group and corresponding subplot axis
for i, group in enumerate(groups):
    # Filter the combined_total_df to get the data for the current group
    group_df = combined_total_df.loc[group]
    
    # Plot a bar plot for the group
    group_df.T.plot(kind='bar', ax=axes[i], color=[colors.get(tech, 'grey') for tech in group_df.index], width=0.6)
    
    # Set the y-axis label for each subplot
    axes[i].set_ylabel(y_labels[i], fontsize=15)
    
    # Set y-axis limits
    axes[i].set_ylim(y_limits[i])
    
    # Set tick parameters for better readability
    axes[i].tick_params(axis='both', which='major', labelsize=15)
    
    # Add grid lines
    axes[i].grid(True, which='both', axis='both', linestyle='--', linewidth=0.3)
    
    # Adjust the legend
    legend = axes[i].get_legend()
    legend.set_title(None)
    plt.setp(legend.get_texts(), fontsize=15)

plt.tight_layout()
plt.show()

