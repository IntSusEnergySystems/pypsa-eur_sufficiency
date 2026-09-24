# Running PyPSA-Eur sufficiency on this fork

These steps assume a Linux workstation with a working solver (Gurobi or HiGHS)
and enough disk for weather cutouts and retrieved datasets.

## 1. Get this code

Use the `sync-upstream-pypsa-eur` branch (latest PyPSA-Eur plus the
sufficiency features). `master` is left unchanged.

```bash
git checkout sync-upstream-pypsa-eur
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

## 3. One workflow, two scenarios

`snakemake` loads `config/study.yaml` after the upstream defaults. That file
runs the 28-country myopic study as two scenarios in one DAG:

- `ref` — reference (efficiency) demands
- `suff` — CLEVER sufficiency demands

Scenario names are listed in `config/study_scenarios.yaml`. A gitignored
`config/config.yaml` can still override the study. A `--configfile` whose
`run.name` is not `ref` or `suff` (the tutorial tests, for example) skips
the scenario file.

## 4. CLEVER data (sufficiency scenario only)

The sufficiency scenario replaces historical Eurostat/JRC demands with CLEVER
scenario files. They are gitignored. Copy them into `data/` with the names
listed in `docs/merge-upstream-pypsa-eur.md`.

Without those files, the `suff` scenario fails when building horizon-specific
energy and industry totals. The `ref` scenario does not need them.

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

## 7. Smoke test with a weekly time step

A tutorial-scale sector model (Belgium, 5 clusters, overnight 2030) with a
one-week average is:

```bash
snakemake --cores 4 --latency-wait 30 --rerun-incomplete \
  --configfile config/test/config.weekly.yaml
```

That config uses the small `be-03-2013-era5` cutout (one week of weather) and
`clustering.temporal.averaging: 168h`, so the optimisation sees a single
aggregated snapshot. It is meant to check that retrieve → compose → solve
still runs after the upstream merge, not to produce research results.

For a full weather year at weekly resolution, keep the default ERA5 cutout and
set in your overlay:

```yaml
clustering:
  temporal:
    averaging: 168h
```

## 8. HTML report (optional)

If [pypsa2html](https://github.com) is installed in the same environment:

```bash
snakemake generate_html_report --cores 1
```

The rule is skipped automatically when the package is missing.

## 9. Typical failures

- **Missing CLEVER CSVs** when `run.name` is `suff`: copy the files into `data/`.
- **Config validation errors** after editing overlays: extra keys are allowed,
  but types must still match the schema (lists vs scalars, especially
  `planning_horizons`).
- **Cutout / CDS download errors**: configure Copernicus CDS credentials as in
  the [PyPSA-Eur installation docs](https://pypsa-eur.readthedocs.io).
- **Gurobi licence**: switch `solving.solver.name` to `highs` for small tests.

More detail on the merge itself is in `docs/merge-upstream-pypsa-eur.md`.
