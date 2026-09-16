"""Reconcile a sample manifest against laboratory result records. Standard library only."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path


def reconcile(manifest, results):
    """Ambiguous keys never match. Concentrations remain in their supplied units."""
    required = {'sample_id', 'analyte', 'unit'}
    for row in manifest + results:
        if not required <= row.keys() or any(not isinstance(row[k], str) or not row[k].strip() for k in required):
            raise ValueError('Every record needs nonempty sample_id, analyte and unit strings')
    key = lambda r: (r['sample_id'], r['analyte'])
    mc, rc = Counter(map(key, manifest)), Counter(map(key, results))
    expected = {key(r): r for r in manifest}
    issues, accepted = [], []
    for k, count in mc.items():
        if count > 1:
            issues.append({'key': list(k), 'reason': 'duplicate_manifest', 'count': count})
        if k not in rc:
            issues.append({'key': list(k), 'reason': 'missing_result'})
    for index, row in enumerate(results, 1):
        k, reasons = key(row), []
        if k not in expected:
            reasons.append('unexpected_result')
        elif mc[k] > 1:
            reasons.append('ambiguous_manifest')
        elif row['unit'] != expected[k]['unit']:
            reasons.append('unit_mismatch')
        if rc[k] > 1:
            reasons.append('duplicate_result')
        qualifier = row.get('qualifier')
        field = 'reporting_limit' if qualifier == 'ND' else 'value'
        value = row.get(field)
        if qualifier not in ('=', 'ND'):
            reasons.append('unknown_qualifier')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or (qualifier == 'ND' and value == 0):
            reasons.append('invalid_' + field)
        if qualifier == 'ND' and row.get('value') is not None:
            reasons.append('nondetect_has_numeric_value')
        if reasons:
            issues.append({'result_row': index, 'key': list(k), 'reasons': reasons})
        else:
            accepted.append(row.copy())
    return {'expected_records': len(manifest), 'received_records': len(results),
            'accepted_records': len(accepted), 'accepted': accepted, 'issues': issues}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path, help='JSON with manifest and results arrays')
    p.add_argument('--output', type=Path, default=Path('report.json'))
    args = p.parse_args()
    data = json.loads(args.input.read_text())
    report = reconcile(data['manifest'], data['results'])
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(f"{report['accepted_records']} accepted; {len(report['issues'])} review items → {args.output}")


if __name__ == '__main__':
    main()
