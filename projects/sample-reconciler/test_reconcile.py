import unittest
from reconcile import reconcile


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.m = {'sample_id': 'A', 'analyte': 'chloride', 'unit': 'mg/L'}
        self.r = dict(self.m, qualifier='=', value=0)

    def test_zero_is_a_valid_measurement(self):
        self.assertEqual(reconcile([self.m], [self.r])['accepted_records'], 1)

    def test_duplicate_results_never_silently_choose_first(self):
        r = reconcile([self.m], [self.r, self.r])
        self.assertEqual(r['accepted_records'], 0)
        self.assertEqual(len(r['issues']), 2)

    def test_duplicate_manifest_is_ambiguous(self):
        self.assertEqual(reconcile([self.m, self.m], [self.r])['accepted_records'], 0)

    def test_nondetect_is_not_zero(self):
        r = dict(self.m, qualifier='ND', value=None, reporting_limit=0.5)
        self.assertIsNone(reconcile([self.m], [r])['accepted'][0]['value'])
        r['value'] = 0
        self.assertEqual(reconcile([self.m], [r])['accepted_records'], 0)

    def test_units_missing_and_orphans(self):
        r = dict(self.r, sample_id='B')
        report = reconcile([self.m], [r])
        self.assertEqual(report['issues'][0]['reason'], 'missing_result')
        self.assertIn('unexpected_result', report['issues'][1]['reasons'])
        self.assertEqual(reconcile([self.m], [dict(self.r, unit='ug/L')])['accepted_records'], 0)

    def test_nonfinite_boolean_and_negative(self):
        for value in [float('nan'), float('inf'), True, -1]:
            self.assertEqual(reconcile([self.m], [dict(self.r, value=value)])['accepted_records'], 0)


if __name__ == '__main__':
    unittest.main()
