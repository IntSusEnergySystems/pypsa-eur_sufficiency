# Merging latest PyPSA-Eur into this sufficiency fork

This branch (`sync-upstream-pypsa-eur`) rebases the fork on the current
[PyPSA-Eur](https://github.com/PyPSA/pypsa-eur) `master` without rewriting
`master` of this repository.

## Why not a straight `git merge` into `master`?

`master` already contained PyPSA-Eur around `v2026.08.0`, but the commit
*Intialising the working workflow for 28 countries scenario* also replaced many
upstream files with an older snapshot (documentation moved back from Markdown
to RST, `config.default.yaml` reset toward `v2025.07.0`, rule/script layout
from before the 2026 workflow streamlining). Merging `upstream/master` into
that tree would have produced hundreds of conflicts and would have kept the
accidental downgrade.

The approach used instead:

1. Fetch `https://github.com/PyPSA/pypsa-eur.git` as `upstream`.
2. Create `sync-upstream-pypsa-eur` from `upstream/master` (includes the
   post-`v2026.08.0` commits, notably *Streamline workflow* `#1838`).
3. Re-apply only the sufficiency-specific features on that new code.

## Upstream commits brought in (relative to the previous merge-base)

Merge-base with this repo’s previous `master` was `134b2cf6`. Upstream then
added:

- `563f22f6` chore(deps): bump dawidd6/action-download-artifact
- `0ddb6cfa` Bring `tabula-calculator-calcsetbuilding` data back
- `a6c45e5a` Streamline workflow (`#1838`)
- `03be9b75` chore(deps): bump github-actions
- `1447294f` chore(deps): bump pixi in docker/dev-env

The streamlining is the important functional change: electricity and sector
networks are now composed in one step (`rules/compose.smk`,
`scripts/compose_network.py`), solved from `resources/networks/composed_{horizon}.nc`
to `results/.../networks/solved_{horizon}.nc`, and many resource files no
longer use the old `base_s_{clusters}_{opts}_{sector_opts}` wildcard pattern.

## Features conserved from the fork

| Feature | Where it lives now |
| --- | --- |
| Sufficiency / reference overlays | `config/config_suff.yaml`, `config/config_ref.yaml` (thin overlays on `config.default.yaml`) |
| Convenience Snakefiles | `Snakefile_suff`, `Snakefile_ref` |
| CLEVER demand overlay per horizon | `scripts/apply_clever_energy_totals.py`, `scripts/apply_clever_co2_totals.py`, industry overlay in `build_industrial_energy_demand_per_node.py` |
| Sufficiency heat / transport / CC / methanol behaviour | `scripts/prepare_sector_network.py` |
| Sufficiency road demand (final energy, not vkm) | `scripts/build_transport_demand.py` |
| National CO2 budgets | `scripts/solve_network.py` (`add_co2limit_country`) plus `sector.co2_budget_national` |
| pypsa2html rules | `rules/pypsa2html.smk`, `config/pypsa2html.yaml` |
| Post-processing | `journal_plots/`, `new_sankey/` |
| Belgian demand helper | `scripts/nW_BE.py`, `scripts/nW_BE_demand_model_sub_functions.py` |

CLEVER CSVs are not stored in git (`/data/*` is gitignored). Place them at:

```
data/clever_residential_{2030,2040,2050}.csv
data/clever_Transport_{2030,2040,2050}.csv
data/clever_Agriculture_{2030,2040,2050}.csv
data/clever_Tertairy_{2030,2040,2050}.csv
data/clever_Macro_{2030,2040,2050}.csv
data/clever_AFOLUB_{2030,2040,2050}.csv
data/clever_Industry_{2030,2040,2050}.csv
```

(The tertiary filename keeps the historical spelling `Tertairy`.)

## Intentionally not conserved

Wholesale copies of older PyPSA-Eur rules, RST documentation, and
`v2025.07.0` defaults were **not** carried forward. Those were an environment
snapshot, not the sufficiency method.

## How to refresh this branch later

```bash
git fetch upstream
git checkout sync-upstream-pypsa-eur
git merge upstream/master
# resolve conflicts, preferring upstream for core workflow files
# and keeping the sufficiency overlays/scripts listed above
```
