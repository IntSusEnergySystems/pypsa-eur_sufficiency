# Running PyPSA-Eur sufficiency on this fork

These steps assume a Linux workstation with a working solver (Gurobi or HiGHS)
and enough disk for weather cutouts and retrieved datasets.

## 1. Get this code

The workflow lives on `master`.

```bash
git checkout master
```

## 2. Install the environment

Upstream PyPSA-Eur is installed with [pixi](https://pixi.sh):

```bash
curl -fsSL https://pixi.sh/install.sh | bash
pixi install
```

If pixi is not available, create an environment from `envs/environment.yaml`
(or the exported pin file `envs/default_linux-64.pin.txt`) and make sure
`snakemake >= 8.11` is on `PATH`.

The default Snakemake profile in `profiles/default/config.yaml` no longer
sets `logger: pypsa`, because that plugin is not installed in a stock pixi
environment and Snakemake 9 then refuses to start. Re-enable it after:

```bash
pixi add snakemake-logger-plugin-pypsa
```

## 3. One workflow, three scenarios

`snakemake` loads `config/study.yaml` after the upstream defaults. That file
runs the 28-country myopic study as three scenarios in one DAG.
Clustering is administrative at country level (`clustering.administrative.level: 0`),
so each country is one node:

- `ref` — reference demands. Sequestration, DAC and CCS are allowed.
- `suff` — CLEVER demands, with the same technology options as `ref`,
  including sequestration, DAC and CCS.
- `suff-nocdr` — CLEVER demands, but sequestration, DAC and BECCS are
  switched off. Carbon capture remains only where the CO2 is used (CCU).

Scenario names are listed in `config/study_scenarios.yaml`. A gitignored
`config/config.yaml` can still override the study. A `--configfile` whose
`run.name` is not one of those three names (the tutorial tests, for example)
skips the scenario file.

Road and shipping fuel shares come from CLEVER in every scenario that can see
`data/clever_Transport_{year}.csv`, and those carrier shares are the same in
`ref`, `suff` and `suff-nocdr`. The reference scenario still applies the ICE
heating correction and the future electric, fuel-cell and ICE efficiencies,
and the default oil-to-hydrogen and oil-to-methanol shipping efficiency
ratios, but only to the total. The split across carriers is unchanged.
`suff` and `suff-nocdr` keep CLEVER final energy and skip those corrections.

## 4. CLEVER data (sufficiency scenarios)

`suff` and `suff-nocdr` replace historical Eurostat/JRC demands with CLEVER
scenario files. They are gitignored. Copy them into `data/` with the names
listed in `docs/merge-upstream-pypsa-eur.md`.

Without those files, the sufficiency scenarios fail when building
horizon-specific energy and industry totals. The `ref` scenario does not need
them for its own demand totals. Transport shares still use the CLEVER
transport file when it is present.

## 5. Retrieve data and solve

Dry-run first:

```bash
snakemake -n --rerun-incomplete
```

Then run (example: 8 cores, extra wait for filesystem latency):

```bash
snakemake --cores 8 --latency-wait 30 --rerun-incomplete
```

Solved networks are written to:

```
results/<run-name>/networks/solved_<horizon>.nc
```

for each planning horizon in the overlay (`2030`, `2040`, `2050`).

## 6. Solver

- Production runs in the overlays use **Gurobi** (`gurobi-numeric-focus`).
- The tutorial/test configs use **HiGHS**, which is enough for smoke tests.

Set `solving.solver.name` in your overlay if you need to switch.

## 7. Weekly time step

`config/study-weekly.yaml` keeps the three-scenario study and aggregates the
weather year to one-week snapshots (`clustering.temporal.averaging: 168h`).
It also lowers the solver memory request so the job can run on a workstation.

```bash
export TMPDIR="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPDIR"
snakemake --cores 8 --latency-wait 30 --rerun-incomplete \
  --configfile config/study-weekly.yaml \
  --resources mem_mb=50000 \
  results/graphs/scenario_demands.png \
  results/html/index.html
```

Demand comparison figures are written to:

```
results/graphs/scenario_demands.png
results/graphs/scenario_demands.pdf
results/graphs/scenario_industry_demands.png
```

`suff` and `suff-nocdr` use the same CLEVER demands, so those two bars match.
`ref` uses the historical energy totals.

Solved networks for this run are:

```
results/<run>/networks/solved_<horizon>.nc
```

with `<run>` one of `ref`, `suff` or `suff-nocdr`, and horizons `2030`,
`2040` and `2050`.

A smaller Belgium overnight check, with one week of weather rather than a
full year, remains:

```bash
snakemake --cores 4 --latency-wait 30 --rerun-incomplete \
  --configfile config/test/config.weekly.yaml
```

## 8. HTML report

Install the report builder into the pixi environment once:

```bash
pixi run pip install -e /home/umair/pypsa2html --no-deps
```

Then, after the three scenarios have solved:

```bash
snakemake generate_html_report_all_scenarios --cores 1 \
  --configfile config/study-weekly.yaml
```

The combined report is `results/html/index.html`. The scenario list is
`config/pypsa2html.yaml`. The rule is skipped when `pypsa2html` is missing.

## 9. Typical failures

- **Missing CLEVER CSVs** when `run.name` is `suff` or `suff-nocdr`: copy the
  files into `data/`.
- **Config validation errors** after editing overlays: extra keys are allowed,
  but types must still match the schema (lists vs scalars, especially
  `planning_horizons`).
- **Cutout / CDS download errors**: configure Copernicus CDS credentials as in
  the [PyPSA-Eur installation docs](https://pypsa-eur.readthedocs.io).
- **Gurobi licence**: switch `solving.solver.name` to `highs` for small tests.

More detail on the merge itself is in `docs/merge-upstream-pypsa-eur.md`.
