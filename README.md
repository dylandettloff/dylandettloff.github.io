# Dylan Dettloff — Data Engineering & Decision Systems

Data pipelines, technology comparison, and decision-support tools for water and climate applications.

## Projects

| Project | What to inspect | Stack |
| --- | --- | --- |
| [Desalination MCDA](projects/desalination-mcda/README.md) | Original research notebook, salinity screening, weighted scoring, uncertainty analysis, and a viewer of saved results | Python, NumPy, pandas |
| [Pilot Data Pipeline](projects/pilot-data-pipeline/README.md) | Synthetic data ingestion, validation, quarantine, repeat-safe imports, and local reporting | Python, SQLite |
| [Anomaly Explorer](projects/anomaly-explorer/README.md) | Interactive thresholds, time-series chart, exceptions table, and CSV export | JavaScript, HTML, CSS |
| [Sample Results Reconciler](projects/sample-reconciler/README.md) | Manifest-to-result matching, duplicate detection, unit checks, and non-detect handling | Python |
| [Membrane Run Comparison](projects/membrane-run-comparison/README.md) | Volume-weighted performance summaries, condition grouping, and invalid-run rejection | Python |

The MCDA is a research prototype with documented limitations. The pipeline and explorer are original portfolio demos using synthetic data, developed with AI assistance. They contain no employer source code or operational data.

## View the site locally

```bash
python -m http.server 8000
```

Open `http://localhost:8000`. The website is static and needs no build step.

## Checks

```bash
python -m unittest discover -s projects/pilot-data-pipeline -v
node projects/anomaly-explorer/test_analyze.js
python -m unittest discover -s projects/sample-reconciler -v
python -m unittest discover -s projects/membrane-run-comparison -v
```

See the research README for its Python dependencies and reproducible CLI run.

## Contact

[GitHub](https://github.com/dylandettloff)
