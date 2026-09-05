import unittest
from scripts.top100_selection_v2 import optimize


class Top100SelectionV2Tests(unittest.TestCase):
    def test_filters_published_low_commission_and_weak_scarcity(self):
        items = [
            {"id":"ok","category":"A","commission_eur":35,"greece_scarcity":0.9,"demand_now":0.8,"forecast_demand":0.8},
            {"id":"published","category":"A","commission_eur":50,"greece_scarcity":1,"status":"published"},
            {"id":"low","category":"A","commission_eur":20,"greece_scarcity":1},
            {"id":"common","category":"A","commission_eur":40,"greece_scarcity":0.2},
        ]
        result = optimize(items)
        self.assertEqual([p["id"] for p in result["selected"]], ["ok"])

    def test_caps_categories_at_five(self):
        items=[]
        for c in range(8):
            for i in range(25):
                items.append({"id":f"{c}-{i}","category":f"C{c}","commission_eur":30+c,"greece_scarcity":0.9,"demand_now":0.7,"forecast_demand":0.7})
        result=optimize(items)
        self.assertLessEqual(len(result["selected_categories"]),5)
        self.assertLessEqual(len(result["selected"]),100)


if __name__ == "__main__":
    unittest.main()
