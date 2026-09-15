# Pilot Data Pipeline

An original portfolio demonstration of reliable ingestion for synthetic water-treatment data. Python standard library only; no cloud account required.

## What it proves

`CSV bytes → content fingerprint → schema and row validation → SQLite transaction → clean CSV + JSON report`

The sample contains 147 rows: 144 accepted readings, one duplicate, one invalid timestamp, and one non-finite value. Four accepted measurements cross the example operational thresholds.

## Run

From this project folder, with Python 3.11+:

```bash
python pipeline.py --output output
python pipeline.py --output output
python -m unittest -v
```

The second import skips the same content. `generate_sample.py` regenerates the deterministic sample with seed 19.

Outputs: `pilot.sqlite3`, `clean.csv`, and `report.json`. `example-report.json` is an actual run of the committed sample. The companion Anomaly Explorer uses its accepted measurements.

## Data contract

CSV columns, in order: `timestamp,asset,flow_lpm,conductivity_us_cm,pressure_bar`.

- Timezone-aware ISO timestamps, normalized to UTC.
- Non-empty asset identifier, up to 80 characters.
- Finite numeric measurements within explicitly defined physical validation ranges.
- Unique `(timestamp, asset)` pair across all accepted records.

Physical validation ranges reject impossible or malformed input. Operational thresholds only flag accepted readings for review; they do not discard them.

## Retry and failure behavior

- Hashing and parsing use the same bytes. Identical contents under another name are still skipped.
- Batch insertion, valid measurements, and quarantine rows share one transaction. Database writers serialize before the digest check.
- A changed file gets a new digest. Existing measurement keys enter quarantine, retaining the first value; new measurements can be accepted.
- Invalid headers or undecodable files fail before a batch is inserted. Row-level errors are quarantined with source line and reason.
- JSON reports are replaced atomically. CSV export is not atomic; the database remains the source of truth and the export can be regenerated.
- Each file is atomic, not an entire multi-file directory import. Earlier successful files stay committed if a later file fails.

## Tests

Tests cover repeat imports, renaming, overlapping modified files, invalid headers, timezone validation, non-finite values, and expected threshold findings.

## Scope and provenance

New code and synthetic measurements created for Dylan Dettloff’s portfolio with AI assistance. The project demonstrates general ingestion and monitoring concepts; it is not employer software or a reproduction of a production system. No employer code, logs, cloud resource names, or credentials are included.

This is a local, small-file demo. It reads each CSV into memory, materializes reports in memory, and does not provide cloud upload, scheduling, email delivery, schema migrations, or a correction workflow. It is not a safety-control system.
