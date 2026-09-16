import unittest
from compare import compare


class ComparisonTests(unittest.TestCase):
    def row(self, **kw):
        return dict(dict(run_id='A', membrane='M', condition_id='C', feed_m3=10, permeate_m3=5, energy_kwh=10), **kw)

    def test_volume_weighted_not_mean_of_ratios(self):
        g = compare([self.row(), self.row(run_id='B', feed_m3=30, permeate_m3=15, energy_kwh=36)])['groups'][0]
        self.assertAlmostEqual(g['specific_energy_kwh_m3'], 2.3)
        self.assertEqual(g['recovery_pct'], 50)

    def test_conditions_do_not_mix(self):
        self.assertEqual(len(compare([self.row(), self.row(run_id='B', condition_id='hot')])['groups']), 2)

    def test_impossible_volume_and_zero(self):
        for value in [0, 11, -1, float('nan'), True]:
            self.assertEqual(len(compare([self.row(permeate_m3=value)])['rejected']), 1)

    def test_duplicate_ids_both_rejected(self):
        r = compare([self.row(), self.row()])
        self.assertEqual(len(r['rejected']), 2)
        self.assertEqual(r['groups'], [])

    def test_missing_metadata(self):
        self.assertEqual(len(compare([self.row(condition_id='')])['rejected']), 1)


if __name__ == '__main__':
    unittest.main()
