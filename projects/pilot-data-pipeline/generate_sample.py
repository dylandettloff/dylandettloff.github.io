"""Generate deterministic fictional pilot data plus intentional quality faults."""
import csv
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

def generate(destination):
    rng = random.Random(19)
    rows = []
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(144):
        rows.append([(start + timedelta(minutes=10*i)).isoformat(), 'Demo-Skid-A',
                     round(12 + math.sin(i/12) + rng.uniform(-.3, .3), 2),
                     round(390 + math.sin(i/9)*30 + rng.uniform(-10, 10), 2),
                     round(2.2 + rng.uniform(-.15, .15), 2)])
    rows[45][3] = 920
    rows[46][3] = 870
    rows[90][4] = 5.2
    rows[110][2] = 4.3
    rows.extend([rows[10].copy(), ['bad-time', 'Demo-Skid-A', 12, 400, 2],
                 [(start + timedelta(days=1)).isoformat(), 'Demo-Skid-A', 'NaN', 400, 2]])
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with (destination / 'synthetic-day.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['timestamp', 'asset', 'flow_lpm', 'conductivity_us_cm', 'pressure_bar'])
        writer.writerows(rows)

if __name__ == '__main__':
    generate(Path(__file__).with_name('sample-data'))
