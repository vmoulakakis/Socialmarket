import datetime as dt
import unittest

from forecast_ensemble import directional_scenarios


class DirectionalScenarioTests(unittest.TestCase):
    def test_withholds_when_history_is_insufficient(self):
        rows=[{'observed_at':'2026-08-01T00:00:00+00:00','demand_score':50}]
        self.assertEqual(directional_scenarios(rows)['status'],'WITHHELD')

    def test_emits_bounded_ordered_scenarios_for_eligible_history(self):
        start=dt.datetime(2026,1,1,tzinfo=dt.timezone.utc)
        rows=[]
        for day in range(100):
            # Three independent observations per day produce sufficient raw
            # history while preserving a realistic daily series.
            for offset in (-1,0,1):
                rows.append({'observed_at':(start+dt.timedelta(days=day,minutes=offset)).isoformat(),'demand_score':45+day*.12+offset})
        result=directional_scenarios(rows,horizon=7)
        self.assertEqual(result['status'],'MODELED_SCENARIOS')
        self.assertEqual(len(result['base']),7)
        for low,base,high in zip(result['conservative'],result['base'],result['upside']):
            self.assertLessEqual(low,base)
            self.assertLessEqual(base,high)
            self.assertGreaterEqual(low,0)
            self.assertLessEqual(high,100)
        self.assertIn('not sales',result['truth_label'])


if __name__=='__main__':
    unittest.main()
