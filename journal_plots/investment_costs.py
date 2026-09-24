import pandas as pd
import matplotlib.pyplot as plt
import yaml
import numpy as np

with open("../config/plotting.default.yaml") as file:
    config = yaml.safe_load(file)

bau_inv = pd.read_csv("../results/ref/country_csvs/EU_investment costs.csv")
suff_inv =  pd.read_csv("../results/suff/country_csvs/EU_investment costs.csv")

bau_inv = bau_inv[['tech', '2030', '2040', '2050']]
suff_inv = suff_inv[['tech', '2030', '2040', '2050']]


bau_inv['Total'] = bau_inv[['2030', '2040', '2050']].sum(axis=1)
bau_cum_inv = bau_inv[['tech', 'Total']]
bau_cum_inv['Total'] = bau_cum_inv['Total']/3
bau_cum_inv['Total'] = bau_cum_inv['Total'] * 27
bau_cum_inv = bau_cum_inv.rename(columns={'Total': 'Reference'})
bau_inv = bau_inv.drop('Total', axis=1)

suff_inv['Total'] = suff_inv[['2030', '2040', '2050']].sum(axis=1)
suff_cum_inv = suff_inv[['tech', 'Total']]
suff_cum_inv['Total'] = suff_cum_inv['Total']/3
suff_cum_inv['Total'] = suff_cum_inv['Total'] * 27
suff_cum_inv = suff_cum_inv.rename(columns={'Total': 'Sufficiency'})
suff_inv = suff_inv.drop('Total', axis=1)


# Dictionary for tech replacement
replacement_dict = {
    'CCGT': 'gas-to-power/heat',
    'BioSNG': 'biomass techs',
    'biogas': 'biomass techs',
    'Biogas Plants': 'biomass techs',
    'co2 sequestered': 'CCS',
    'H2': 'hydrogen techs/storage',
    'H2 pipeline': 'hydrogen techs/storage',
    'H2 turbine': 'hydrogen techs/storage',
    'Haber-Bosch': 'ammonia techs',
    'SMR': 'hydrogen techs/storage',
    'ammonia': 'ammonia techs',
    'ammonia cracker': 'ammonia techs',
    'biomass': 'biomass techs',
    'biomass to liquid': 'biomass techs',
    'gas pipeline': 'gas pipeline/storage',
    'gas pipeline new': 'gas pipeline/storage',
    'gas storage': 'gas pipeline/storage',
    'hot water storage': 'thermal storage',
    'hydroelectricity': 'hydro',
    'oil boiler': 'oil techs/storage',
    'oil storage': 'oil techs/storage',
    'solid biomass transport': 'biomass techs',
    'uranium': 'nuclear'
}

bau_inv['tech'] = bau_inv['tech'].replace(replacement_dict)
bau_inv = bau_inv.groupby('tech', as_index=False).sum()
suff_inv['tech'] = suff_inv['tech'].replace(replacement_dict)
suff_inv = suff_inv.groupby('tech', as_index=False).sum()
bau_cum_inv['tech'] = bau_cum_inv['tech'].replace(replacement_dict)
bau_cum_inv = bau_cum_inv.groupby('tech', as_index=False).sum()
suff_cum_inv['tech'] = suff_cum_inv['tech'].replace(replacement_dict)
suff_cum_inv = suff_cum_inv.groupby('tech', as_index=False).sum()

colors = config["plotting"]["tech_colors"]
colors["Reference"] = "black"
colors["Sufficiency"] = "black"
colors["biomass techs"] = "#baa741"
colors["process emissions CC"] = "#4f1745"
colors["hydrogen techs/storage"] = "slateblue"
colors["ammonia techs"] = "#46caf0"
colors["gas pipeline/storage"] = "#4f1745"
colors["thermal storage"] = "#f3afa3"
colors["hydro"] = "#298c81"
colors["oil techs/storage"] = "#c9c9c9"
colors["gas-to-power/heat"] = "chocolate"
colors["Fossil Fuel techs"] = colors["Fossil Fuels"]

