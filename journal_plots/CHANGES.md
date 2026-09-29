# Journal plot changes

The scripts in this folder used paths and result files from an older
checkout (`country_csvs`, `htmls/ChartData_*.xlsx`, SEPIA workbooks, and
networks named `base_s_33___{year}.nc`). Those files are not produced by
the current study. Every figure now reads `results/<scenario>/csvs` or
`results/<scenario>/networks/solved_<year>.nc`, with `<scenario>` one of
`ref`, `suff` and `suff-nocdr`.

`suff-npcdr` in the plotting request is the study scenario `suff-nocdr`
(CLEVER demands, carbon capture for utilisation only, no sequestration,
DAC or BECCS).

Figures are written to `journal_plots/output/`. Country curtailment is
cached in `journal_plots/.cache/` because it is summed from the solved
network time series.

## Shared loader

`common.py` holds scenario names, colours, GDP figures, CSV and network
paths, population, and the VRE curtailment helper. Snapshot weights in
these networks are 6 hours, so curtailed energy is
`(p_max_pu * p_nom_opt - p) * 6`.

## Script fixes

- `capacities.py` no longer reads `/home/umair/28 countries_previous` or
  `/home/umair/pypsa-eur`. The previous 2020 baseline and the hardcoded
  DAC, BECCS and gas-CC rows were removed. Bars are 2050 capacities for
  all three scenarios, and axis limits follow the data.
- Biogas upgrading with capture is omitted from the capacity figure.
  BECCS remains the solid-biomass capture group, which is zero in
  `suff-nocdr`.
- CO2-per-capita and investment maps keep the colour bar in its own
  column on the right. Country borders stay drawn so the near-zero
  2040 and 2050 maps do not disappear into the background. The earlier
  blur came from attaching the colour bar to the whole axes grid, which
  squeezed the later years into the middle of the figure.
- Cumulative emissions start in 2020 from the EU27 UNFCCC CO2 inventory
  in the JRC-IDEES comparison workbook. The path to 2050 is the running
  sum of linearly interpolated annual emissions. Bar labels are omitted
  because the shared legend sits under the figure. Land use and forestry
  is the CLEVER AFOLU LULUCF sink for every scenario, including reference.
  Sources are dropped and the sink is kept as a negative emission.
- Investment bars are ordered Ref, Suff, suff-nocdr within each year.
  The year is a heading above each group.
- Self-sufficiency maps keep the colour bar in a column to the right of
  the maps.
- Curtailment maps have one colour bar per technology, at the right of
  that row.
- Final-energy bars share one x-axis limit wide enough for the reference
  totals, and each panel has a carrier legend.
- Investment costs are summed into technology groups, each with one colour.
- The multi-panel figure uses a grid so row titles sit in the margin,
  and the CO2 maps have their own colour bar.
  In `suff-nocdr` that plant is still built, but `co2 sequestered` is
  zero and the captured CO2 is consumed by Fischer-Tropsch. BECCS on
  the figure is solid-biomass capture (`biomass to liquid CC`,
  `BioSNG CC`, biomass CHP CC, industry biomass CC), which is zero in
  `suff-nocdr`.
- `investment_costs.py` reads capital costs from `costs.csv`. The left
  panel is the 27-year period total (mean of the three snapshot years,
  held for 27 years). Technology colours no longer look up a missing
  `Fossil Fuels` key. `suff-nocdr` is a third bar in each year.
- `cumulative_emmissions.py` no longer needs `SEPIA/SEPIA_config.xlsx`.
  Annual CO2 is the `co2` bus of `energy_balance.csv`, in Gt, for all
  three scenarios. Removals stay negative.
- `self_sufficiency.py` no longer reads `ChartData_EU.xlsx`. Gas
  self-sufficiency is domestic renewable gas divided by total gas supply.
- `pie_charts.py` no longer reads `total_imports_BE.csv` or
  `data/europe.geojson`, which is not in this checkout. The locator map
  uses `resources/ref/onshore_regions.geojson`. Belgium 2050 primary-fuel
  supply and local renewable generation come from
  `nodal_energy_balance.csv` for all three scenarios. Solved years start
  at 2030, so the old 2020 pie is not drawn.
- CCGT is a link, so it is absent from `capacity_factors.csv`. Its
  capacity factor is AC output divided by nameplate capacity and 8760 h.
- `ind.py` and `multi.py` no longer divide prices by 8760 and a fixed
  node count. Prices come from `prices.csv`. Capacity factors come from
  `capacity_factors.csv`, which already accounts for the 6-hour
  weighting. Curtailment pies are in TWh. CO2 per capita uses link flows
  on the atmospheric CO2 bus, because `nodal_energy_balance.csv` books
  that bus at `EU`, together with `pop_layout.csv`. Each panel includes
  `suff-nocdr`.
- `map.py` no longer looks up retired bus names such as `AT0 0`, and it
  no longer opens the solved networks. Investment as a share of GDP is
  mapped from `nodal_costs.csv` for all three scenarios.
- `Efficiency vs Sufficiency/curtailment.py` no longer points at
  `/home/umair/pypsa-eur_master`. Country maps cover the three scenarios
  and the three planning years.
- `Efficiency vs Sufficiency/piebars.py` no longer reads SEPIA
  `inputsEU.xlsx`. Delivered energy by sector comes from the energy
  balance. `suff` and `suff-nocdr` use the same CLEVER demands, so those
  bars match.
