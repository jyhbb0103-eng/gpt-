import unittest

from market_analyzer import advice_from_score, analyze_market, environment_from_score


def sample_data(up=3200, down=1500, index_change=1.0, today=1.1e12, yesterday=1e12):
    indexes = {}
    for name in ("上证指数", "深证成指", "创业板指", "沪深300"):
        indexes[name] = {
            "change_pct": index_change,
            "above_ma5": True,
            "above_ma10": True,
            "above_ma20": True,
        }
    return {
        "indexes": indexes,
        "market": {
            "up_count": up, "down_count": down, "flat_count": 50,
            "limit_up_count": 70, "limit_down_count": 4,
        },
        "turnover": {"today": today, "yesterday": yesterday, "average_5d": 0.98e12},
        "is_partial": False,
    }


class TestMarketAnalyzer(unittest.TestCase):
    def test_score_is_stable_and_bounded(self):
        first = analyze_market(sample_data())
        second = analyze_market(sample_data())
        self.assertEqual(first["score"], second["score"])
        self.assertGreaterEqual(first["score"], 0)
        self.assertLessEqual(first["score"], 100)
        self.assertEqual(sum(x["score"] for x in first["components"].values()), first["score"])

    def test_environment_boundaries(self):
        self.assertEqual(environment_from_score(80), "强势")
        self.assertEqual(environment_from_score(65), "震荡偏强")
        self.assertEqual(environment_from_score(50), "震荡")
        self.assertEqual(environment_from_score(35), "震荡偏弱")
        self.assertEqual(environment_from_score(34), "弱势")

    def test_advice_is_restricted_to_allowed_levels(self):
        allowed = {
            "可以积极关注", "可以参与，但注意控制仓位", "谨慎参与",
            "以观察为主", "风险较高，优先控制风险",
        }
        for score in range(101):
            self.assertIn(advice_from_score(score), allowed)

    def test_weak_market_scores_lower(self):
        strong = analyze_market(sample_data())["score"]
        weak_data = sample_data(up=900, down=3800, index_change=-2.0, today=0.7e12, yesterday=1e12)
        weak_data["market"]["limit_up_count"] = 12
        weak_data["market"]["limit_down_count"] = 45
        for item in weak_data["indexes"].values():
            item.update(above_ma5=False, above_ma10=False, above_ma20=False)
        weak = analyze_market(weak_data)["score"]
        self.assertLess(weak, strong)


if __name__ == "__main__":
    unittest.main()
