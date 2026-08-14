"""Tests for the educational trade quality scorecard."""

import unittest

from trade_score import (
    WEIGHTS,
    build_trade_quality_score,
    classify_assessment,
    score_delta,
    score_dte,
    score_earnings,
    score_liquidity,
    score_open_interest,
    score_trend,
    score_volume,
)


class TradeScoreTests(unittest.TestCase):
    """Test each deterministic score component and the integrated result."""

    def strong_inputs(self, **changes):
        inputs = {
            "dte": 30,
            "delta": 0.20,
            "strike_distance": 7,
            "breakeven_cushion": 12,
            "stock_price": 25,
            "ma50": 24,
            "ma200": 21,
            "iv_rank": 50,
            "days_until_earnings": 45,
            "earnings_source": "Retrieved",
            "spread_percentage": 4,
            "open_interest": 600,
            "volume": 120,
        }
        inputs.update(changes)
        return inputs

    def test_weights_total_one_hundred(self):
        self.assertEqual(sum(WEIGHTS.values()), 100)

    def test_strong_dte_range(self):
        self.assertEqual(score_dte(30)["points"], 10)

    def test_weak_dte_range(self):
        self.assertEqual(score_dte(7)["points"], 0)

    def test_preferred_delta_range(self):
        self.assertEqual(score_delta(0.20)["points"], 15)

    def test_unknown_delta_is_not_favorable(self):
        result = score_delta(None)
        self.assertEqual(result["points"], 0)
        self.assertIn("Unknown", result["detail"])

    def test_stock_above_both_moving_averages(self):
        self.assertEqual(score_trend(25, 24, 21)["points"], 15)

    def test_stock_below_two_hundred_day_average(self):
        result = score_trend(20, 21, 22)
        self.assertLess(result["points"], 15)
        self.assertIn("below", result["detail"].lower())

    def test_earnings_after_expiration(self):
        self.assertEqual(score_earnings(45, 30, "Retrieved")["points"], 10)

    def test_earnings_inside_option_period(self):
        self.assertEqual(score_earnings(20, 30, "Retrieved")["points"], 0)

    def test_unknown_earnings_is_conservative(self):
        result = score_earnings(None, 30, "Unknown")
        self.assertEqual(result["points"], 1)
        self.assertIn("Unknown", result["detail"])

    def test_manual_earnings_remains_labeled_unverified(self):
        result = score_earnings(45, 30, "Manual")
        self.assertEqual(result["points"], 7)
        self.assertIn("Manual/unverified", result["detail"])

    def test_tight_liquidity_spread(self):
        self.assertEqual(score_liquidity(4.9)["points"], 10)

    def test_wide_liquidity_spread(self):
        self.assertEqual(score_liquidity(31)["points"], 0)

    def test_high_and_low_open_interest(self):
        self.assertEqual(score_open_interest(500)["points"], 5)
        self.assertEqual(score_open_interest(20)["points"], 1)

    def test_high_and_low_volume(self):
        self.assertEqual(score_volume(100)["points"], 5)
        self.assertEqual(score_volume(0)["points"], 1)

    def test_final_score_cannot_exceed_one_hundred(self):
        scorecard = build_trade_quality_score(**self.strong_inputs())
        self.assertLessEqual(scorecard["total"], 100)

    def test_final_score_cannot_fall_below_zero(self):
        scorecard = build_trade_quality_score(
            **self.strong_inputs(
                dte=1,
                delta=None,
                strike_distance=-10,
                breakeven_cushion=-10,
                stock_price=10,
                ma50=20,
                ma200=30,
                iv_rank=0,
                days_until_earnings=0,
                spread_percentage=100,
                open_interest=0,
                volume=0,
            )
        )
        self.assertGreaterEqual(scorecard["total"], 0)

    def test_assessment_band_strong_setup(self):
        self.assertEqual(classify_assessment(80), "STRONG SETUP")

    def test_assessment_band_caution(self):
        self.assertEqual(classify_assessment(60), "CAUTION")
        self.assertEqual(classify_assessment(79), "CAUTION")

    def test_assessment_band_high_risk(self):
        self.assertEqual(classify_assessment(59), "HIGH RISK")

    def test_missing_data_produces_score_without_fabrication(self):
        scorecard = build_trade_quality_score(
            **self.strong_inputs(
                delta=None,
                iv_rank=None,
                days_until_earnings=None,
                earnings_source="Unknown",
                spread_percentage=None,
                open_interest=None,
                volume=None,
            )
        )
        self.assertIsInstance(scorecard["total"], int)
        self.assertIn("Unknown", scorecard["components"]["Delta"]["detail"])
        self.assertIn(
            "unavailable",
            scorecard["components"]["Bid/ask liquidity"]["detail"],
        )

    def test_integrated_realistic_scorecard(self):
        scorecard = build_trade_quality_score(
            **self.strong_inputs(
                strike_distance=12,
                breakeven_cushion=14.4,
                earnings_source="Manual",
                spread_percentage=12,
                open_interest=350,
                volume=40,
            )
        )
        self.assertEqual(len(scorecard["components"]), 10)
        self.assertEqual(scorecard["maximum"], 100)
        self.assertIn(scorecard["assessment"], ("STRONG SETUP", "CAUTION", "HIGH RISK"))
        self.assertIn(
            "Manual/unverified",
            scorecard["components"]["Earnings"]["detail"],
        )


if __name__ == "__main__":
    unittest.main()
