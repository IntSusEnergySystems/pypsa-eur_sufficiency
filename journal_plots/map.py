#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  8 11:28:33 2024

@author: umair
"""

import logging
import pypsa
import yaml
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import sys
import os
import geopandas as gpd
from matplotlib.lines import Line2D
logger = logging.getLogger(__name__)
current_script_dir = os.path.dirname(os.path.abspath(__file__))
scripts_path = os.path.join(current_script_dir, "../scripts/")
sys.path.append(scripts_path)
from pypsa.plot import add_legend_circles, add_legend_lines, add_legend_patches

preferred_order = pd.Index(
    [
        "transmission lines",
        "hydroelectricity",
        "hydro reservoir",
        "run of river",
        "pumped hydro storage",
        "solid biomass",
        "biogas",
        "onshore wind",
        "offshore wind",
        "offshore wind (AC)",
        "offshore wind (DC)",
        "solar PV",
        "solar thermal",
        "solar rooftop",
        "solar",
        "building retrofitting",
        "ground heat pump",
        "air heat pump",
        "heat pump",
        "resistive heater",
        "power-to-heat",
        "gas-to-power/heat",
        "CHP",
        "OCGT",
        "gas boiler",
        "gas",
        "natural gas",
        "methanation",
        "ammonia",
        "hydrogen storage",
        "power-to-gas",
        "power-to-liquid",
        "battery storage",
        "hot water storage",
        "CO2 sequestration",
    ]
)

def rename_techs(label: str) -> str:
    """
    Rename technology labels for better readability.

    Removes some prefixes and renames if certain conditions defined in function body are met.

    Parameters
    ----------
    label: str
        Technology label to be renamed

    Returns
    -------
    str
        Renamed label
    """
    prefix_to_remove = [
        "residential ",
        "services ",
        "urban ",
        "rural ",
        "central ",
        "decentral ",
    ]

    rename_if_contains = [
        "CHP",
        "gas boiler",
        "biogas",
        "solar thermal",
        "air heat pump",
        "ground heat pump",
        "resistive heater",
        "Fischer-Tropsch",
    ]

    rename_if_contains_dict = {
        "water tanks": "hot water storage",
        "retrofitting": "building retrofitting",
        # "H2 Electrolysis": "hydrogen storage",
        # "H2 Fuel Cell": "hydrogen storage",
        # "H2 pipeline": "hydrogen storage",
        "battery": "battery storage",
        "H2 for industry": "H2 for industry",
        "land transport fuel cell": "land transport fuel cell",
        "land transport oil": "land transport oil",
        "oil shipping": "shipping oil",
        # "CC": "CC"
    }

    rename = {
        "solar": "solar PV",
        "Sabatier": "methanation",
        "offwind": "offshore wind",
        "offwind-ac": "offshore wind (AC)",
        "offwind-dc": "offshore wind (DC)",
        "offwind-float": "offshore wind (Float)",
        "onwind": "onshore wind",
        "ror": "hydroelectricity",
        "hydro": "hydroelectricity",
        "PHS": "hydroelectricity",
        "NH3": "ammonia",
        "co2 Store": "DAC",
        "co2 stored": "CO2 sequestration",
        "AC": "transmission lines",
        "DC": "transmission lines",
        "B2B": "transmission lines",
    }

    for ptr in prefix_to_remove:
        if label[: len(ptr)] == ptr:
            label = label[len(ptr) :]

    for rif in rename_if_contains:
        if rif in label:
            label = rif

    for old, new in rename_if_contains_dict.items():
        if old in label:
            label = new

    for old, new in rename.items():
        if old == label:
            label = new
    return label

def assign_location(n: pypsa.Network) -> None:
    for c in n.iterate_components(n.one_port_components):
        c.df["location"] = c.df.bus.map(n.buses.location)

    for c in n.iterate_components(n.branch_components):
        c_bus_cols = c.df.filter(regex="^bus")
        locs = c_bus_cols.apply(lambda c: c.map(n.buses.location)).sort_index(axis=1)
        # Use first location that is not "EU"; take "EU" if nothing else available
        c.df["location"] = locs.apply(
            lambda row: next(
                (loc for loc in row.dropna() if loc != "EU"),
                "EU",
            ),
            axis=1,
        )
        


planning_horizons = [2030, 2040, 2050]
with open("../config/plotting.default.yaml") as file:
    config = yaml.safe_load(file)
    
def rename_techs_tyndp(tech):
    tech = rename_techs(tech)
    if "heat pump" in tech or "resistive heater" in tech:
        return "power-to-heat"
    elif tech in ["H2 Electrolysis", "methanation", 'methanolisation',"helmeth", "H2 liquefaction"]:
        return "power-to-gas"
    elif "H2 pipeline" in tech:
        return "H2 pipeline"
    elif tech in ["H2 Store", "H2 storage"]:
        return "hydrogen storage"
    elif tech in ["OCGT", "CHP", "gas boiler", "H2 Fuel Cell"]:
        return "gas-to-power/heat"
    elif "solar" in tech:
        return "solar"
    elif tech == "Fischer-Tropsch":
        return "power-to-liquid"
    elif "offshore wind" in tech:
        return "offshore wind"
    elif tech in ["CO2 sequestration", "co2", "SMR CC", "process emissions CC", "solid biomass for industry CC", "gas for industry CC"]:
         return "CCS"
    elif tech in ["biomass", "biomass boiler", "solid biomass", "solid biomass for industry"]:
         return "biomass"
    elif "Li ion" in tech:
        return "battery storage"
    elif "BEV charger" in tech:
        return "V2G"
    elif "load" in tech:
        return "load shedding"
    # elif tech == "oil" or tech == "gas":
    #      return "fossil oil and gas"
    elif tech == "coal" or tech == "lignite":
          return "coal"
    
    else:
        return tech
 
replacement_dict = {
    'CCGT': 'gas-to-power/heat',
    'BioSNG': 'biomass techs',
    'biogas': 'biomass techs',
    'co2 sequestered': 'CCS',
    'hydrogen storage': 'hydrogen techs',
    'H2 pipeline': 'hydrogen techs',
    'H2 turbine': 'hydrogen techs',
    'Haber-Bosch': 'ammonia techs',
    'SMR': 'hydrogen techs',
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
    'uranium': 'nuclear',
    'water pits': 'thermal storage',
    'battery charger': 'battery',
    'home battery charger': 'battery',
    'home battery': 'battery'
}

tech_colors = config["plotting"]["tech_colors"]
colors = tech_colors 
colors["fossil oil and gas"] = colors["oil"]
colors["hydrogen storage"] = colors["H2 Store"]
colors["load shedding"] = 'black'
colors["gas-to-power/heat"] = 'darkred'
colors["biomass techs"] = "#baa741"
colors["process emissions CC"] = "#4f1745"
colors["hydrogen techs"] = "slateblue"
colors["ammonia techs"] = "#46caf0"
colors["gas pipeline/storage"] = "#4f1745"
colors["thermal storage"] = "#f3afa3"
colors["hydro"] = "#298c81"
colors["oil techs/storage"] = "#c9c9c9"
colors["gas-to-power/heat"] = "chocolate"

components=["links", "stores", "storage_units", "generators"]
bus_size_factor=5.7e11
transmission=True
with_legend=True
LL = "vopt"
costs_dict = {}
for planning_horizon in planning_horizons:
 n=pypsa.Network(f"../results/ref/networks/base_s_33___{planning_horizon}.nc")
 assign_location(n)
 # Drop non-electric buses so they don't clutter the plot
 n.buses.drop(n.buses.index[n.buses.carrier != "AC"], inplace=True)

 costs = pd.DataFrame(index=n.buses.index)

 for comp in components:
     df_c = getattr(n, comp)

     if df_c.empty:
         continue

     df_c["nice_group"] = df_c.carrier.map(rename_techs_tyndp)

     attr = "e_nom_opt" if comp == "stores" else "p_nom_opt"

     costs_c = (
         (df_c.capital_cost * df_c[attr])
         .groupby([df_c.location, df_c.nice_group])
         .sum()
         .unstack()
         .fillna(0.0)
     )
     costs = pd.concat([costs, costs_c], axis=1)
     

     #logger.debug(f"{comp}, {costs}")

 costs = costs.groupby(costs.columns, axis=1).sum()
 #del costs["CCS"]

 costs.drop(list(costs.columns[(costs == 0.0).all()]), axis=1, inplace=True)

 new_columns = preferred_order.intersection(costs.columns).append(
     costs.columns.difference(preferred_order)
 )
 costs = costs[new_columns]


 costs = costs.stack()  # .sort_index()

 # hack because impossible to drop buses...
 eu_location = config["plotting"].get(
     "eu_node_location", dict(x=-5.5, y=46)
 )
 n.buses.loc["EU gas", "x"] = eu_location["x"]
 n.buses.loc["EU gas", "y"] = eu_location["y"]

 n.links.drop(
     n.links.index[(n.links.carrier != "DC") & (n.links.carrier != "B2B")],
     inplace=True,
 )

 # drop non-bus
 to_drop = costs.index.levels[0].symmetric_difference(n.buses.index)
 if len(to_drop) != 0:
     #logger.info(f"Dropping non-buses {to_drop.tolist()}")
     costs.drop(to_drop, level=0, inplace=True, axis=0, errors="ignore")

 # make sure they are removed from index
 costs.index = pd.MultiIndex.from_tuples(costs.index.values)
 costs_dict[planning_horizon] = costs
 combined_df = pd.concat(costs_dict.values())
 combined_costs = combined_df.groupby(combined_df.index).sum()
 multi_index = pd.MultiIndex.from_tuples(combined_costs.index)
 combined_costs.index = multi_index
 combined_costs = combined_costs /3
 combined_costs = combined_costs * 27
 # Update the second level of the MultiIndex
 updated_index = [(i[0], replacement_dict.get(i[1], i[1])) for i in combined_costs.index]
 combined_costs.index = pd.MultiIndex.from_tuples(updated_index, names=combined_costs.index.names)
 terms_to_drop = ['gas', 'oil']
 mask = ~combined_costs.index.get_level_values(1).str.contains('|'.join(terms_to_drop))
 combined_costs = combined_costs[mask]
 cum_costs = combined_costs.groupby(level=0).sum()/1e9
 index_of_cum_costs = cum_costs.index
 value_dict = {
    'AT0 0': 520,
    'BE0 0': 700,
    'BG0 0': 95,
    'CH0 0': 930,
    'CZ0 0': 340,
    'DE0 0': 4300,
    'DK0 0': 400,
    'DK1 0': 400,
    'EE0 0': 34,
    'ES0 0': 1600,
    'ES6 0': 1600,
    'FI1 0': 290,
    'FR0 0': 3300,
    'FR5 0': 3300,
    'GB2 0': 3100,
    'GB3 0': 3100,
    'GR0 0': 276,
    'HR0 0': 70,
    'HU0 0': 207,
    'IE3 0': 522,
    'IT0 0': 2300,
    'IT4 0': 2300,
    'LT0 0': 68,
    'LU0 0': 92,
    'LV0 0': 43,
    'NL0 0': 936,
    'NO1 0': 477,
    'PL0 0': 774,
    'PT0 0': 330,
    'RO0 0': 340,
    'SE1 0': 560,
    'SI0 0': 62,
    'SK0 0': 115,
}
 new_values = [value_dict.get(idx, 0) for idx in cum_costs.index]
 gdp_costs = pd.Series(new_values, index=cum_costs.index)
 gdp_ratio = (cum_costs / (gdp_costs * 27)) * 100
 index_mapping = {
    'DK1 0': 'DK0 0',
    'ES6 0': 'ES0 0',
    'FR5 0': 'FR0 0',
    'GB3 0': 'GB2 0',
    'IT4 0': 'IT0 0'
}
 for target_index, reference_index in index_mapping.items():
    if target_index in gdp_ratio.index and reference_index in gdp_ratio.index:
        gdp_ratio[target_index] = gdp_ratio[reference_index]
        
 regions = gpd.read_file("../resources/ref/regions_onshore_base_s_33.geojson").set_index("name")
 regions['GDP'] = regions.index.map(gdp_ratio)
 threshold = 100e6  # 100 mEUR/a
 carriers = combined_costs.groupby(level=1).sum()
 carriers = carriers.where(carriers > threshold).dropna()
 carriers = list(carriers.index)

 # PDF has minimum width, so set these to zero
 line_lower_threshold = 500.0
 line_upper_threshold = 1e4
 linewidth_factor = 2e3
 ac_color = "rosybrown"
 dc_color = "darkseagreen"

 if LL == "1.0":
      # should be zero
      line_widths = n.lines.s_nom_opt - n.lines.s_nom
      link_widths = n.links.p_nom_opt - n.links.p_nom
      linewidth_factor = 2e3
      line_lower_threshold = 0.0
      title = "added grid"
     

      if transmission:
          line_widths = n.lines.s_nom_opt
          link_widths = n.links.p_nom_opt
          linewidth_factor = 2e3
          line_lower_threshold = 0.0
          title = "current grid"
         
 else:
      line_widths = n.lines.s_nom_opt - n.lines.s_nom_min
      link_widths = n.links.p_nom_opt - n.links.p_nom_min
      linewidth_factor = 2e3
      line_lower_threshold = 0.0
      title = "added grid"

      if transmission:
          line_widths = n.lines.s_nom_opt
          link_widths = n.links.p_nom_opt
          linewidth_factor = 2e3
          line_lower_threshold = 0.0
          title = "total grid"
 map_opts = config["plotting"]["map"]
 regions = regions.to_crs(ccrs.EqualEarth())
 
costs_dict_ncdr = {}
for planning_horizon in planning_horizons:
 n=pypsa.Network(f"../results/suff/networks/base_s_33___{planning_horizon}.nc")
 assign_location(n)
 # Drop non-electric buses so they don't clutter the plot
 n.buses.drop(n.buses.index[n.buses.carrier != "AC"], inplace=True)

 costs_ncdr = pd.DataFrame(index=n.buses.index)

 for comp in components:
     df_c = getattr(n, comp)

     if df_c.empty:
         continue

     df_c["nice_group"] = df_c.carrier.map(rename_techs_tyndp)

     attr = "e_nom_opt" if comp == "stores" else "p_nom_opt"

     costs_c_ncdr = (
         (df_c.capital_cost * df_c[attr])
         .groupby([df_c.location, df_c.nice_group])
         .sum()
         .unstack()
         .fillna(0.0)
     )
     costs_ncdr = pd.concat([costs_ncdr, costs_c_ncdr], axis=1)
     

     #logger.debug(f"{comp}, {costs}")

 costs_ncdr = costs_ncdr.groupby(costs_ncdr.columns, axis=1).sum()
 #del costs["CCS"]

 costs_ncdr.drop(list(costs_ncdr.columns[(costs_ncdr == 0.0).all()]), axis=1, inplace=True)

 new_columns = preferred_order.intersection(costs_ncdr.columns).append(
     costs_ncdr.columns.difference(preferred_order)
 )
 costs_ncdr = costs_ncdr[new_columns]


 costs_ncdr = costs_ncdr.stack()  # .sort_index()

 # hack because impossible to drop buses...
 eu_location = config["plotting"].get(
     "eu_node_location", dict(x=-5.5, y=46)
 )
 n.buses.loc["EU gas", "x"] = eu_location["x"]
 n.buses.loc["EU gas", "y"] = eu_location["y"]

 n.links.drop(
     n.links.index[(n.links.carrier != "DC") & (n.links.carrier != "B2B")],
     inplace=True,
 )

 # drop non-bus
 to_drop = costs_ncdr.index.levels[0].symmetric_difference(n.buses.index)
 if len(to_drop) != 0:
     #logger.info(f"Dropping non-buses {to_drop.tolist()}")
     costs_ncdr.drop(to_drop, level=0, inplace=True, axis=0, errors="ignore")

 # make sure they are removed from index
 costs_ncdr.index = pd.MultiIndex.from_tuples(costs_ncdr.index.values)
 costs_dict_ncdr[planning_horizon] = costs_ncdr
 combined_df_ncdr = pd.concat(costs_dict_ncdr.values())
 combined_costs_ncdr = combined_df_ncdr.groupby(combined_df_ncdr.index).sum()
 multi_index = pd.MultiIndex.from_tuples(combined_costs_ncdr.index)
 combined_costs_ncdr.index = multi_index
 combined_costs_ncdr = combined_costs_ncdr /3
 combined_costs_ncdr = combined_costs_ncdr * 27
 # Update the second level of the MultiIndex
 updated_index = [(i[0], replacement_dict.get(i[1], i[1])) for i in combined_costs_ncdr.index]
 combined_costs_ncdr.index = pd.MultiIndex.from_tuples(updated_index, names=combined_costs_ncdr.index.names)
 terms_to_drop = ['gas', 'oil']
 mask = ~combined_costs_ncdr.index.get_level_values(1).str.contains('|'.join(terms_to_drop))
 combined_costs_ncdr = combined_costs_ncdr[mask]
 cum_costs_ncdr = combined_costs_ncdr.groupby(level=0).sum()/1e9
 index_of_cum_costs_ncdr = cum_costs_ncdr.index
 value_dict = {
    'AT0 0': 520,
    'BE0 0': 700,
    'BG0 0': 95,
    'CH0 0': 930,
    'CZ0 0': 340,
    'DE0 0': 4300,
    'DK0 0': 400,
    'DK1 0': 400,
    'EE0 0': 34,
    'ES0 0': 1600,
    'ES6 0': 1600,
    'FI1 0': 290,
    'FR0 0': 3300,
    'FR5 0': 3300,
    'GB2 0': 3100,
    'GB3 0': 3100,
    'GR0 0': 276,
    'HR0 0': 70,
    'HU0 0': 207,
    'IE3 0': 522,
    'IT0 0': 2300,
    'IT4 0': 2300,
    'LT0 0': 68,
    'LU0 0': 92,
    'LV0 0': 43,
    'NL0 0': 936,
    'NO1 0': 477,
    'PL0 0': 774,
    'PT0 0': 330,
    'RO0 0': 340,
    'SE1 0': 560,
    'SI0 0': 62,
    'SK0 0': 115,
}
 new_values = [value_dict.get(idx, 0) for idx in cum_costs_ncdr.index]
 gdp_costs = pd.Series(new_values, index=cum_costs_ncdr.index)
 gdp_ratio_ncdr = (cum_costs_ncdr / (gdp_costs * 27)) * 100
 index_mapping = {
    'DK1 0': 'DK0 0',
    'ES6 0': 'ES0 0',
    'FR5 0': 'FR0 0',
    'GB3 0': 'GB2 0',
    'IT4 0': 'IT0 0'
}
 for target_index, reference_index in index_mapping.items():
    if target_index in gdp_ratio_ncdr.index and reference_index in gdp_ratio_ncdr.index:
        gdp_ratio_ncdr[target_index] = gdp_ratio_ncdr[reference_index]
        
 regions_ncdr = gpd.read_file("../resources/suff/regions_onshore_base_s_33.geojson").set_index("name")
 regions_ncdr['GDP'] = regions_ncdr.index.map(gdp_ratio_ncdr)
 threshold = 100e6  # 100 mEUR/a
 carriers = combined_costs_ncdr.groupby(level=1).sum()
 carriers = carriers.where(carriers > threshold).dropna()
 carriers = list(carriers.index)

 # PDF has minimum width, so set these to zero
 line_lower_threshold = 500.0
 line_upper_threshold = 1e4
 linewidth_factor = 2e3
 ac_color = "rosybrown"
 dc_color = "darkseagreen"

 if LL == "1.0":
      # should be zero
      line_widths_ncdr = n.lines.s_nom_opt - n.lines.s_nom
      link_widths_ncdr = n.links.p_nom_opt - n.links.p_nom
      linewidth_factor = 2e3
      line_lower_threshold = 0.0
      title = "added grid"
     

      if transmission:
          line_widths_ncdr = n.lines.s_nom_opt
          link_widths_ncdr = n.links.p_nom_opt
          linewidth_factor = 2e3
          line_lower_threshold = 0.0
          title = "current grid"
         
 else:
      line_widths_ncdr = n.lines.s_nom_opt - n.lines.s_nom_min
      link_widths_ncdr = n.links.p_nom_opt - n.links.p_nom_min
      linewidth_factor = 2e3
      line_lower_threshold = 0.0
      title = "added grid"

      if transmission:
          line_widths_ncdr = n.lines.s_nom_opt
          link_widths_ncdr = n.links.p_nom_opt
          linewidth_factor = 2e3
          line_lower_threshold = 0.0
          title = "total grid"
 map_opts = config["plotting"]["map"]
 regions_ncdr = regions_ncdr.to_crs(ccrs.EqualEarth())
 fig, axes = plt.subplots(nrows=1, ncols=2,subplot_kw={"projection": ccrs.EqualEarth()},constrained_layout=False)
 fig.set_size_inches(20, 10)
 plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.15, wspace=0.1)
 n.plot(
      bus_sizes=combined_costs / bus_size_factor,
      bus_colors=tech_colors,
      line_colors=ac_color,
      link_colors=dc_color,
      line_widths=line_widths / linewidth_factor,
      link_widths=link_widths / linewidth_factor,
      ax=axes[0],
      **map_opts,
  )
 regions.plot(
        ax=axes[0],
        column="GDP",
        cmap="OrRd",
        linewidths=0,
        legend=False,
        vmax=6,
        vmin=0,
        legend_kwds={
            "label": "GDP Percentage / year",
            "shrink": 0.6,
            # "extend": "max",
        },
    )
 n.plot(
      bus_sizes=combined_costs_ncdr / bus_size_factor,
      bus_colors=tech_colors,
      line_colors=ac_color,
      link_colors=dc_color,
      line_widths=line_widths_ncdr / linewidth_factor,
      link_widths=link_widths_ncdr / linewidth_factor,
      ax=axes[1],
      **map_opts,
  )
 regions_ncdr.plot(
        ax=axes[1],
        column="GDP",
        cmap="OrRd",
        linewidths=0,
        legend=False,
        vmax=6,
        vmin=0,
        legend_kwds={
            "label": "GDP Percentage / year",
            "shrink": 0.6,
            # "extend": "max",
        },
    )
 #sizes = [20, 10, 5]
 sizes = [1200, 600, 300]
 labels = [f"{s} bEUR" for s in sizes]
 sizes = [s / bus_size_factor * 1e9 for s in sizes]

 legend_kw = dict(
         loc="upper left",
         bbox_to_anchor=(0, 1),
        labelspacing=1.5,
        frameon=False,
        fontsize=15,
        handletextpad=1,
        title="Cumulative investment costs",
    )

 add_legend_circles(
        axes[0],
        sizes,
        labels,
        srid=n.srid,
        patch_kw=dict(facecolor="black"),
        legend_kw=legend_kw,
    )

 sizes = [10, 5]
 labels = [f"{s} GW" for s in sizes]
 scale = 1e3 / linewidth_factor
 sizes = [s * scale for s in sizes]
 legend_kw = dict(
        loc="upper left",
        bbox_to_anchor=(0, 1),
       fontsize=15,
       frameon=False,
       labelspacing=1,
       handletextpad=1,
       title="Transmission lines capacity"
   )

 add_legend_lines(
       axes[1], sizes, labels, patch_kw=dict(color="black"), legend_kw=legend_kw,
   )
 sm = plt.cm.ScalarMappable(cmap="OrRd", norm=plt.Normalize(vmin=0, vmax=6))
 sm._A = []
 cbar = fig.colorbar(sm, ax=axes, orientation="vertical", shrink=0.8, pad=0.02)
 cbar.set_label(r"Cost [% GDP$_{2023}$ / year]", fontsize=15)
 legend_kw = dict(
      bbox_to_anchor=(1, 1),
      frameon=False,
      fontsize=15,
  )
 colors = [tech_colors[c] for c in carriers] + [ac_color, dc_color]
 labels = carriers + ['AC Line', 'DC Line']
 legend_handles = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markersize=15) for color in colors
]
 fig.legend(
    legend_handles,
    labels,
    loc="lower center",            # Position the legend at the bottom center of the figure
    bbox_to_anchor=(0.45, 0.03),    # Centered horizontally and placed below the figure
    ncol=6,                        # Number of columns in the legend
    frameon=False,                 # No frame around the legend
    fontsize=15,
)
 fig.text(0.25, 0.18, '(a) Reference Scenario', ha='center', va='center', fontsize=15)
 fig.text(0.65, 0.18, '(b) Sufficiency Scenario', ha='center', va='center', fontsize=15)
 plt.rcParams.update({'font.size': 15}) 
 # if with_legend:
 #        colors = [tech_colors[c] for c in carriers] + [ac_color, dc_color]
 #        labels = carriers + ["HVAC line", "HVDC link"]

 #        add_legend_patches(
 #            axes,
 #            colors,
 #            labels,
 #            legend_kw=legend_kw,
 #        )
 
 
