# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""Compare annual final energy demands of ref, suff and suff-nocdr."""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from scripts._helpers import configure_logging, set_scenario_config

logger = logging.getLogger(__name__)

GROUPS = {
    "Road": ["total road"],
    "Rail": ["total rail"],
    "Residential heat": ["total residential space", "total residential water"],
    "Services heat": ["total services space", "total services water"],
    "Navigation": ["total domestic navigation", "total international navigation"],
    "Aviation": ["total domestic aviation", "total international aviation"],
}

INDUSTRY = [
    "electricity",
    "hydrogen",
    "solid biomass",
    "methane",
    "low-temperature heat",
    "naphtha",
    "ammonia",
]


def _annual_group(energy: pd.DataFrame, year: int, columns: list[str]) -> float:
    frame = energy
    if isinstance(frame.index, pd.MultiIndex) and "year" in (frame.index.names or []):
        frame = frame.xs(year, level="year")
    present = [col for col in columns if col in frame.columns]
    if not present:
        return 0.0
    return float(frame[present].sum().sum())


if __name__ == "__main__":
    if "snakemake" not in globals():
        from scripts._helpers import mock_snakemake

        snakemake = mock_snakemake("plot_scenario_demands")

    configure_logging(snakemake)
    set_scenario_config(snakemake)

    runs = list(snakemake.params.runs)
    horizons = [int(h) for h in snakemake.params.horizons]
    year = int(snakemake.params.energy_totals_year)
    energy_files = list(snakemake.input.energy)
    industry_files = list(snakemake.input.industry)

    rows = []
    for path in energy_files:
        # resources/<run>/energy_totals_<horizon>.csv
        parts = Path(path).parts
        run = parts[-2]
        horizon = int(Path(path).stem.rsplit("_", 1)[-1])
        energy = pd.read_csv(path, index_col=[0, 1])
        for group, columns in GROUPS.items():
            rows.append(
                {
                    "run": run,
                    "horizon": horizon,
                    "group": group,
                    "twh": _annual_group(energy, year, columns),
                }
            )

    industry_rows = []
    for path in industry_files:
        parts = Path(path).parts
        run = parts[-2]
        horizon = int(Path(path).stem.rsplit("_", 1)[-1])
        industry = pd.read_csv(path, index_col=0)
        present = [col for col in INDUSTRY if col in industry.columns]
        industry_rows.append(
            {
                "run": run,
                "horizon": horizon,
                "group": "Industry",
                "twh": float(industry[present].sum().sum()) if present else 0.0,
            }
        )

    demand = pd.DataFrame(rows)
    industry = pd.DataFrame(industry_rows)
    order = runs

    fig, axes = plt.subplots(
        1, len(horizons), figsize=(4.2 * len(horizons), 5.2), sharey=True
    )
    if len(horizons) == 1:
        axes = [axes]
    groups = list(GROUPS)
    x = range(len(groups))
    width = 0.8 / max(len(order), 1)
    for ax, horizon in zip(axes, horizons):
        subset = demand[demand.horizon == horizon]
        for i, run in enumerate(order):
            values = [
                float(subset.loc[(subset.run == run) & (subset.group == group), "twh"].sum())
                for group in groups
            ]
            offset = (i - (len(order) - 1) / 2) * width
            ax.bar([xi + offset for xi in x], values, width=width, label=run)
        ax.set_xticks(list(x))
        ax.set_xticklabels(groups, rotation=35, ha="right")
        ax.set_title(str(horizon))
        ax.set_ylabel("TWh/a")
    axes[0].legend(frameon=False)
    fig.suptitle("Final energy demand by scenario")
    fig.tight_layout()

    png = Path(snakemake.output.png)
    pdf = Path(snakemake.output.pdf)
    png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png, dpi=150)
    fig.savefig(pdf)
    plt.close(fig)

    ind_path = Path(snakemake.output.industry)
    fig, ax = plt.subplots(figsize=(7, 4))
    width = 0.8 / max(len(order), 1)
    x = range(len(horizons))
    for i, run in enumerate(order):
        values = [
            float(
                industry.loc[
                    (industry.run == run) & (industry.horizon == horizon), "twh"
                ].sum()
            )
            for horizon in horizons
        ]
        offset = (i - (len(order) - 1) / 2) * width
        ax.bar([xi + offset for xi in x], values, width=width, label=run)
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(h) for h in horizons])
    ax.set_ylabel("TWh/a")
    ax.set_title("Industrial final energy")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(ind_path, dpi=150)
    plt.close(fig)
    logger.info("Wrote demand comparison plots to %s", png.parent)
