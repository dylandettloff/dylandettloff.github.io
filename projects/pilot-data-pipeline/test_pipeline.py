import json
import tempfile
import unittest
from pathlib import Path
import pipeline
from generate_sample import generate

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        generate(self.folder)
        self.source = self.folder / 'synthetic-day.csv'
        self.db = pipeline.connect(':memory:')

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_quality_rules_and_repeat_safety(self):
        first = pipeline.ingest(self.db, self.source)
        self.assertEqual((first['accepted'], first['rejected']), (144, 3))
        self.assertEqual(len(pipeline.report(self.db)['alerts']), 4)
        self.assertEqual(pipeline.ingest(self.db, self.source)['status'], 'skipped')
        self.assertEqual(pipeline.report(self.db)['accepted'], 144)

    def test_renamed_identical_file_skips(self):
        pipeline.ingest(self.db, self.source)
        other = self.folder / 'renamed.csv'
        other.write_bytes(self.source.read_bytes())
        self.assertEqual(pipeline.ingest(self.db, other)['status'], 'skipped')

    def test_modified_file_quarantines_conflicts_and_keeps_new_rows(self):
        pipeline.ingest(self.db, self.source)
        with self.source.open('a') as stream:
            stream.write('2026-01-02T00:10:00+00:00,Demo-Skid-A,12,400,2\n')
        result = pipeline.ingest(self.db, self.source)
        self.assertEqual((result['accepted'], result['rejected']), (1, 147))
        self.assertEqual(pipeline.report(self.db)['accepted'], 145)

    def test_bad_header_leaves_no_batch(self):
        self.source.write_text('wrong,header\n1,2\n')
        with self.assertRaises(ValueError):
            pipeline.ingest(self.db, self.source)
        self.assertEqual(pipeline.report(self.db)['batches'], 0)

    def test_naive_time_and_nonfinite_rejected(self):
        row = dict(zip(pipeline.FIELDS, ['2026-01-01T00:00:00', 'A', '12', '400', '2']))
        with self.assertRaises(ValueError):
            pipeline.validate(row)
        row['timestamp'] += '+00:00'
        row['pressure_bar'] = 'inf'
        with self.assertRaises(ValueError):
            pipeline.validate(row)

    def test_worker_failure_rolls_back_whole_file(self):
        # Force an unexpected worker error after earlier valid inserts.
        from unittest.mock import patch
        original = pipeline.validate
        calls = 0
        def fail_third(raw):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise RuntimeError('simulated worker interruption')
            return original(raw)
        with patch.object(pipeline, 'validate', side_effect=fail_third):
            with self.assertRaises(RuntimeError):
                pipeline.ingest(self.db, self.source)
        self.assertEqual(pipeline.report(self.db)['accepted'], 0)
        self.assertEqual(pipeline.report(self.db)['batches'], 0)

if __name__ == '__main__':
    unittest.main()
