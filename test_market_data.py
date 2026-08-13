"""Offline tests for market-data retrieval and calculator fallback."""

from datetime import date, timedelta
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from market_data import (
    MarketDataError,
    calculate_days_until_earnings,
    find_next_earnings_date,
    get_market_data,
)
from put_calculator import earnings_occur_during_trade, get_user_inputs


class MarketDataTests(unittest.TestCase):
    """Test market data without contacting Yahoo Finance."""

    @patch("market_data.yf.Ticker")
    def test_successful_retrieval_and_ticker_normalization(self, mock_ticker):
        """Retrieved values use history and normalize the ticker."""

        closes = list(range(1, 202))
        history = pd.DataFrame({"Close": closes})
        mock_ticker.return_value.history.return_value = history

        result = get_market_data("  sofi  ")

        mock_ticker.assert_called_once_with("SOFI")
        self.assertEqual(result["ticker"], "SOFI")
        self.assertEqual(result["stock_price"], 201.0)
        self.assertAlmostEqual(result["ma50"], sum(closes[-50:]) / 50)
        self.assertAlmostEqual(result["ma200"], sum(closes[-200:]) / 200)

    @patch("market_data.yf.Ticker")
    def test_successful_future_earnings_date_retrieval(self, mock_ticker):
        """A future provider date is returned with its calendar-day count."""

        today = date.today()
        future_date = today + timedelta(days=45)
        mock_ticker.return_value.history.return_value = pd.DataFrame(
            {"Close": range(1, 202)}
        )
        mock_ticker.return_value.get_earnings_dates.return_value = pd.DataFrame(
            {"Reported EPS": [None]},
            index=pd.to_datetime([future_date]),
        )

        result = get_market_data("SOFI")

        self.assertEqual(result["next_earnings_date"], future_date)
        self.assertEqual(result["days_until_earnings"], 45)

    def test_days_until_earnings_and_dte_outcomes(self):
        """Calculated days drive inside, outside, and boundary DTE behavior."""

        today = date(2026, 8, 13)
        inside_days = calculate_days_until_earnings(date(2026, 9, 2), today)
        outside_days = calculate_days_until_earnings(date(2026, 9, 27), today)
        boundary_days = calculate_days_until_earnings(date(2026, 9, 12), today)

        self.assertEqual(inside_days, 20)
        self.assertTrue(earnings_occur_during_trade(inside_days, 30))
        self.assertEqual(outside_days, 45)
        self.assertFalse(earnings_occur_during_trade(outside_days, 30))
        self.assertEqual(boundary_days, 30)
        self.assertTrue(earnings_occur_during_trade(boundary_days, 30))

    def test_past_earnings_date_is_rejected(self):
        """A provider response containing only past dates is unusable."""

        earnings_dates = pd.DataFrame(
            {"Reported EPS": [0.10]},
            index=pd.to_datetime(["2026-08-12"]),
        )

        with self.assertRaises(MarketDataError):
            find_next_earnings_date(earnings_dates, date(2026, 8, 13))

    def test_malformed_earnings_date_is_rejected(self):
        """Malformed provider dates do not become invented earnings dates."""

        earnings_dates = pd.DataFrame(
            {"Reported EPS": [None]},
            index=["not-a-date"],
        )

        with self.assertRaises(MarketDataError):
            find_next_earnings_date(earnings_dates, date(2026, 8, 13))

    @patch("market_data.yf.Ticker")
    def test_insufficient_history_raises_error(self, mock_ticker):
        """Fewer than 200 closing prices cannot produce a 200-day MA."""

        mock_ticker.return_value.history.return_value = pd.DataFrame(
            {"Close": range(1, 200)}
        )

        with self.assertRaises(MarketDataError):
            get_market_data("SOFI")

    @patch("market_data.yf.Ticker")
    def test_empty_history_raises_error(self, mock_ticker):
        """An empty provider response is treated as unavailable data."""

        mock_ticker.return_value.history.return_value = pd.DataFrame()

        with self.assertRaises(MarketDataError):
            get_market_data("SOFI")


