#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 12:54:36 2026

@author: umair
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

# =========================
# DATA LOADING & CLEANING
# =========================
suff_raw = pd.read_excel("/home/umair/pypsa-eur_master/results/suff/sepia/inputsEU.xlsx", sheet_name="Inputs", index_col=2)
ref_raw = pd.read_excel("/home/umair/pypsa-eur_master/results/ref/sepia/inputsEU.xlsx", sheet_name="Inputs", index_col=2)

ref_clean = ref_raw.groupby(ref_raw.index).sum()
suff_clean = suff_raw.groupby(suff_raw.index).sum()
baseline_clean = pd.DataFrame(ref_clean["2020"])

# =========================
# SECTOR CONFIGURATIONS
# =========================
sectors = {
    "Transport": {
        "rows": ["preselccftra", "preshydcftra", "preslqfcftra", "preslqfcffrewati", "presngvcffrewati", "preshydwati", "preserailoil", "preserail", "preslqfcfavi"],
        "labels": ["EV", "FCV", "ICE", "Maritime Oil", "Maritime methanol", "Maritime Hydrogen", "Rail Oil", "Rail Electric", "Aviation Oil"],
        "colors": ["lime", "slateblue", "grey", "silver", "aquamarine", "indigo", "black", "green", "whitesmoke"],
        "xlim": 6500, "pie_x": 5800
    },
    "Industry": {
        "rows": ["prespetcfind", "cmscfind", "preselccfind", "presgazcfind", "preshydcfind", "prespetcfneind", "presenccfind", "preammind", "presmethcfind", "preshydcfneind", "presvapcfind"],
        "labels": ["Oil", "Coal", "Electricity", "Gas", "Hydrogen", "Naphtha", "Biomass", "Ammonia", "Methanol", "Hydrogen (Non-energy)", "Heat"],
        "colors": ["grey", "black", "navy", "darkorange", "indigo", "darkslategray", "green", "gold", "cyan", "violet", "red"],
        "xlim": 5500, "pie_x": 4800
    },
    "Residential & Tertiary": {
        "rows": ["presvapcfdhs", "demandheatc", "preselccfres", "preselccfterr"],
        "labels": ["District Heating", "Decentral Heat", "Electricity", "Electricity"],
        "colors": ["maroon", "orange", "navy", "navy"],
        "xlim": 6500, "pie_x": 5800
    }
}

fig, axes = plt.subplots(3, 1, figsize=(14, 18)) # 3 Rows, 1 Column
y_positions = [3, 2, 1, 0]
bar_height = 0.35
offset = 0.15

# =========================
# PLOTTING LOOP
# =========================
for (sector_name, cfg), ax in zip(sectors.items(), axes):
    rows, labels, colors = cfg["rows"], cfg["labels"], cfg["colors"]
    
    # Reindex for safety
    b_df = baseline_clean.reindex(rows, fill_value=0)
    r_df = ref_clean.reindex(rows, fill_value=0)
    s_df = suff_clean.reindex(rows, fill_value=0)

    # 1. Baseline Bars
    left = 0
    for i, tech in enumerate(rows):
        val = b_df.loc[tech, "2020"]
        ax.barh(y_positions[0], val, left=left, color=colors[i], height=bar_height, edgecolor='black', linewidth=0.2)
        left += val

    # 2. Future Years (Ref & Suff)
    for i, year in enumerate(["2030", "2040", "2050"]):
        ypos = y_positions[i+1]
        l_ref, l_suff = 0, 0
        for j, tech in enumerate(rows):
            v_ref = r_df.loc[tech, year]
            v_suff = s_df.loc[tech, year]
            ax.barh(ypos + offset, v_ref, left=l_ref, color=colors[j], height=bar_height, edgecolor='black', linewidth=0.2)
            ax.barh(ypos - offset, v_suff, left=l_suff, color=colors[j], height=bar_height, edgecolor='black', linewidth=0.2)
            l_ref += v_ref
            l_suff += v_suff
        ax.text(l_ref + 40, ypos + offset, "Ref", va='center', fontsize=9)
        ax.text(l_suff + 40, ypos - offset, "Suff", va='center', fontsize=9)

    # 3. Energy Savings Bubbles
    diff_totals = [(r_df.loc[rows, y] - s_df.loc[rows, y]).sum() for y in ["2030", "2040", "2050"]]
    max_diff = max(diff_totals) if max(diff_totals) > 0 else 1
    
    ax.text(cfg["pie_x"], y_positions[0] - 0.4, "Energy Savings\n[TWh]", ha='center', fontweight='bold', fontsize=9)

    for i, year in enumerate(["2030", "2040", "2050"]):
        ypos = y_positions[i+1]
        diff_val = (r_df.loc[rows, year] - s_df.loc[rows, year]).sum()
        if diff_val <= 0: continue

        b_size = 0.4 + (0.7 * (diff_val / max_diff))
        ax_ins = inset_axes(ax, width=b_size, height=b_size, bbox_to_anchor=(cfg["pie_x"], ypos), 
                            bbox_transform=ax.transData, loc='center')
        ax_ins.pie([1], colors=['palegreen'], wedgeprops={"edgecolor":"darkgreen", "linewidth": 0.5})
        ax_ins.text(0, 0, f"{int(diff_val)}", ha='center', va='center', fontweight='bold', fontsize=9)

    # 4. Axes Formatting
    ax.set_yticks(y_positions)
    ax.set_yticklabels(["Baseline", "2030", "2040", "2050"], fontsize=12)
    ax.set_title(f"{sector_name} Sector", fontsize=15, fontweight='bold', loc='left')
    ax.set_xlim(0, cfg["xlim"])
    ax.set_xlabel("Final Energy Consumption [TWh]", fontsize=12)
    ax.tick_params(axis='x', labelsize=12)   # <-- increase x ticks here
    ax.invert_yaxis()

    # 5. Legend (Unique handles only)
    handles, lbls = ax.get_legend_handles_labels()
    # If no labels were set in barh, we build it from labels list
    from collections import OrderedDict
    unique_legend = OrderedDict(zip(labels, [plt.Rectangle((0,0),1,1, color=c) for c in colors]))
    ax.legend(unique_legend.values(), unique_legend.keys(), title="Carrier", loc='center left', bbox_to_anchor=(1, 0.75))

plt.tight_layout(rect=[0, 0, 0.9, 1]) # Adjust for legends
plt.show()