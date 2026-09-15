"""Smoke tests for preserved research behavior, not scientific validation."""
import unittest
import numpy as np
import model

class ModelSmokeTests(unittest.TestCase):
    def test_salinity_screen(self):
        seawater = model.CommunityProfile('seawater')
        self.assertFalse(model.passes_screening('demo','ED',seawater))
        self.assertTrue(model.passes_screening('demo','RO',seawater))

    def test_seed_and_rank_invariants(self):
        communities={'demo':model.CommunityProfile('brackish')}
        first=model.robust_run(communities, n_param_samples=3, n_weight_samples=8, seed=7)
        second=model.robust_run(communities, n_param_samples=3, n_weight_samples=8, seed=7)
        self.assertTrue(first.equals(second))
        self.assertEqual(len(first),10)
        for _, group in first.groupby('future'):
            self.assertAlmostEqual(group.win_rate.sum(),1)
            self.assertTrue(group.avg_rank.between(1,2).all())

    def test_missing_columns_rejected(self):
        with self.assertRaises(ValueError):
            model.validate_community_input_table(model.pd.DataFrame({'community':['demo']}))

if __name__ == '__main__':
    unittest.main()
