# Optional pypsa2html integration for a PyPSA-Eur workflow.
#
# Drop this file next to your other rule files and add to the Snakefile:
#
#     include: "rules/pypsa2html.smk"
#
# then run `snakemake generate_html_report` after solving.

try:
    import pypsa2html as _pypsa2html

    HAVE_PYPSA2HTML = True
except ImportError:
    HAVE_PYPSA2HTML = False
    print(
        "pypsa2html not installed -- HTML report rule disabled. "
        "Install with: pip install -e /path/to/pypsa2html --no-deps"
    )


if HAVE_PYPSA2HTML:

    PYPSA2HTML_CONFIG = config.get("pypsa2html", {}).get(
        "config", "config/pypsa2html.yaml"
    )

    rule generate_html_report:
        """Build the interactive HTML report from the solved networks."""
        params:
            config_file=PYPSA2HTML_CONFIG,
            scenario=lambda w: config["run"]["name"],
        input:
            networks=expand(
                RESULTS + "networks/solved_{horizon}.nc",
                horizon=config["planning_horizons"],
                allow_missing=True,
            ),
            config_file=PYPSA2HTML_CONFIG,
        output:
            index=RESULTS + "html/index.html",
        log:
            RESULTS + "logs/pypsa2html.log",
        benchmark:
            RESULTS + "benchmarks/pypsa2html"
        threads: 1
        resources:
            mem_mb=8000,
        run:
            import logging
            from pathlib import Path

            from pypsa2html import build_site, load_config

            logging.basicConfig(
                filename=log[0],
                level=logging.INFO,
                format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
            )

            cfg = load_config(
                params.config_file,
                overrides={"output": {"dir": str(Path(output.index).parent)}},
            )
            report = build_site(cfg, scenarios=[params.scenario])
            logging.info(report.summary())


    rule generate_html_report_all_scenarios:
        """Cross-scenario report, including the comparison overview page."""
        params:
            config_file=PYPSA2HTML_CONFIG,
        output:
            index="results/html/index.html",
        log:
            "logs/pypsa2html_all.log",
        threads: 1
        run:
            import logging
            from pathlib import Path

            from pypsa2html import build_site, load_config

            logging.basicConfig(filename=log[0], level=logging.INFO)
            cfg = load_config(
                params.config_file,
                overrides={"output": {"dir": str(Path(output.index).parent)}},
            )
            logging.info(build_site(cfg).summary())
