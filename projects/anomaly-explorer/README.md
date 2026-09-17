# Anomaly Explorer

A browser tool for inspecting synthetic pilot measurements with adjustable range thresholds.

## Use

Open `index.html` through the portfolio site, or run a local static server from the portfolio root:

```bash
python -m http.server 8000
```

Visit `/projects/anomaly-explorer/`. Choose flow, conductivity, or pressure. Edit lower and upper thresholds, inspect the chart and exceptions table, and download flagged records as CSV. Reset restores the defaults for the selected metric.

All calculations run in the browser, using 144 synthetic measurements exported by the companion Python pipeline. No data is sent to a server. The default conductivity range flags two readings; flow and pressure each flag one. Values exactly on a threshold are accepted.

## Implementation

- `analyze.js`: pure range-check and summary functions.
- `app.js`: controls, validation, SVG chart, accessible table, and CSV export.
- `data.js`: accepted synthetic measurements and pipeline report.
- `test_analyze.js`: boundary, empty-input, invalid-range, and non-finite-input checks.

Run the analysis tests with Node.js:

```bash
node test_analyze.js
```

This is deterministic threshold analysis, not machine learning, live monitoring, or a safety alarm. Threshold changes are temporary and do not update the pipeline database. The UI intentionally works with the bundled synthetic dataset; arbitrary file upload is not implemented.
