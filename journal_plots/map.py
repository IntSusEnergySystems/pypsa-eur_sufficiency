#!/usr/bin/env python3
"""Cost pies and transmission lines.

One map for each scenario, in a single row. Each panel is the cumulative
2025–2050 system cost, capital and operating (2030 for 5 years, 2040 and
2050 for 10 years each), with the 2050 transmission grid. A transmission
line or a hydrogen, CO2 or gas pipeline between two countries is split
equally between them. Pie and line legends use one scale for every map.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import pypsa
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from pyproj import Transformer
from pypsa.plot import add_legend_circles, add_legend_lines

import common
from investment_costs import color_for, group_carrier

AC_COLOR = "rosybrown"
DC_COLOR = "darkseagreen"
# Equal Earth. Pie radius is metres on that map.
PROJECTED = "EPSG:8857"
PIE_RADIUS = 2.2e5
MAX_LINEWIDTH = 8.0
# Reference sizes drawn in the legends. Areas follow the same EUR scale as the pies.
PIE_LEGEND_BEUR = (4000, 2000, 1000)
LINE_LEGEND_GW = (10, 5)
# Onshore Europe in Equal Earth, width over height.
MAP_ASPECT = 3252119 / 3416663
# Branches whose cost is shared when the two ends are different countries.
CROSS_BORDER_CARRIERS = {
    "AC",
    "DC",
    "B2B",
    "H2 pipeline",
    "H2 pipeline retrofitted",
    "CO2 pipeline",
    "gas pipeline",
    "gas pipeline new",
}
# Marginal cost of the CO2 commodity itself. Capture-plant operating
# costs stay in. These rows are left out of country expenditure.
CO2_MARGINAL_CARRIERS = {"co2", "co2 stored", "co2 sequestered", "CO2 pipeline"}


def _tech_colors() -> dict:
    return common.plotting_config()["plotting"]["tech_colors"]


def _ac_bus(network: pypsa.Network) -> pd.Series:
    """Map a country code to its AC bus."""
    buses = network.buses
    ac = buses.loc[buses.carrier == "AC"]
    return pd.Series(ac.index, index=ac.location).groupby(level=0).first()


def _pie_series(costs: pd.Series, bus_of: pd.Series) -> pd.Series:
    """Costs indexed by (location, tech) -> (AC bus, tech), in data units."""
    frame = costs.rename("value").reset_index()
    frame["bus"] = frame["location"].map(bus_of)
    frame = frame.dropna(subset=["bus"])
    frame = frame.loc[frame["value"] > 0]
    frame = frame.groupby(["bus", "tech"], as_index=False)["value"].sum()
    totals = frame.groupby("tech")["value"].sum()
    keep = totals[totals > totals.max() * 0.01].index
    frame = frame.loc[frame["tech"].isin(keep)]
    series = frame.set_index(["bus", "tech"])["value"]
    series.index = pd.MultiIndex.from_tuples(series.index, names=["bus", "tech"])
    return series


def _branch_table(network: pypsa.Network) -> pd.DataFrame:
    """One row per transmission line and pipeline, with a size used to share costs."""
    countries = set(network.buses.loc[network.buses.carrier == "AC", "location"]) - {"EU"}
    rows = []
    specs = (("Line", "s_nom_opt", None), ("Link", "p_nom_opt", CROSS_BORDER_CARRIERS))
    for component, nominal, carriers in specs:
        frame = network.df(component)
        if carriers is not None:
            frame = frame.loc[frame.carrier.isin(carriers)]
        if frame.empty:
            continue
        location0 = frame.bus0.map(network.buses.location)
        location1 = frame.bus1.map(network.buses.location)
        carrier = frame["carrier"].fillna("AC")
        size = (frame[nominal].fillna(0.0) * frame["capital_cost"].fillna(0.0)).abs()
        # The nodal table charges a branch to the first end that is a study country.
        assigned = location0.where(location0.isin(countries), location1)
        rows.append(pd.DataFrame({
            "location0": location0,
            "location1": location1,
            "carrier": carrier,
            "assigned": assigned,
            "size": size,
        }))
    if not rows:
        return pd.DataFrame(columns=["location0", "location1", "carrier", "assigned", "size"])
    return pd.concat(rows, ignore_index=True)


def _split_branch_costs(network: pypsa.Network, year_costs: pd.Series) -> pd.Series:
    """Give each country half of a cross-border branch, keeping the nodal total.

    ``year_costs`` is the annual nodal cost indexed by (location, carrier).
    Branches are the transmission lines and the hydrogen, CO2 and gas
    pipelines. A branch inside one country stays there. A branch between
    two countries is split in half. Shares of a country's cost follow the
    capital cost of each of its branches.
    """
    countries = set(network.buses.loc[network.buses.carrier == "AC", "location"]) - {"EU"}
    table = _branch_table(network)
    if year_costs.empty and table.empty:
        return pd.Series(dtype=float)
    pots = year_costs.rename_axis(["assigned", "carrier"])
    if table.empty:
        kept = pots.rename_axis(["location", "carrier"]).reset_index(name="value")
    else:
        grouped = table.groupby(["assigned", "carrier"])["size"]
        table["group_size"] = grouped.transform("sum")
        table["count"] = grouped.transform("size")
        zero = table["group_size"] <= 0
        table["share_of_group"] = 0.0
        table.loc[~zero, "share_of_group"] = table.loc[~zero, "size"] / table.loc[~zero, "group_size"]
        table.loc[zero, "share_of_group"] = 1.0 / table.loc[zero, "count"]
        keys = pd.MultiIndex.from_frame(table[["assigned", "carrier"]])
        table["pot"] = pots.reindex(keys).to_numpy()
        table["pot"] = table["pot"].fillna(0.0)
        table["branch_cost"] = table["pot"] * table["share_of_group"]
        valid0 = table["location0"].isin(countries)
        valid1 = table["location1"].isin(countries)
        cross = valid0 & valid1 & table["location0"].ne(table["location1"])
        table["share0"] = 1.0
        table["share1"] = 0.0
        table.loc[cross, "share0"] = 0.5
        table.loc[cross, "share1"] = 0.5
        only1 = ~valid0 & valid1
        table.loc[only1, "share0"] = 0.0
        table.loc[only1, "share1"] = 1.0
        covered = table.groupby(["assigned", "carrier"])["branch_cost"].sum()
        residual = pots.subtract(covered, fill_value=0.0)
        residual = residual[residual.abs() > 1.0]
        parts = [
            pd.DataFrame({
                "location": table["location0"],
                "carrier": table["carrier"],
                "value": table["branch_cost"] * table["share0"],
            }),
            pd.DataFrame({
                "location": table["location1"],
                "carrier": table["carrier"],
                "value": table["branch_cost"] * table["share1"],
            }),
        ]
        if not residual.empty:
            left = residual.rename_axis(["location", "carrier"]).reset_index(name="value")
            parts.append(left)
        kept = pd.concat(parts, ignore_index=True)
    kept = kept.loc[kept["location"].isin(countries)]
    kept["tech"] = kept["carrier"].map(group_carrier)
    return kept.groupby(["location", "tech"])["value"].sum()


def scenario_costs(scenario: str) -> tuple:
    """Cumulative cost, trade bill, and the 2050 network.

    Cost is capital plus operating expenditure. Transmission lines and
    hydrogen, CO2 and gas pipelines are taken off the nodal table and
    rebuilt from the solved networks so a cross-border branch is shared.
    """
    costs = common.read_csv(scenario, "nodal_costs")
    co2_marginal = costs["cost"].eq("marginal") & costs["carrier"].isin(CO2_MARGINAL_CARRIERS)
    costs = costs.loc[~co2_marginal]
    shared = costs.loc[costs["carrier"].isin(CROSS_BORDER_CARRIERS) & (costs["location"] != "EU")]
    local = costs.loc[~costs["carrier"].isin(CROSS_BORDER_CARRIERS) & (costs["location"] != "EU")].copy()
    local["tech"] = local["carrier"].map(group_carrier)
    by_year = local.groupby(["location", "tech"])[["2030", "2040", "2050"]].sum()
    total = by_year["2030"] * 5 + by_year["2040"] * 10 + by_year["2050"] * 10
    trade = pd.Series(dtype=float)
    network_2050 = None
    for year, weight in ((2030, 5), (2040, 10), (2050, 10)):
        network = pypsa.Network(common.network_path(scenario, year))
        year_costs = shared.groupby(["location", "carrier"])[str(year)].sum()
        total = total.add(_split_branch_costs(network, year_costs) * weight, fill_value=0.0)
        trade = trade.add(trade_balance(network) * weight, fill_value=0.0)
        if year == 2050:
            network_2050 = network
    return total, trade, network_2050


def _branch_mw(network: pypsa.Network, line_column: str, link_column: str) -> tuple[pd.Series, pd.Series]:
    """HVAC and HVDC capacity in MW, with HVDC zero except on DC links."""
    lines = network.lines[line_column].fillna(0).clip(lower=0)
    links = pd.Series(0.0, index=network.links.index)
    direct = network.links.carrier.isin(["DC", "B2B"])
    links.loc[direct] = network.links.loc[direct, link_column].fillna(0).clip(lower=0)
    return lines, links


def _scale_pies(costs: pd.Series, peak: float) -> pd.Series:
    """One EUR-to-radius factor for every map. ``peak`` is the largest country total."""
    if peak <= 0:
        return costs
    return costs / peak * PIE_RADIUS**2


def _branch_trade(network: pypsa.Network, component: str, exclude_carriers=None) -> pd.Series:
    """Net cross-border payment by country for one component, in EUR per year.

    Each snapshot is priced on its own. Energy arriving in that snapshot is
    multiplied by the marginal price of the receiving bus in the same
    snapshot. The importer pays that amount and the exporter is credited
    the same amount. Positive means the country pays for net imports.
    """
    frame = getattr(network, component)
    if exclude_carriers and "carrier" in frame.columns:
        frame = frame.loc[~frame.carrier.isin(exclude_carriers)]
    if frame.empty or "p0" not in getattr(network, f"{component}_t"):
        return pd.Series(dtype=float)
    buses = network.buses
    countries = set(buses.loc[buses.carrier == "AC", "location"]) - {"EU"}
    location0 = frame.bus0.map(buses.location)
    location1 = frame.bus1.map(buses.location)
    keep = location0.isin(countries) & location1.isin(countries) & location0.ne(location1)
    if not keep.any():
        return pd.Series(dtype=float)
    chosen = frame.index[keep]
    bus0 = frame.loc[chosen, "bus0"]
    bus1 = frame.loc[chosen, "bus1"]
    flows = getattr(network, f"{component}_t")
    weight = network.snapshot_weightings.objective.reindex(flows.p0.index)
    prices = network.buses_t.marginal_price.reindex(flows.p0.index)
    power0 = flows.p0.reindex(columns=chosen)
    power1 = flows.p1.reindex(columns=chosen)
    received0 = (-power0).clip(lower=0).mul(weight, axis=0)
    received1 = (-power1).clip(lower=0).mul(weight, axis=0)
    price0 = prices.reindex(index=received0.index, columns=bus0.to_numpy())
    price1 = prices.reindex(index=received1.index, columns=bus1.to_numpy())
    paid0 = pd.Series((received0.to_numpy() * price0.to_numpy()).sum(axis=0), index=chosen)
    paid1 = pd.Series((received1.to_numpy() * price1.to_numpy()).sum(axis=0), index=chosen)
    paid = paid0.groupby(location0.loc[chosen]).sum().add(paid1.groupby(location1.loc[chosen]).sum(), fill_value=0)
    earned = paid0.groupby(location1.loc[chosen]).sum().add(paid1.groupby(location0.loc[chosen]).sum(), fill_value=0)
    return paid.subtract(earned, fill_value=0)


def trade_balance(network: pypsa.Network) -> pd.Series:
    """Net import bill by country, EUR per year, over lines and cross-border links."""
    links = _branch_trade(network, "links", exclude_carriers=CO2_MARGINAL_CARRIERS)
    return _branch_trade(network, "lines").add(links, fill_value=0.0)


def gdp_share(costs: pd.Series, years: float, trade: pd.Series = None) -> pd.Series:
    """Annual spending as a percentage of national GDP per year.

    Spending is cumulative capital and operating cost, plus import costs
    minus export revenue, divided by the number of years. The marginal
    cost of CO2, and cross-border CO2 priced at the CO2 bus, are left out.
    Other flows use the receiving node's marginal price in that snapshot.
    """
    annual = costs.groupby(level=0).sum()
    if trade is not None:
        annual = annual.add(trade, fill_value=0.0)
    annual = annual / years
    gdp = pd.Series(common.GDP_BEUR)
    share = annual / (gdp.reindex(annual.index) * 1e9) * 100
    return share.replace([float("inf")], pd.NA).dropna()


def draw_map(ax, network: pypsa.Network, regions: gpd.GeoDataFrame, pies: pd.Series, share: pd.Series, vmin: float, vmax: float, colors: dict, line_column: str, link_column: str, pie_peak: float, line_peak: float) -> None:
    painted = regions.join(share.rename("share"), how="left")
    painted.plot(
        ax=ax,
        column="share",
        cmap="OrRd",
        vmin=vmin,
        vmax=vmax,
        linewidth=0.4,
        edgecolor="0.35",
        missing_kwds={"color": "0.92"},
    )
    bounds = regions.total_bounds
    bus_colors = {tech: color_for(tech, colors) for tech in pies.index.get_level_values(1).unique()}
    network.plot(
        ax=ax,
        geomap=False,
        bus_sizes=_scale_pies(pies, pie_peak),
        bus_colors=bus_colors,
        line_widths=_branch_mw(network, line_column, link_column)[0] / line_peak * MAX_LINEWIDTH,
        link_widths=_branch_mw(network, line_column, link_column)[1] / line_peak * MAX_LINEWIDTH,
        line_colors=AC_COLOR,
        link_colors=DC_COLOR,
        boundaries=[bounds[0], bounds[2], bounds[1], bounds[3]],
        margin=0.02,
    )
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_axis_off()


def project_network(network: pypsa.Network) -> pypsa.Network:
    """Move bus coordinates from longitude/latitude into Equal Earth."""
    transformer = Transformer.from_crs("EPSG:4326", PROJECTED, always_xy=True)
    x, y = transformer.transform(network.buses["x"].to_numpy(), network.buses["y"].to_numpy())
    network.buses["x"] = x
    network.buses["y"] = y
    return network


def main() -> None:
    colors = _tech_colors()
    regions = gpd.read_file(common.regions_path("ref")).set_index("name").to_crs(PROJECTED)
    panels = []
    for scenario in common.SCENARIOS:
        costs, trade, network = scenario_costs(scenario)
        network = project_network(network)
        pies = _pie_series(costs, _ac_bus(network))
        panels.append((common.LABELS[scenario], network, pies, gdp_share(costs, 25, trade), "s_nom_opt", "p_nom_opt"))

    pie_peak = max(float(pies.groupby(level=0).sum().max()) for _, _, pies, _, _, _ in panels)
    line_peaks = []
    for _, network, _, _, line_column, link_column in panels:
        lines, links = _branch_mw(network, line_column, link_column)
        line_peaks.append(float(lines.max()) if len(lines) else 0.0)
        line_peaks.append(float(links.max()) if len(links) else 0.0)
    line_peak = max(line_peaks) or 1.0

    vmax = max(float(share.max()) for _, _, _, share, _, _ in panels)
    vmin = min(0.0, min(float(share.min()) for _, _, _, share, _, _ in panels))
    fig_w, fig_h = 28.0, 11.5
    fig = plt.figure(figsize=(fig_w, fig_h))
    left, bottom, top = 0.004, 0.18, 0.96
    gap_x = 0.014
    cbar_w = 0.012
    panel_h = top - bottom
    panel_w = MAP_ASPECT * panel_h * fig_h / fig_w
    axes = []
    for col in range(3):
        x0 = left + col * (panel_w + gap_x)
        axes.append(fig.add_axes([x0, bottom, panel_w, panel_h]))
    cax = fig.add_axes([left + 3 * panel_w + 2 * gap_x + 0.01, bottom, cbar_w, panel_h])
    panel_titles = ["(a) Ref", "(b) Suff", "(c) Suff-nocdr"]
    seen = []
    for ax, panel_title, (title, network, pies, share, line_column, link_column) in zip(axes, panel_titles, panels):
        draw_map(ax, network, regions, pies, share, vmin, vmax, colors, line_column, link_column, pie_peak, line_peak)
        ax.text(0.5, -0.025, panel_title, transform=ax.transAxes, ha="center", va="top", fontsize=18)
        for tech in pies.index.get_level_values(1).unique():
            if tech not in seen:
                seen.append(tech)

    handles = [Patch(facecolor=color_for(tech, colors), edgecolor="none", label=tech) for tech in seen]
    handles += [
        Line2D([0], [0], color=AC_COLOR, linewidth=2, label="HVAC line"),
        Line2D([0], [0], color=DC_COLOR, linewidth=2, label="HVDC link"),
    ]
    fig.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(left + 1.5 * panel_w + gap_x, 0.0),
        ncol=(len(handles) + 1) // 2,
        frameon=False,
        fontsize=18,
        handlelength=1.8,
        columnspacing=1.4,
    )
    pie_areas = [billion * 1e9 / pie_peak * PIE_RADIUS**2 for billion in PIE_LEGEND_BEUR]
    add_legend_circles(
        axes[1],
        pie_areas,
        [f"{billion:g} bEUR" for billion in PIE_LEGEND_BEUR],
        patch_kw={"facecolor": "black", "edgecolor": "none", "alpha": 0.9},
        legend_kw={
            "loc": "upper left",
            "bbox_to_anchor": (0.0, 1.0),
            "frameon": False,
            "title": "Cumulative cost",
            "labelspacing": 3.2,
            "handletextpad": 1.0,
            "handlelength": 4.5,
            "fontsize": 18,
            "title_fontsize": 19,
            "borderpad": 0.3,
        },
    )
    line_widths = [gigawatt * 1e3 / line_peak * MAX_LINEWIDTH for gigawatt in LINE_LEGEND_GW]
    add_legend_lines(
        axes[2],
        line_widths,
        [f"{gigawatt:g} GW" for gigawatt in LINE_LEGEND_GW],
        patch_kw={"color": "0.15"},
        legend_kw={
            "loc": "upper left",
            "bbox_to_anchor": (0.0, 1.0),
            "frameon": False,
            "title": "Transmission capacity",
            "labelspacing": 2.4,
            "handletextpad": 1.6,
            "handlelength": 3.2,
            "fontsize": 18,
            "title_fontsize": 19,
            "borderpad": 0.2,
        },
    )
    colorbar = fig.colorbar(
        plt.cm.ScalarMappable(cmap="OrRd", norm=plt.Normalize(vmin=vmin, vmax=10)),
        cax=cax,
    )
    colorbar.ax.tick_params(labelsize=18)
    colorbar.set_label("Spending [% of GDP per year]", fontsize=19)
    print(common.savefig(fig, "investment_map"))


if __name__ == "__main__":
    main()
