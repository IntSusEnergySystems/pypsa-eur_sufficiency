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
  all three scenarios, and axis limits follow the data. The same script
  also writes a scenario dot plot (`capacities_dots`), the change from
  Ref (`capacities_difference`), and stacked system bars
  (`capacities_stacked`). The dot and difference legends sit under the
  figure. The carbon-management panel is 2050 CO2 captured, in
  Mt/year, from the `co2 stored` bus, and its axis label is carbon
  management capacities. Each y-axis extends 25% above its previous
  maximum, with even gaps between the ticks. Technology legends are larger.
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
  Sources are dropped and the sink is kept as a negative emission. Area
  and bar colours are drawn at 50% opacity. The legend is two rows of
  six columns, spanning from the area-chart y-axis to the right edge of
  the bars. Area-chart titles are centered and read (a) Ref, (b) Suff
  and (c) Suff-nocdr. Bar labels are one decimal place.
- Investment bars are ordered Ref, Suff, suff-nocdr within each year.
  The year is a heading above each group.
- Self-sufficiency maps keep the colour bar in a column to the right of
  the maps.
- Curtailment maps have one colour bar per technology, at the right of
  that row.
- Final-energy bars share one x-axis limit wide enough for the reference
  totals, and each panel has a carrier legend.
- Investment costs use only the `capital` rows of `costs.csv` (annualised
  capex). Carriers are renamed with the TYNDP rules and then grouped with
  the study replacement dictionary. Colours come from
  `config/plotting.default.yaml`. The left panel is titled Cumulative
  investment costs and its scenario bars are black. Bar gaps are 25%
  narrower than the pandas default.
- The multi-panel figure uses a grid so row titles sit in the margin,
  and the CO2 maps have their own colour bar.
  In `suff-nocdr` that plant is still built, but `co2 sequestered` is
  zero and the captured CO2 is consumed by Fischer-Tropsch. BECCS on
  the figure is solid-biomass capture (`biomass to liquid CC`,
  `BioSNG CC`, biomass CHP CC, industry biomass CC), which is zero in
  `suff-nocdr`.
- `investment_costs.py` reads capital costs from `costs.csv`. The left
  panel is the 2025–2050 total: the 2030 investment cost for 5 years
  and the 2040 and 2050 costs for 10 years each. Dotted lines separate
  the years on the annual chart. Technology colours no longer look up a missing
  `Fossil Fuels` key. `suff-nocdr` is a third bar in each year.
- `cumulative_emmissions.py` no longer needs `SEPIA/SEPIA_config.xlsx`.
  Annual CO2 is the `co2` bus of `energy_balance.csv`, in Gt, for all
  three scenarios. Removals stay negative. `cumulative_emissions_ccs`
  keeps that figure and adds a pie for each scenario. One half of the
  pie is capture, split into CC and CC (DAC). The other half is its
  fate, split into CCU and sequestration. Pie area follows CO2 use
  (CCU plus sequestration). Amounts are Gt from 2021 to 2050.
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
  that bus at `EU`, together with `pop_layout.csv`. Only CO2 added to
  the atmosphere is counted. DAC, biomass capture and sequestration are
  left out. In `multi.py`, gas and oil self-sufficiency share one chart,
  cumulative CO2 to 2050 is one map per scenario, and wholesale prices
  for all three scenarios share one chart. Each panel includes
  `suff-nocdr`. Gas and oil self-sufficiency is 2020 production in the
  study countries divided by fossil use. The 2020 point is Eurostat
  natural gas (`G3000`) and crude oil (`O4100_TOT`): production divided
  by production plus imports minus exports, so trade inside the study
  region cancels. Later years keep that 2020 production and use fossil
  gas and crude oil from the energy balance. The share stops at 100%
  when that production covers all fossil use. Switzerland is absent
  from the Eurostat file. Line charts are narrower and use a thinner
  stroke. Curtailment is one stacked bar chart for every scenario and
  year. Cumulative CO2
  per capita uses a stepped `Reds` scale. The top of the colour bar is
  the highest value in Ref. The bar sits under the maps. Line and bar
  panels are taller than the earlier equal-height layout. Axis labels,
  ticks and legends use a larger type size. The left-hand panel titles
  are bold.
- `map.py` is one row of three maps in the Equal Earth projection
  (EPSG:8857), for Ref, Suff and suff-nocdr. Pies are cumulative
  2025–2050 system cost, capital and operating (2030 weighted by 5 years,
  2040 and 2050 by 10), with the 2050 HVAC and HVDC grid. Transmission
  lines and hydrogen, CO2 and gas pipelines that join two countries are
  split equally between those countries. Panel titles sit under the maps as
  (a) Ref, (b) Suff and (c) Suff-nocdr. The technology legend is two rows.
  Pie size and line width each use one
  scale. The cost-size legend sits on the upper left of Suff, and the
  transmission-capacity legend sits between Suff and Suff-nocdr. Tick labels,
  axis labels and legends use a larger type size. Country shading is annual spending as a share of GDP per year:
  that cumulative cost plus imports and minus exports. The marginal cost
  of CO2 is left out, including cross-border CO2 valued at the CO2 bus
  price. Other cross-border flows are valued snapshot by snapshot at the
  marginal price of the importing node, and that same amount is the
  exporter's revenue. The colour bar uses the OrRd scale.
- `Efficiency vs Sufficiency/curtailment.py` no longer points at
  `/home/umair/pypsa-eur_master`. Country maps cover the three scenarios
  and the three planning years.
- `Efficiency vs Sufficiency/piebars.py` no longer reads SEPIA
  `inputsEU.xlsx`. Delivered energy by sector comes from the energy
  balance. `suff` and `suff-nocdr` use the same CLEVER demands, so those
  bars match.
