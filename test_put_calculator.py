"""Automated tests for the cash-secured put calculator."""

import unittest

from put_calculator import (
    calculate_iv_rank,
    calculate_put_results,
    calculate_technical_context,
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


if __name__ == "__main__":
    unittest.main()
