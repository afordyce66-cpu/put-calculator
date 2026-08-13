"""Offline tests for market-data retrieval and calculator fallback."""

import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from market_data import MarketDataError, get_market_data
from put_calculator import get_user_inputs


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
