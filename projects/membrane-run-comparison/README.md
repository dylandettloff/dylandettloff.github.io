# Membrane Run Comparison

A reproducible Python tool for summarizing recovery and specific energy use from synthetic membrane-test batch totals. Separate operating conditions stay separate, and physically inconsistent rows are rejected.

**Why it matters:** averaging individual run ratios can distort comparisons when runs produce different volumes. This tool aggregates the underlying totals first and keeps the calculation visible.

## Run

Python 3.10+, standard library only. From this directory:

```bash
python compare.py sample.json --output comparison.json
python -m unittest -v
```

Inspect [the input](sample.json), [actual output](example-report.json), [implementation](compare.py), and [tests](test_compare.py).

## Example results

| Synthetic condition | Membrane | Recovery | Specific energy |
| --- | --- | --- | --- |
| Low salinity, 25°C | A | 50% | 2.30 kWh/m³ |
| Low salinity, 25°C | B | 60% | 2.00 kWh/m³ |
| High salinity, 25°C | A | 40% | 4.00 kWh/m³ |

One row is rejected because product volume exceeds feed volume. These invented examples demonstrate calculations, not performance claims about real membranes.

## Calculation and input contract

Input is a JSON array. Each row requires unique `run_id`, nonempty `membrane` and `condition_id`, and finite numeric batch totals `feed_m3`, `permeate_m3`, and `energy_kwh`. Energy is nonnegative; volumes must satisfy `0 < permeate_m3 <= feed_m3`. Both occurrences of a duplicate run ID are rejected.

Within each `(condition_id, membrane)` group:

```text
recovery (%) = 100 × sum(permeate_m3) / sum(feed_m3)
specific energy (kWh/m³) = sum(energy_kwh) / sum(permeate_m3)
```

For membrane A in the low-salinity example, `(10 + 36) / (5 + 15) = 2.30 kWh/m³`. The unweighted mean of run ratios would be 2.20 and answers a different question. Unrounded numeric totals and ratios are retained in JSON.

## Comparison limits

`condition_id` is a user-declared grouping label, not an automatic equivalence check. Real comparisons require matched salinity, temperature, pressure, feed chemistry, test duration, measurement boundaries and other relevant conditions. The caller must establish these and use the same energy-meter boundary. These are batch totals, not instantaneous readings or cumulative counters.

No temperature normalization, salt rejection calculation, uncertainty intervals, significance tests, cost estimates or technology recommendation is supplied. The CLI reads small files in memory and replaces the chosen local output. It makes no network calls.

Original portfolio demo using synthetic data, developed with AI assistance. Contains no employer code or measurements.