class CalculatorMarketDataTests(unittest.TestCase):
    """Test automatic values and manual fallback in calculator input."""

    def remaining_inputs(self):
        """Return inputs that remain manual after successful retrieval."""

        return [
            "22", "0.60", "1", "30", "0.20", "45", "25", "65", "65",
            "22.50", "28", "45",
        ]

    def inputs_without_manual_earnings(self):
        """Return remaining inputs when earnings timing is automatic."""

        return self.remaining_inputs()[:-1]

    @patch("put_calculator.get_market_data")
    @patch("builtins.input")
    def test_automatic_earnings_data_skips_manual_prompt(
        self, mock_input, mock_get
    ):
        """A valid retrieved date supplies days until earnings automatically."""

        next_date = date.today() + timedelta(days=45)
        mock_input.side_effect = ["sofi"] + self.inputs_without_manual_earnings()
        mock_get.return_value = {
            "ticker": "SOFI",
            "stock_price": 25.0,
            "ma50": 24.0,
            "ma200": 21.0,
            "next_earnings_date": next_date,
            "days_until_earnings": 45,
        }

        results = get_user_inputs()

        self.assertEqual(results[16], 45)
        self.assertEqual(results[17], next_date)
        self.assertEqual(results[18], "Retrieved")

    @patch("put_calculator.get_market_data")
    @patch("builtins.input")
    def test_missing_earnings_date_uses_manual_earnings_fallback(
        self, mock_input, mock_get
    ):
        """Missing earnings fields prompt only for manual earnings timing."""

        mock_input.side_effect = ["SOFI"] + self.remaining_inputs()
        mock_get.return_value = {
            "ticker": "SOFI",
            "stock_price": 25.0,
            "ma50": 24.0,
            "ma200": 21.0,
            "next_earnings_date": None,
            "days_until_earnings": None,
        }

        results = get_user_inputs()

        self.assertEqual(results[1], "Retrieved")
        self.assertEqual(results[16], 45)
        self.assertIsNone(results[17])
        self.assertEqual(results[18], "Manual")

    @patch("put_calculator.get_market_data")
    @patch("builtins.input")
    def test_malformed_earnings_date_uses_manual_earnings_fallback(
        self, mock_input, mock_get
    ):
        """A malformed earnings field uses the manual earnings prompt."""

        mock_input.side_effect = ["SOFI"] + self.remaining_inputs()
        mock_get.return_value = {
            "ticker": "SOFI",
            "stock_price": 25.0,
            "ma50": 24.0,
            "ma200": 21.0,
            "next_earnings_date": "not-a-date",
            "days_until_earnings": 45,
        }

        results = get_user_inputs()

        self.assertEqual(results[1], "Retrieved")
        self.assertEqual(results[16], 45)
        self.assertEqual(results[18], "Manual")

    @patch("put_calculator.get_market_data")
    @patch("builtins.input")
    def test_past_earnings_data_uses_manual_earnings_fallback(
        self, mock_input, mock_get
    ):
        """Negative retrieved days use the manual earnings prompt."""

        mock_input.side_effect = ["SOFI"] + self.remaining_inputs()
        mock_get.return_value = {
            "ticker": "SOFI",
            "stock_price": 25.0,
            "ma50": 24.0,
            "ma200": 21.0,
            "next_earnings_date": date.today() - timedelta(days=1),
            "days_until_earnings": -1,
        }

        results = get_user_inputs()

        self.assertEqual(results[1], "Retrieved")
        self.assertEqual(results[16], 45)
        self.assertEqual(results[18], "Manual")

    @patch("put_calculator.get_market_data")
    @patch("builtins.input")
    def test_calculator_uses_all_automatic_values(self, mock_input, mock_get):
        """The calculator uses automatic stock price, MA50, and MA200."""

        mock_input.side_effect = ["sofi"] + self.remaining_inputs()
        mock_get.return_value = {
            "ticker": "SOFI",
            "stock_price": 25.0,
            "ma50": 24.0,
            "ma200": 21.0,
        }

        results = get_user_inputs()

        self.assertEqual(results[0], "SOFI")
        self.assertEqual(results[1], "Retrieved")
        self.assertEqual(results[2], 25.0)
        self.assertEqual(results[13], 24.0)
        self.assertEqual(results[14], 21.0)
        mock_get.assert_called_once_with("SOFI")

    @patch("put_calculator.get_market_data", side_effect=RuntimeError("offline"))
    @patch("builtins.input")
    def test_retrieval_failure_uses_manual_fallback(self, mock_input, mock_get):
        """A retrieval exception prompts for all three manual market values."""

        manual_market_values = ["25", "24", "21"]
        mock_input.side_effect = (
            ["sofi"] + manual_market_values + self.remaining_inputs()
        )

        results = get_user_inputs()

        self.assertEqual(results[1], "Manual")
        self.assertEqual(results[2], 25.0)
        self.assertEqual(results[13], 24.0)
        self.assertEqual(results[14], 21.0)

    @patch("put_calculator.get_market_data", return_value={})
    @patch("builtins.input")
    def test_empty_market_data_uses_manual_fallback(self, mock_input, mock_get):
        """An empty market-data result also uses manual entry."""

        mock_input.side_effect = (
            ["SOFI", "25", "24", "21"] + self.remaining_inputs()
        )

        results = get_user_inputs()

        self.assertEqual(results[1], "Manual")
        self.assertEqual(results[2], 25.0)
        self.assertEqual(results[13], 24.0)
        self.assertEqual(results[14], 21.0)


if __name__ == "__main__":
    unittest.main()
