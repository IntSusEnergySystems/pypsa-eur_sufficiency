#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Apr  5 17:25:11 2026

@author: umair
"""

import pypsa
import pandas as pd
import yaml
import geopandas as gpd

with open("/home/umair/pypsa-eur_master/config/config_suff.yaml") as file:
    config = yaml.safe_load(file)
countries = config["countries"]
planning_horizons = [2030,2040,2050]

def build_filename_ref(planning_horizon):
    prefix=f"/home/umair/pypsa-eur_master/results/ref/networks/"
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
    prefix=f"/home/umair/pypsa-eur_master/results/suff/networks/"
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
regions = gpd.read_file("/home/umair/pypsa-eur_master/resources/ref/regions_onshore_base_s_33.geojson").set_index("name")
regions['country_code'] = regions.index.str[:2]
regions = regions.set_index('country_code')
#%%
curtailment = {}

for planning_horizon in planning_horizons:
    n = loaded_files_ref[planning_horizon]
    m = loaded_files_suff[planning_horizon]
    
    curtailment[planning_horizon] = {}
    
    for country in countries:
        curtailment[planning_horizon][country] = {}

        # REF case
        curtailment[planning_horizon][country]["ref"] = {
            "solar": ((n.generators_t.p_max_pu * n.generators.p_nom_opt) - n.generators_t.p)
                        .filter(like="solar", axis=1)
                        .filter(like=country)
                        .sum(axis=1).sum() / 1e6,

            "onwind": ((n.generators_t.p_max_pu * n.generators.p_nom_opt) - n.generators_t.p)
                        .filter(like="onwind", axis=1)
                        .filter(like=country)
                        .sum(axis=1).sum() / 1e6,

            "offwind": ((n.generators_t.p_max_pu * n.generators.p_nom_opt) - n.generators_t.p)
                        .filter(like="offwind", axis=1)
                        .filter(like=country)
                        .sum(axis=1).sum() / 1e6
        }

        # SUFF case
        curtailment[planning_horizon][country]["suff"] = {
            "solar": ((m.generators_t.p_max_pu * m.generators.p_nom_opt) - m.generators_t.p)
                        .filter(like="solar", axis=1)
                        .filter(like=country)
                        .sum(axis=1).sum() / 1e6,

            "onwind": ((m.generators_t.p_max_pu * m.generators.p_nom_opt) - m.generators_t.p)
                        .filter(like="onwind", axis=1)
                        .filter(like=country)
                        .sum(axis=1).sum() / 1e6,

            "offwind": ((m.generators_t.p_max_pu * m.generators.p_nom_opt) - m.generators_t.p)
                        .filter(like="offwind", axis=1)
                        .filter(like=country)
                        .sum(axis=1).sum() / 1e6
        }
        
#%%
rows = []

for ph in planning_horizons:
    for country in countries:
        for case in ["ref", "suff"]:
            for tech in ["solar", "onwind", "offwind"]:
                
                rows.append({
                    "planning_horizon": ph,
                    "country": country,
                    "case": case,
                    "tech": tech,
                    "curtailment": curtailment[ph][country][case][tech]
                })

df_curtailment = pd.DataFrame(rows)
  
#%%
import matplotlib.pyplot as plt
import matplotlib as mpl
import cartopy.crs as ccrs

techs = ["solar", "onwind", "offwind"]

fig = plt.figure(figsize=(16, 12))
gs = fig.add_gridspec(len(techs), 2)

tech_cmaps = {
    "solar": plt.cm.OrRd,
    "onwind": plt.cm.Blues,
    "offwind": plt.cm.Greens
}

for i, tech in enumerate(techs):

    # 🔵 LEFT COLUMN → REF
    cmap = tech_cmaps[tech]
    tech_ranges = {
    "solar": (0, 30),
    "onwind": (0, 10),
    "offwind": (0, 10)
}
    vmin, vmax = tech_ranges[tech]
    norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)
    ax_main_ref = fig.add_subplot(gs[i, 0])
    ax_main_ref.axis("off")

    for idx, planning_horizon in enumerate(planning_horizons):

        ax = fig.add_axes([
            0.08 + idx * 0.12,     # horizontal spacing
            0.72 - i * 0.35,       # vertical position per tech
            0.25,                  # width
            0.25                   # height
        ], projection=ccrs.EqualEarth())

        ax.set_aspect("auto")

        data = df_curtailment[
            (df_curtailment["planning_horizon"] == planning_horizon) &
            (df_curtailment["case"] == "ref") &
            (df_curtailment["tech"] == tech)
        ]

        plot_df = regions.merge(data, left_index=True, right_on="country")

        plot_df.plot(
            ax=ax,
            column="curtailment",
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            edgecolor="grey",
            linewidth=0.3      
        )

        ax.set_title(f"{planning_horizon}", fontsize=12)
        ax.axis("off")
    
    ax_main_suff = fig.add_subplot(gs[i, 1])
    ax_main_suff.axis("off")

    for idx, planning_horizon in enumerate(planning_horizons):

        ax = fig.add_axes([
            0.55 + idx * 0.12,
            0.72 - i * 0.35,
            0.25,
            0.25
        ], projection=ccrs.EqualEarth())

        ax.set_aspect("auto")

        data = df_curtailment[
            (df_curtailment["planning_horizon"] == planning_horizon) &
            (df_curtailment["case"] == "suff") &
            (df_curtailment["tech"] == tech)
        ]

        plot_df = regions.merge(data, left_index=True, right_on="country")

        plot_df.plot(
            ax=ax,
            column="curtailment",
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            edgecolor="grey",
            linewidth=0.3      
        )

        ax.set_title(f"{planning_horizon}", fontsize=12)
        ax.axis("off")
        
    y_base = 0.7 - i * 0.34   # just below each row

    # REF colorbar (left column)
    cbar_ax_ref = fig.add_axes([0.18, y_base, 0.3, 0.01])
    mpl.colorbar.ColorbarBase(
        cbar_ax_ref,
        cmap=cmap,
        norm=norm,
        orientation="horizontal",
    )

    # SUFF colorbar (right column)
    cbar_ax_suff = fig.add_axes([0.65, y_base, 0.3, 0.01])
    mpl.colorbar.ColorbarBase(
        cbar_ax_suff,
        cmap=cmap,
        norm=norm,
        orientation="horizontal",
    )
    cbar_ax_ref.set_title("Curtailment [TWh]", fontsize=12)
    cbar_ax_suff.set_title("Curtailment [TWh]", fontsize=12)
    
    row_y = 0.72 - i * 0.35
    row_height = 0.25
    tech_labels = {
    "solar": "Solar PV",
    "onwind": "Onshore Wind",
    "offwind": "Offshore Wind"
}
    fig.text(
    0.04,
    row_y + row_height / 2,
    tech_labels[tech],
    fontsize=14,
    rotation=90,
    va="center",
    ha="center"
)