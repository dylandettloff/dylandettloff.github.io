"""Compare synthetic batch totals only within identical declared test conditions."""
import argparse
import json
import math
from pathlib import Path


def compare(runs):
    groups, rejected = {}, []
    # Reject all duplicate IDs rather than allowing an arbitrary first measurement.
    ids = [r.get('run_id') for r in runs]
    for index, r in enumerate(runs, 1):
        try:
            for field in ['run_id', 'membrane', 'condition_id']:
                if not isinstance(r.get(field), str) or not r[field].strip():
                    raise ValueError('missing ' + field)
            if ids.count(r['run_id']) != 1:
                raise ValueError('duplicate run_id')
            for field in ['feed_m3', 'permeate_m3', 'energy_kwh']:
                v = r.get(field)
                if isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or v < 0:
                    raise ValueError('invalid ' + field)
            if r['permeate_m3'] <= 0 or r['feed_m3'] <= 0 or r['permeate_m3'] > r['feed_m3']:
                raise ValueError('require 0 < permeate_m3 <= feed_m3')
        except ValueError as e:
            rejected.append({'row': index, 'run_id': r.get('run_id'), 'reason': str(e)})
            continue
        k = (r['condition_id'], r['membrane'])
        g = groups.setdefault(k, {'condition_id': k[0], 'membrane': k[1], 'runs': 0, 'feed_m3': 0, 'permeate_m3': 0, 'energy_kwh': 0})
        g['runs'] += 1
        for field in ['feed_m3', 'permeate_m3', 'energy_kwh']:
            g[field] += r[field]
    summaries = []
    for k in sorted(groups):
        g = groups[k]
        g['recovery_pct'] = 100 * g['permeate_m3'] / g['feed_m3']
        g['specific_energy_kwh_m3'] = g['energy_kwh'] / g['permeate_m3']
        summaries.append(g)
    return {'groups': summaries, 'rejected': rejected}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('--output', type=Path, default=Path('comparison.json'))
    args = p.parse_args()
    report = compare(json.loads(args.input.read_text()))
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    for g in report['groups']:
        print(f"{g['condition_id']} / {g['membrane']}: {g['recovery_pct']:.1f}% recovery, {g['specific_energy_kwh_m3']:.2f} kWh/m³")
    print(f"{len(report['rejected'])} rejected rows → {args.output}")


if __name__ == '__main__':
    main()
