"""Automated tests for the cash-secured put calculator."""

from contextlib import redirect_stdout
from datetime import date
from io import StringIO
import unittest

from put_calculator import (
    calculate_iv_rank,
    calculate_put_results,
    calculate_technical_context,
    build_market_snapshot,
    build_put_seller_view,
    classify_earnings_risk,
    classify_trend,
    create_trade_checklist,
    display_market_snapshot,
    earnings_occur_during_trade,
    validate_inputs,
)


class PutCalculatorTests(unittest.TestCase):
    """Test the calculator with the standard example trade."""

    def setUp(self):
        """Store valid inputs that validation tests can adjust as needed."""

        self.valid_inputs = {
            "stock_price": 25,
            "strike_price": 22,
            "premium_received": 0.60,
            "number_of_contracts": 1,
            "days_to_expiration": 30,
            "delta": 0.20,
            "iv_low": 25,
            "iv_high": 65,
            "iv_percentile": 65,
            "support_price": 22.50,
            "ma50": 24,
            "ma200": 21,
            "resistance_price": 28,
            "days_until_earnings": 20,
        }

    def assert_invalid(self, **changes):
        """Confirm that changed inputs are rejected by existing validation."""

        inputs = self.valid_inputs.copy()
        inputs.update(changes)
        with self.assertRaises(ValueError):
            validate_inputs(**inputs)

    def make_checklist(self, **changes):
        """Create a checklist, changing only values needed by a test."""

        inputs = {
            "delta": 0.20,
            "iv_rank": 50,
            "iv_percentile": 65,
            "strike_price": 22,
            "support_price": 22.50,
            "days_until_earnings": 45,
            "days_to_expiration": 30,
            "stock_price": 25,
            "ma50": 24,
            "ma200": 21,
        }
        inputs.update(changes)
        return create_trade_checklist(**inputs)

    def test_put_calculations(self):
        """Test all seven original put calculations."""

        results = calculate_put_results(25, 22, 0.60, 1, 30)
        expected = (60.00, 21.40, 2200.00, 2.7273, 33.1818, 12.00, 14.40)

        for actual, expected_value in zip(results, expected):
            self.assertAlmostEqual(actual, expected_value, places=4)

    def test_iv_rank(self):
        """Test IV Rank for the standard IV range."""

        self.assertAlmostEqual(calculate_iv_rank(45, 25, 65), 50.00)

    def test_technical_context_calculations(self):
        """Test support, moving-average, and resistance calculations."""

        results = calculate_technical_context(25, 22, 22.50, 24, 21, 28)
        expected = (11.1111, 2.2222, 4.1667, 19.0476, -10.7143)

        for actual, expected_value in zip(results, expected):
            self.assertAlmostEqual(actual, expected_value, places=4)

    def test_earnings_before_expiration(self):
        """Earnings before expiration should trigger the warning condition."""

        self.assertTrue(earnings_occur_during_trade(20, 30))

    def test_earnings_after_expiration(self):
        """Earnings after expiration should not trigger the warning."""

        self.assertFalse(earnings_occur_during_trade(45, 30))

    def test_earnings_on_expiration_boundary(self):
        """Earnings on expiration day should trigger the warning condition."""

        self.assertTrue(earnings_occur_during_trade(30, 30))

    def test_zero_dte_is_invalid(self):
        self.assert_invalid(days_to_expiration=0)

    def test_zero_stock_price_is_invalid(self):
        self.assert_invalid(stock_price=0)

    def test_negative_premium_is_invalid(self):
        self.assert_invalid(premium_received=-0.01)

    def test_delta_greater_than_one_is_invalid(self):
        self.assert_invalid(delta=1.01)

    def test_negative_delta_is_invalid(self):
        self.assert_invalid(delta=-0.01)

    def test_equal_iv_high_and_low_are_invalid(self):
        self.assert_invalid(iv_low=25, iv_high=25)

    def test_iv_high_below_low_is_invalid(self):
        self.assert_invalid(iv_low=30, iv_high=25)

    def test_nonpositive_support_is_invalid(self):
        self.assert_invalid(support_price=0)

    def test_nonpositive_resistance_is_invalid(self):
        self.assert_invalid(resistance_price=0)

    def test_nonpositive_moving_averages_are_invalid(self):
        for field in ("ma50", "ma200"):
            with self.subTest(field=field):
                self.assert_invalid(**{field: 0})

    def test_negative_days_until_earnings_are_invalid(self):
        self.assert_invalid(days_until_earnings=-1)

    def test_valid_iv_percentile(self):
        validate_inputs(**self.valid_inputs)

    def test_iv_percentile_below_zero_is_invalid(self):
        self.assert_invalid(iv_percentile=-0.01)

    def test_iv_percentile_above_100_is_invalid(self):
        self.assert_invalid(iv_percentile=100.01)

    def test_delta_check_pass(self):
        self.assertIn("Delta Check: PASS", self.make_checklist(delta=0.20)[0])

    def test_delta_check_review(self):
        self.assertIn("Delta Check: REVIEW", self.make_checklist(delta=0.40)[0])

    def test_iv_rank_check_pass(self):
        self.assertIn("IV Rank Check: PASS", self.make_checklist(iv_rank=50)[1])

    def test_iv_rank_check_review(self):
        self.assertIn("IV Rank Check: REVIEW", self.make_checklist(iv_rank=20)[1])

    def test_iv_percentile_check_pass(self):
        checklist = self.make_checklist(iv_percentile=65)
        self.assertIn("IV Percentile Check: PASS", checklist[2])

    def test_iv_percentile_check_review(self):
        checklist = self.make_checklist(iv_percentile=30)
        self.assertIn("IV Percentile Check: REVIEW", checklist[2])

    def test_support_check_pass(self):
        self.assertIn("Support Check: PASS", self.make_checklist()[3])

    def test_support_check_review(self):
        checklist = self.make_checklist(strike_price=23, support_price=22.50)
        self.assertIn("Support Check: REVIEW", checklist[3])

    def test_earnings_check_pass(self):
        checklist = self.make_checklist(days_until_earnings=45)
        self.assertIn("Earnings Check: PASS", checklist[4])

    def test_earnings_check_warning(self):
        checklist = self.make_checklist(days_until_earnings=20)
        self.assertIn("Earnings Check: WARNING", checklist[4])

    def test_trend_check_pass(self):
        self.assertIn("Trend Check: PASS", self.make_checklist()[5])

    def test_trend_check_review(self):
        checklist = self.make_checklist(stock_price=23, ma50=24, ma200=21)
        self.assertIn("Trend Check: REVIEW", checklist[5])

    def test_trend_more_than_two_percent_above_is_bullish(self):
        self.assertEqual(classify_trend(2.01), "Bullish")

    def test_trend_within_two_percent_is_neutral(self):
        for distance in (-2, 0, 2):
            with self.subTest(distance=distance):
                self.assertEqual(classify_trend(distance), "Neutral")

    def test_trend_more_than_two_percent_below_is_bearish(self):
        self.assertEqual(classify_trend(-2.01), "Bearish")

    def test_earnings_zero_to_seven_days_is_high_risk(self):
        for days in (0, 7):
            with self.subTest(days=days):
                self.assertEqual(classify_earnings_risk(days), "HIGH earnings risk")

    def test_earnings_eight_to_twenty_one_days_is_caution(self):
        for days in (8, 21):
            with self.subTest(days=days):
                self.assertEqual(classify_earnings_risk(days), "CAUTION")

    def test_earnings_more_than_twenty_one_days_is_lower_risk(self):
        self.assertEqual(
            classify_earnings_risk(22),
            "Lower near-term earnings risk",
        )

    def test_unknown_earnings_date_is_unknown_risk(self):
        self.assertEqual(
            classify_earnings_risk(None),
            "UNKNOWN - verify manually",
        )

    def test_snapshot_output_uses_automatic_market_values(self):
        snapshot = build_market_snapshot(
            25,
            24,
            21,
            date(2026, 9, 27),
            45,
            "Retrieved",
        )
        output = StringIO()

        with redirect_stdout(output):
            display_market_snapshot(snapshot)

        rendered = output.getvalue()
        self.assertIn("Current price:        $25.00", rendered)
        self.assertIn("50-day average:       $24.00", rendered)
        self.assertIn("200-day average:      $21.00", rendered)
        self.assertIn("Next earnings:        2026-09-27", rendered)
        self.assertIn("Earnings source:      retrieved", rendered)
        self.assertIn("PUT SELLER VIEW", rendered)

    def test_put_seller_view_warns_when_earnings_date_is_unknown(self):
        snapshot = build_market_snapshot(25, 24, 21, None, 45, "Manual")
        self.assertIn("⚠ Earnings date is unknown", build_put_seller_view(snapshot))


if __name__ == "__main__":
    unittest.main()