# Merging cumulative data
cum_data = pd.merge(bau_cum_inv, suff_cum_inv, on='tech', how='outer').set_index('tech').fillna(0).T/1e12
cum_data =  cum_data.sum(axis=1)
combined_df = pd.merge(bau_inv, suff_inv, on='tech', how='outer', suffixes=('_Ref', '_Suff')).set_index('tech').fillna(0).T/1e9
desired_order = ['2030_Ref', '2030_Suff', '2040_Ref', '2040_Suff', '2050_Ref', '2050_Suff']
combined_df = combined_df.loc[desired_order]
# Plotting cumulative investments
fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(16, 10), gridspec_kw={'width_ratios': [0.25, 1]})

cum_data =cum_data.plot(kind='bar', stacked=True, ax=axes[0], legend=False, color=[colors[index] for index in cum_data.index])
axes[0].set_ylabel('Cumulative Investment Costs [Trillion Euros]',fontsize=15)
axes[0].grid(True, which='both', linestyle='--', linewidth=0.3, color='grey')
axes[0].tick_params(axis='y', labelsize=15)
axes[0].tick_params(axis='x', labelsize=15)
for container in cum_data.containers:
    for bar in container:
        height = bar.get_height()
        axes[0].text(
            bar.get_x() + bar.get_width() / 2,
            height,
            f'{height:.1f}',
            ha='center',
            va='bottom',
            fontsize=15,
            color='black'
        )
# Plot combined investments
com=combined_df.plot(kind='bar', stacked=True, ax=axes[1], legend=False,color=[colors.get(x, '#333333') for x in combined_df.columns])
axes[1].set_ylabel('Investment Costs [Billion Euros/year]',fontsize=15)
axes[1].grid(True, which='both', linestyle='--', linewidth=0.3, color='grey')
axes[1].tick_params(axis='y', labelsize=15)
axes[1].tick_params(axis='x', labelsize=15)
axes[1].set_xticks([])
# Customize bar width
for bar in axes[1].patches:
    bar.set_width(0.4) 

x = [-0.05, 0.95, 1.95, 2.95, 3.95, 4.95]
x_labels = ['Ref-2030', 'Suff-2030', 'Ref-2040', 'Suff-2040', 'Ref-2050', 'Suff-2050']
axes[1].set_xticks(x)
axes[1].set_xticklabels(x_labels, rotation=90, ha='center', fontsize=15)

for bar in axes[1].patches:
    bar.set_width(0.4)

# Manually add labels to the top of each stacked bar
for i, patch in enumerate(axes[1].patches):
    # Extract the x and y position of each bar segment
    x = patch.get_x() + patch.get_width() / 2
    height = patch.get_height()
    bottom = patch.get_y()
    
    # Calculate the top of the bar (accumulated height)
    top = bottom + height
    
    # Check if the current patch is the last one in the stack
    if bottom == 0:
        # Find all patches in the same x location
        same_x_patches = [p for p in axes[1].patches if p.get_x() == patch.get_x()]
        # Calculate the total height for the bar
        total_height = sum(p.get_height() for p in same_x_patches)
        
        # Place the label on top of the bar
        axes[1].text(
            x,
            total_height,
            f'{total_height:.1f}',
            ha='center',
            va='bottom',
            fontsize=15,
            color='black'
        )

handles, labels = axes[1].get_legend_handles_labels()
# Create a separate axis for the legend
ax_legend = fig.add_axes([0.5, 0.05, 0.8, 0.2], frameon=False)
fig.legend(handles, labels, loc='center', bbox_to_anchor=(0.5, 0.085), ncol=5, fontsize=13.5, labelspacing=0.8, handletextpad=0.6)

# Hide the legend axis
ax_legend.axis('off')
plt.tight_layout(rect=[0, 0.15, 1, 1]) 
plt.show()



