"""Offline tests for optional put option-chain retrieval."""

from datetime import date
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from option_chain import (
    OptionChainError,
    calculate_midpoint,
    calculate_spread,
    classify_spread,
    get_put_contract,
    normalize_put_contract,
    select_closest_expiration,
    select_nearest_strike,
)
from put_calculator import get_user_inputs, select_effective_delta


class OptionChainCalculationTests(unittest.TestCase):
    """Test option selection and quote calculations without a network."""

    def test_expiration_closest_to_requested_dte(self):
        expiration, actual_dte = select_closest_expiration(
            ["2026-09-11", "2026-09-18", "2026-10-16"],
            30,
            date(2026, 8, 14),
        )
        self.assertEqual(expiration, date(2026, 9, 11))
        self.assertEqual(actual_dte, 28)

    def test_requested_expiration_unavailable(self):
        with self.assertRaises(OptionChainError):
            select_closest_expiration([], 30, date(2026, 8, 14))

    def test_nearest_listed_strike(self):
        contracts = [{"strike": 20.0}, {"strike": 22.5}, {"strike": 25.0}]
        self.assertEqual(select_nearest_strike(contracts, 23.0)["strike"], 22.5)

    def test_exact_listed_strike(self):
        contracts = [{"strike": 20.0}, {"strike": 22.5}, {"strike": 25.0}]
        self.assertEqual(select_nearest_strike(contracts, 25.0)["strike"], 25.0)

    def test_midpoint_calculation(self):
        self.assertAlmostEqual(calculate_midpoint(0.90, 1.10), 1.00)

    def test_spread_and_percentage_calculation(self):
        spread, percentage = calculate_spread(0.90, 1.10)
        self.assertAlmostEqual(spread, 0.20)
        self.assertAlmostEqual(percentage, 20.0)

    def test_spread_classifications(self):
        self.assertEqual(classify_spread(4.9), "Narrower spread")
        self.assertEqual(classify_spread(5), "Moderate spread")
        self.assertEqual(classify_spread(15), "Moderate spread")
        self.assertIn("Wide spread", classify_spread(15.1))

    def test_missing_bid_prevents_midpoint(self):
        self.assertIsNone(calculate_midpoint(None, 1.10))

    def test_missing_ask_prevents_midpoint(self):
        self.assertIsNone(calculate_midpoint(0.90, None))

    def test_missing_optional_contract_fields_are_preserved_as_none(self):
        contract = normalize_put_contract(
            {"strike": 22.0, "bid": 0.50, "ask": 0.70},
            date(2026, 9, 18),
        )
        self.assertIsNone(contract["implied_volatility"])
        self.assertIsNone(contract["volume"])
        self.assertIsNone(contract["open_interest"])
        self.assertIsNone(contract["delta"])

    def test_empty_option_chain_is_rejected(self):
        with self.assertRaises(OptionChainError):
            select_nearest_strike([], 22.0)

    def test_invalid_ticker_is_rejected(self):
        with self.assertRaises(OptionChainError):
            get_put_contract("   ", 30, 22.0)

    def test_provider_delta_used_only_when_supplied(self):
        option_data = {"contract": {"delta": -0.22}}
        self.assertEqual(select_effective_delta(option_data, 0.30), 0.22)

    def test_manual_delta_preserved_when_provider_delta_absent(self):
        option_data = {"contract": {"delta": None}}
        self.assertEqual(select_effective_delta(option_data, 0.20), 0.20)


class OptionChainProviderTests(unittest.TestCase):
    """Test one mocked yfinance option lookup."""

    def put_rows(self):
        """Return a representative provider put table."""

        return pd.DataFrame(
            [
                {
                    "strike": 22.0,
                    "bid": 0.50,
                    "ask": 0.70,
                    "lastPrice": 0.60,
                    "impliedVolatility": 0.426,
                    "volume": 25,
                    "openInterest": 300,
                    "inTheMoney": False,
                },
                {
                    "strike": 25.0,
                    "bid": 1.00,
                    "ask": 1.10,
                    "lastPrice": 1.05,
                    "impliedVolatility": 0.45,
                    "volume": 50,
                    "openInterest": 500,
                    "inTheMoney": False,
                },
            ]
        )

    @patch("option_chain.yf.Ticker")
    def test_successful_automatic_contract_lookup_and_single_chain_call(
        self, mock_ticker
    ):
        stock = mock_ticker.return_value
        stock.options = ("2026-09-11", "2026-09-18")
        stock.option_chain.return_value = MagicMock(puts=self.put_rows())

        result = get_put_contract(
            "sofi",
            30,
            22.25,
            today=date(2026, 8, 14),
        )

        self.assertEqual(result["ticker"], "SOFI")
        self.assertEqual(result["expiration_date"], date(2026, 9, 11))
        self.assertEqual(result["contract"]["strike"], 22.0)
        self.assertAlmostEqual(result["midpoint"], 0.60)
        stock.option_chain.assert_called_once_with("2026-09-11")

    @patch("option_chain.yf.Ticker")
    def test_empty_provider_chain_raises_error(self, mock_ticker):
        stock = mock_ticker.return_value
        stock.options = ("2026-09-11",)
        stock.option_chain.return_value = MagicMock(puts=pd.DataFrame())

        with self.assertRaises(OptionChainError):
            get_put_contract("SOFI", 30, 22.0, date(2026, 8, 14))

    @patch("option_chain.yf.Ticker", side_effect=RuntimeError("offline"))
    def test_provider_network_exception_is_normalized(self, mock_ticker):
        with self.assertRaises(OptionChainError):
            get_put_contract("SOFI", 30, 22.0, date(2026, 8, 14))


class OptionChainFallbackTests(unittest.TestCase):
    """Test graceful calculator fallback when optional lookup fails."""

    @patch("put_calculator.get_put_contract", side_effect=OptionChainError("offline"))
    @patch("put_calculator.get_market_data")
    @patch("builtins.input")
    def test_option_failure_continues_manual_workflow(
        self, mock_input, mock_market_data, mock_option_data
    ):
        mock_market_data.return_value = {
            "ticker": "SOFI",
            "stock_price": 25.0,
            "ma50": 24.0,
            "ma200": 21.0,
        }
        mock_input.side_effect = [
            "SOFI", "22", "0.60", "1", "30", "0.20", "45", "25", "65",
            "65", "22.50", "28", "45", "y",
        ]

        results = get_user_inputs()

        self.assertEqual(results[4], 0.60)
        self.assertEqual(results[7], 0.20)
        self.assertIsNone(results[19])


if __name__ == "__main__":
    unittest.main()
