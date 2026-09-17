# Sample Results Reconciler

A small Python tool that reconciles expected samples with laboratory result files before analysis. It catches missing results, unexpected samples, duplicate keys, unit mismatches and malformed concentrations.

**Why it matters:** a pilot team can receive a result file that looks complete while identifiers or units prevent reliable matching. This demo produces an explicit review queue instead of silently joining the wrong rows.

## Run

Python 3.10+, standard library only. From this directory:

```bash
python reconcile.py sample.json --output report.json
python -m unittest -v
```

The committed synthetic example produces **2 accepted records and 5 review items**. Inspect [the input](sample.json), [actual example output](example-report.json), [implementation](reconcile.py), and [tests](test_reconcile.py).

## Contract and decisions

- Input is one JSON object with `manifest` and `results` arrays. Each record requires nonempty `sample_id`, `analyte`, and `unit` strings.
- Matching uses the exact `(sample_id, analyte)` pair. Identifiers are not silently trimmed or case-folded.
- Duplicate manifest or result keys are ambiguous: no affected result is accepted.
- Units must match exactly. No implicit conversion occurs.
- A measured result uses `qualifier: "="` and a finite, nonnegative numeric `value`. Zero is valid.
- A non-detect uses `qualifier: "ND"`, a null/absent `value`, and a positive finite `reporting_limit`. It is never substituted with zero or half the reporting limit.
- Issues retain the one-based result-array row and matching key. Missing expected results appear separately. A review item is not necessarily a unique sample.
- Invalid identifiers fail the file; measurement problems enter the review queue. Inputs are not modified. Existing output is replaced only after analysis succeeds.

## Scope

Original portfolio demo using entirely synthetic chloride records. No employer code or operational data. This is data preparation, not laboratory certification, chemical interpretation, or regulatory compliance software. It does not handle revisions, unit conversion, chain of custody, or large-file streaming. The CLI writes JSON locally and sends nothing.
