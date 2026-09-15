"""Local, transactional ingestion of synthetic water-treatment measurements.

No cloud credentials, network calls, or external Python dependencies.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ['timestamp', 'asset', 'flow_lpm', 'conductivity_us_cm', 'pressure_bar']
RANGES = {'flow_lpm': (0, 1000), 'conductivity_us_cm': (0, 100000), 'pressure_bar': (0, 100)}
RULES = {'flow_lpm': (8, 18), 'conductivity_us_cm': (0, 650), 'pressure_bar': (0, 4)}

def connect(path):
    db = sqlite3.connect(path)
    db.execute('PRAGMA foreign_keys = ON')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS batches (
        digest TEXT PRIMARY KEY, source TEXT NOT NULL, imported_at TEXT NOT NULL,
        accepted INTEGER NOT NULL, rejected INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS measurements (
        timestamp TEXT NOT NULL, asset TEXT NOT NULL,
        flow_lpm REAL NOT NULL, conductivity_us_cm REAL NOT NULL, pressure_bar REAL NOT NULL,
        batch TEXT NOT NULL REFERENCES batches(digest),
        PRIMARY KEY(timestamp, asset));
      CREATE TABLE IF NOT EXISTS quarantine (
        batch TEXT NOT NULL REFERENCES batches(digest), line INTEGER NOT NULL,
        reason TEXT NOT NULL, raw TEXT NOT NULL);
    ''')
    return db

def validate(raw):
    if None in raw or any(raw.get(field) is None for field in FIELDS):
        raise ValueError('Wrong number of columns')
    timestamp = datetime.fromisoformat(raw['timestamp'].replace('Z', '+00:00'))
    if timestamp.tzinfo is None:
        raise ValueError('Timestamp must include a timezone')
    asset = raw['asset'].strip()
    if not asset or len(asset) > 80:
        raise ValueError('Asset must be 1–80 characters')
    values = {}
    for field, (low, high) in RANGES.items():
        number = float(raw[field])
        if not math.isfinite(number) or not low <= number <= high:
            raise ValueError(f'{field} outside physical validation range [{low}, {high}]')
        values[field] = number
    return {'timestamp': timestamp.astimezone(timezone.utc).isoformat(), 'asset': asset, **values}

def ingest(db, source):
    # Hash and parse the same bytes so a changing source cannot mismatch its digest.
    payload = Path(source).read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    reader = csv.DictReader(io.StringIO(payload.decode('utf-8-sig')))
    if reader.fieldnames != FIELDS:
        raise ValueError(f'{Path(source).name}: expected columns {FIELDS}')
    with db:
        # Serialize the digest check and insertion across concurrent writers.
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM batches WHERE digest=?', (digest,)).fetchone():
            return {'file': Path(source).name, 'status': 'skipped', 'accepted': 0, 'rejected': 0}
        db.execute('INSERT INTO batches VALUES (?,?,?,0,0)',
                   (digest, Path(source).name, datetime.now(timezone.utc).isoformat()))
        accepted = rejected = 0
        for line, raw in enumerate(reader, start=2):
            try:
                row = validate(raw)
                db.execute('INSERT INTO measurements VALUES (?,?,?,?,?,?)',
                           (*[row[field] for field in FIELDS], digest))
                accepted += 1
            except (ValueError, OverflowError, sqlite3.IntegrityError) as exc:
                reason = ('Duplicate asset/timestamp; existing value retained'
                          if isinstance(exc, sqlite3.IntegrityError) else str(exc))
                db.execute('INSERT INTO quarantine VALUES (?,?,?,?)',
                           (digest, line, reason, json.dumps(raw)))
                rejected += 1
        db.execute('UPDATE batches SET accepted=?, rejected=? WHERE digest=?', (accepted, rejected, digest))
    return {'file': Path(source).name, 'status': 'imported', 'accepted': accepted, 'rejected': rejected}

def report(db):
    records = [dict(zip(FIELDS, values)) for values in db.execute(
        'SELECT timestamp,asset,flow_lpm,conductivity_us_cm,pressure_bar FROM measurements ORDER BY timestamp,asset')]
    alerts = []
    for row in records:
        for field, (low, high) in RULES.items():
            if not low <= row[field] <= high:
                alerts.append({'timestamp': row['timestamp'], 'asset': row['asset'],
                               'metric': field, 'value': row[field], 'low': low, 'high': high})
    return {'dataset': 'Synthetic water-treatment pilot; demonstration only',
            'rules': RULES, 'accepted': len(records),
            'rejected': db.execute('SELECT count(*) FROM quarantine').fetchone()[0],
            'batches': db.execute('SELECT count(*) FROM batches').fetchone()[0],
            'alerts': alerts, 'measurements': records}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path(__file__).with_name('sample-data'))
    parser.add_argument('--output', type=Path, default=Path('output'))
    args = parser.parse_args()
    sources = sorted(args.input.glob('*.csv'))
    if not sources:
        parser.error('Input folder contains no CSV files')
    args.output.mkdir(parents=True, exist_ok=True)
    db = connect(args.output / 'pilot.sqlite3')
    try:
        for source in sources:
            print(json.dumps(ingest(db, source)))
        result = report(db)
        temp = args.output / 'report.json.tmp'
        temp.write_text(json.dumps(result, indent=2) + '\n')
        temp.replace(args.output / 'report.json')
        with (args.output / 'clean.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(result['measurements'])
        print(json.dumps({key: result[key] for key in ('accepted', 'rejected', 'batches')}))
    finally:
        db.close()

if __name__ == '__main__':
    main()
