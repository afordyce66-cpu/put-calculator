"""Tests for the pure Streamlit analysis adapter."""

from datetime import date
import unittest

from app import (
    build_streamlit_data_status,
    build_streamlit_scenario_rows,
    calculate_streamlit_analysis,
)
from put_calculator import build_assignment_downside_analysis


class StreamlitAnalysisTests(unittest.TestCase):
    """Verify browser results reuse the existing calculation engine."""

    def values(self, **changes):
        values = {
            "ticker": "SOFI",
            "stock_price": 25.0,
            "ma50": 24.0,
            "ma200": 21.0,
            "strike_price": 22.0,
            "premium_received": 0.60,
            "number_of_contracts": 1,
            "days_to_expiration": 30,
            "delta": 0.20,
            "current_iv": 45.0,
            "iv_low": 25.0,
            "iv_high": 65.0,
            "iv_percentile": 65.0,
            "support_price": 22.50,
            "resistance_price": 28.0,
            "days_until_earnings": 45,
            "next_earnings_date": None,
            "earnings_source": "Manual",
            "available_capital": None,
            "max_allocation_percentage": None,
        }
        values.update(changes)
        return values

    def test_manual_analysis_preserves_core_results(self):
        result = calculate_streamlit_analysis(self.values())

        self.assertAlmostEqual(result["maximum_profit"], 60.0)
        self.assertAlmostEqual(result["breakeven_price"], 21.40)
        self.assertAlmostEqual(result["cash_required"], 2200.0)
        self.assertAlmostEqual(result["annualized_return"], 33.1818, places=3)
        self.assertEqual(result["scorecard"]["maximum"], 100)

    def test_optional_account_inputs_flow_into_existing_sizing(self):
        result = calculate_streamlit_analysis(
            self.values(
                available_capital=10000.0,
                max_allocation_percentage=30.0,
            )
        )

        self.assertAlmostEqual(result["sizing"]["collateral_percentage"], 22.0)
        self.assertAlmostEqual(result["sizing"]["cash_remaining"], 7800.0)
        self.assertFalse(result["sizing"]["exceeds_cash_limit"])
        self.assertFalse(result["sizing"]["exceeds_allocation_limit"])

    def test_retrieved_market_data_replaces_manual_market_values(self):
        result = calculate_streamlit_analysis(
            self.values(stock_price=10.0, ma50=10.0, ma200=10.0),
            market_data={
                "ticker": "SOFI",
                "stock_price": 25.0,
                "ma50": 24.0,
                "ma200": 21.0,
                "next_earnings_date": date(2026, 9, 27),
                "days_until_earnings": 45,
                "source": "Retrieved",
            },
        )

        self.assertEqual(result["market_data_source"], "Retrieved")
        self.assertEqual(result["stock_price"], 25.0)
        self.assertEqual(result["next_earnings_date"], date(2026, 9, 27))
        self.assertEqual(result["days_until_earnings"], 45)

    def test_retrieved_market_data_without_earnings_uses_manual_days_fallback(self):
        values = self.values(days_until_earnings=37)

        result = calculate_streamlit_analysis(
            values,
            market_data={
                "ticker": "SOFI",
                "stock_price": 25.0,
                "ma50": 24.0,
                "ma200": 21.0,
                "next_earnings_date": None,
                "days_until_earnings": None,
                "source": "Retrieved",
            },
        )

        self.assertEqual(result["market_data_source"], "Retrieved")
        self.assertEqual(result["stock_price"], 25.0)
        self.assertEqual(result["ma50"], 24.0)
        self.assertEqual(result["ma200"], 21.0)
        self.assertIsNone(result["next_earnings_date"])
        self.assertEqual(result["days_until_earnings"], 37)

        messages = build_streamlit_data_status(result, values)
        self.assertIn(
            "Market data: Retrieved automatically for the ticker.",
            messages,
        )
        self.assertIn(
            "Earnings: No verified earnings date is available.",
            messages,
        )

    def test_invalid_iv_range_uses_existing_validation(self):
        with self.assertRaises(ValueError):
            calculate_streamlit_analysis(self.values(iv_low=70.0, iv_high=65.0))

    def test_option_reference_data_updates_delta_and_liquidity_score(self):
        option_data = {
            "spread_percentage": 4.0,
            "contract": {
                "delta": -0.30,
                "open_interest": 600,
                "volume": 120,
            },
        }
        result = calculate_streamlit_analysis(
            self.values(delta=0.40),
            option_contract_data=option_data,
        )

        self.assertEqual(result["analysis"]["delta"], 0.30)
        self.assertEqual(result["scorecard"]["components"]["Delta"]["points"], 15)
        self.assertEqual(
            result["scorecard"]["components"]["Bid/ask liquidity"]["points"],
            10,
        )

    def test_scenario_rows_reuse_existing_prices_and_payoffs(self):
        assignment = build_assignment_downside_analysis(
            25.0,
            22.0,
            0.60,
            1,
            21.40,
            22.50,
        )

        rows = build_streamlit_scenario_rows(assignment)

        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["Scenario"], "At strike")
        self.assertEqual(rows[0]["Stock price"], 22.0)
        self.assertEqual(rows[0]["Expiration P/L"], 60.0)
        self.assertIn("Assignment", rows[0]["Educational outcome"])
        self.assertAlmostEqual(rows[1]["Expiration P/L"], 0.0)

    def test_scenario_rows_omit_unavailable_support(self):
        assignment = build_assignment_downside_analysis(
            25.0,
            22.0,
            0.60,
            1,
            21.40,
            None,
        )

        rows = build_streamlit_scenario_rows(assignment)

        self.assertEqual(len(rows), 4)
        self.assertNotIn("At support", [row["Scenario"] for row in rows])

    def test_data_status_explains_manual_and_missing_optional_context(self):
        result = calculate_streamlit_analysis(self.values())

        messages = build_streamlit_data_status(result, self.values())

        self.assertIn("Market data: Manual values are in use.", messages)
        self.assertIn("Earnings: No verified earnings date is available.", messages)
        self.assertIn("Account sizing: Available capital was not entered.", messages)
        self.assertIn("Option-chain reference: Not requested or unavailable.", messages)

    def test_data_status_omits_missing_messages_when_context_is_available(self):
        values = self.values(
            available_capital=10000.0,
            delta=0.20,
        )
        result = calculate_streamlit_analysis(
            values,
            market_data={
                "ticker": "SOFI",
                "stock_price": 25.0,
                "ma50": 24.0,
                "ma200": 21.0,
                "next_earnings_date": date(2026, 9, 27),
                "days_until_earnings": 45,
                "source": "Retrieved",
            },
        )

        messages = build_streamlit_data_status(result, values)

        self.assertIn("Market data: Retrieved automatically for the ticker.", messages)
        self.assertNotIn("Earnings: No verified earnings date is available.", messages)
        self.assertNotIn("Account sizing: Available capital was not entered.", messages)


if __name__ == "__main__":
    unittest.main()
