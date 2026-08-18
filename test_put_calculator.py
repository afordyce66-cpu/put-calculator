"""Automated tests for the cash-secured put calculator."""

from contextlib import redirect_stdout
from datetime import date
from io import StringIO
import unittest
from unittest.mock import patch

from put_calculator import (
    build_assignment_downside_analysis,
    build_option_candidate_analysis,
    build_position_sizing_analysis,
    build_trade_guardrails,
    calculate_allocation_limit_dollar_value,
    calculate_cash_collateral_required,
    calculate_cash_remaining_after_position,
    calculate_collateral_percentage_of_capital,
    calculate_effective_assigned_cost_basis,
    calculate_iv_rank,
    calculate_breakeven_cushion,
    calculate_max_contracts_by_allocation,
    calculate_max_contracts_by_cash,
    calculate_max_theoretical_loss,
    calculate_put_expiration_pl,
    calculate_put_results,
    calculate_strike_distance,
    calculate_technical_context,
    calculate_total_effective_stock_basis,
    calculate_total_shares,
    build_market_snapshot,
    build_put_seller_view,
    classify_earnings_risk,
    classify_contract_earnings_risk,
    classify_delta,
    classify_strike_distance,
    classify_trend,
    contract_count_exceeds_allocation_limit,
    contract_count_exceeds_cash_limit,
    create_trade_checklist,
    display_market_snapshot,
    display_results,
    earnings_occur_during_trade,
    get_user_inputs,
    validate_inputs,
)
from trade_score import build_trade_quality_score


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

    @patch("put_calculator.get_market_data")
    @patch("builtins.input")
    def test_blank_delta_is_stored_as_unknown(self, mock_input, mock_get):
        """The existing delta prompt may be left blank."""

        # These are the calculator's remaining manual inputs after the ticker.
        inputs = [
            "22", "0.60", "1", "30", "", "45", "25", "65", "65",
            "22.50", "28", "45",
        ]
        mock_input.side_effect = ["SOFI"] + inputs
        mock_get.return_value = {
            "ticker": "SOFI",
            "stock_price": 25.0,
            "ma50": 24.0,
            "ma200": 21.0,
        }

        self.assertIsNone(get_user_inputs()[7])

    @patch("put_calculator.get_market_data")
    @patch("builtins.input")
    def test_negative_put_delta_is_normalized_to_magnitude(
        self, mock_input, mock_get
    ):
        """A conventional negative put delta is accepted as its magnitude."""

        inputs = [
            "22", "0.60", "1", "30", "-0.20", "45", "25", "65", "65",
            "22.50", "28", "45",
        ]
        mock_input.side_effect = ["SOFI"] + inputs
        mock_get.return_value = {
            "ticker": "SOFI",
            "stock_price": 25.0,
            "ma50": 24.0,
            "ma200": 21.0,
        }

        self.assertEqual(get_user_inputs()[7], 0.20)

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

    def test_strike_less_than_two_percent_below_stock(self):
        self.assertEqual(classify_strike_distance(1.99), "Very close to current price")

    def test_strike_two_to_less_than_five_percent_below_stock(self):
        self.assertEqual(
            classify_strike_distance(2), "Moderate distance below current price"
        )
        self.assertEqual(
            classify_strike_distance(4.99), "Moderate distance below current price"
        )

    def test_strike_five_to_less_than_ten_percent_below_stock(self):
        self.assertEqual(classify_strike_distance(5), "Meaningful downside cushion")
        self.assertEqual(
            classify_strike_distance(9.99), "Meaningful downside cushion"
        )

    def test_strike_ten_percent_or_more_below_stock(self):
        self.assertEqual(classify_strike_distance(10), "Large distance below current price")

    def test_strike_above_stock_price(self):
        self.assertIn("In-the-money", classify_strike_distance(-1))

    def test_option_distance_and_breakeven_calculations(self):
        breakeven = 22 - 0.60
        self.assertAlmostEqual(breakeven, 21.40)
        self.assertAlmostEqual(calculate_strike_distance(25, 22), 12.00)
        self.assertAlmostEqual(calculate_breakeven_cushion(25, breakeven), 14.40)

    def test_contract_earnings_during_option(self):
        self.assertIn("HIGH EVENT RISK", classify_contract_earnings_risk(20, 30))

    def test_contract_earnings_one_to_seven_days_after_expiration(self):
        for days in (31, 37):
            with self.subTest(days=days):
                self.assertIn("CAUTION", classify_contract_earnings_risk(days, 30))

    def test_contract_earnings_more_than_seven_days_after_expiration(self):
        self.assertEqual(
            classify_contract_earnings_risk(38, 30),
            "No earnings event during the option contract",
        )

    def test_contract_earnings_unknown(self):
        self.assertIn("UNKNOWN", classify_contract_earnings_risk(45, 30, False))

    def test_delta_point_fifteen_boundary(self):
        self.assertIn("Lower-delta", classify_delta(0.15))

    def test_moderate_delta(self):
        self.assertEqual(classify_delta(-0.20), "Moderate delta")

    def test_higher_exposure_delta(self):
        self.assertEqual(classify_delta(0.30), "Higher assignment exposure")

    def test_aggressive_delta(self):
        self.assertIn("Aggressive delta", classify_delta(0.40))

    def test_blank_or_unknown_delta(self):
        self.assertIn("Unknown", classify_delta(None))

    def test_invalid_delta_classification_is_rejected(self):
        with self.assertRaises(ValueError):
            classify_delta(1.01)

    def test_analysis_reuses_market_snapshot_and_existing_values(self):
        snapshot = build_market_snapshot(
            25, 24, 21, date(2026, 9, 27), 45, "Retrieved"
        )
        analysis = build_option_candidate_analysis(
            25,
            22,
            0.60,
            21.40,
            12.00,
            14.40,
            30,
            2200.00,
            60.00,
            0.20,
            45,
            True,
            snapshot,
        )

        self.assertIs(analysis["snapshot"], snapshot)
        self.assertEqual(analysis["breakeven_price"], 21.40)
        self.assertEqual(analysis["cash_required"], 2200.00)
        self.assertEqual(analysis["maximum_profit"], 60.00)

    def test_manual_earnings_after_expiration_is_used_and_labeled(self):
        context = classify_contract_earnings_risk(45, 30, "Manual")
        self.assertIn("MANUAL ESTIMATE", context)
        self.assertIn("45 days", context)
        self.assertIn("after this 30-day option expiration", context)
        self.assertIn("Verify", context)

    def test_manual_earnings_before_expiration_warns(self):
        context = classify_contract_earnings_risk(20, 30, "Manual")
        self.assertIn("MANUAL WARNING", context)
        self.assertIn("during or by", context)

    def test_manual_earnings_on_expiration_warns(self):
        context = classify_contract_earnings_risk(30, 30, "Manual")
        self.assertIn("MANUAL WARNING", context)
        self.assertIn("30 days", context)

    def test_no_earnings_information_remains_unknown(self):
        context = classify_contract_earnings_risk(None, 30, "Unknown")
        self.assertIn("UNKNOWN", context)

    def test_manual_earnings_analysis_retains_unverified_source(self):
        snapshot = build_market_snapshot(25, 24, 21, None, 45, "Manual")
        analysis = build_option_candidate_analysis(
            25, 22, 0.60, 21.40, 12.00, 14.40, 30, 2200.00, 60.00,
            0.20, 45, "Manual", snapshot,
        )
        self.assertIn("MANUAL ESTIMATE", analysis["earnings_context"])
        self.assertIn("independently", analysis["earnings_context"])

    def test_automatic_earnings_analysis_remains_intact(self):
        context = classify_contract_earnings_risk(20, 30, "Retrieved")
        self.assertEqual(
            context,
            "HIGH EVENT RISK - earnings occur during the option contract",
        )


class AssignmentScenarioTests(unittest.TestCase):
    """Tests for assignment and downside educational scenario analysis."""

    def test_assignment_metrics_for_single_contract(self):
        self.assertEqual(calculate_total_shares(1), 100)
        self.assertAlmostEqual(calculate_effective_assigned_cost_basis(22, 0.60), 21.40)
        self.assertAlmostEqual(calculate_total_effective_stock_basis(22, 0.60, 1), 2140.00)
        self.assertAlmostEqual(
            calculate_max_theoretical_loss(22, 0.60, 1),
            2140.00,
        )

    def test_expiration_pl_at_strike_price(self):
        self.assertAlmostEqual(
            calculate_put_expiration_pl(22, 22, 0.60, 1),
            60.00,
        )

    def test_expiration_pl_at_breakeven_price(self):
        self.assertAlmostEqual(
            calculate_put_expiration_pl(21.40, 22, 0.60, 1),
            0.00,
        )

    def test_expiration_pl_below_breakeven(self):
        self.assertAlmostEqual(
            calculate_put_expiration_pl(20.00, 22, 0.60, 1),
            -140.00,
        )

    def test_expiration_pl_at_zero(self):
        self.assertAlmostEqual(
            calculate_put_expiration_pl(0.00, 22, 0.60, 1),
            -2140.00,
        )

    def test_expiration_pl_multiple_contracts(self):
        self.assertAlmostEqual(
            calculate_put_expiration_pl(20.00, 22, 0.60, 3),
            -420.00,
        )

    def test_zero_premium_sets_expected_values(self):
        self.assertAlmostEqual(calculate_effective_assigned_cost_basis(22, 0), 22.00)
        self.assertAlmostEqual(calculate_put_expiration_pl(20.00, 22, 0.00, 1), -200.00)

    def test_negative_scenario_price_is_invalid(self):
        with self.assertRaises(ValueError):
            calculate_put_expiration_pl(-1.00, 22, 0.60, 1)

    def test_support_unavailable_is_handled(self):
        analysis = build_assignment_downside_analysis(
            stock_price=25.00,
            strike_price=22.00,
            premium_received=0.60,
            number_of_contracts=1,
            breakeven_price=21.40,
            support_price=None,
        )
        self.assertIsNone(analysis["support_price"])
        self.assertIsNone(analysis["support_pl"])

    def test_existing_version_7_put_calculations_are_preserved(self):
        results = calculate_put_results(25, 22, 0.60, 1, 30)
        self.assertAlmostEqual(results[0], 60.00)
        self.assertAlmostEqual(results[1], 21.40)
        self.assertAlmostEqual(results[2], 2200.00)
        self.assertAlmostEqual(results[3], 2.727272727272727)
        self.assertAlmostEqual(results[4], 33.18181818181818)
        self.assertAlmostEqual(results[5], 12.00)
        self.assertAlmostEqual(results[6], 14.400000000000004)


class TradeGuardrailTests(unittest.TestCase):
    """Tests for the concise Version 8.2 guardrail summary."""

    def make_analysis(self, **changes):
        snapshot = build_market_snapshot(
            25,
            24,
            21,
            date(2026, 9, 27),
            45,
            "Retrieved",
        )
        values = {
            "stock_price": 25,
            "strike_price": 22,
            "premium_received": 0.60,
            "breakeven_price": 21.40,
            "strike_distance": 12.00,
            "breakeven_cushion": 14.40,
            "days_to_expiration": 30,
            "cash_required": 2200.00,
            "maximum_profit": 60.00,
            "delta": 0.20,
            "days_until_earnings": 45,
            "earnings_source": "Retrieved",
            "snapshot": snapshot,
        }
        values.update(changes)
        return build_option_candidate_analysis(**values)

    def test_guardrails_work_without_optional_account_inputs(self):
        guardrails = build_trade_guardrails(
            self.make_analysis(),
            build_position_sizing_analysis(22, 1),
        )

        self.assertTrue(
            any(
                "Cash sufficiency: Available capital was not entered" in message
                for message in guardrails["messages"]
            )
        )
        self.assertTrue(
            any(
                "Allocation limit: No user-selected allocation limit was entered" in message
                for message in guardrails["messages"]
            )
        )

    def test_delta_guardrail_reuses_existing_classification(self):
        analysis = self.make_analysis(delta=0.40)
        guardrails = build_trade_guardrails(
            analysis,
            build_position_sizing_analysis(22, 1),
        )

        self.assertEqual(guardrails["delta_context"], classify_delta(0.40))
        self.assertTrue(
            any(classify_delta(0.40) in message for message in guardrails["messages"])
        )

    def test_strike_and_breakeven_guardrails_reuse_existing_classifications(self):
        analysis = self.make_analysis(strike_distance=1.5, breakeven_cushion=-1.0)
        guardrails = build_trade_guardrails(
            analysis,
            build_position_sizing_analysis(22, 1),
        )

        self.assertEqual(guardrails["strike_context"], classify_strike_distance(1.5))
        self.assertIn("strike is very close", guardrails["messages"][1])
        self.assertIn("breakeven is above", guardrails["messages"][2])

    def test_sufficient_cash_and_within_allocation_are_reported(self):
        guardrails = build_trade_guardrails(
            self.make_analysis(),
            build_position_sizing_analysis(22, 1, 10000, 30),
        )

        self.assertTrue(
            any("Within entered available capital" in message for message in guardrails["messages"])
        )
        self.assertTrue(
            any("Within your entered allocation limit" in message for message in guardrails["messages"])
        )
        self.assertFalse(guardrails["cash_limit_exceeded"])
        self.assertFalse(guardrails["allocation_limit_exceeded"])

    def test_insufficient_cash_and_exceeded_allocation_are_reported(self):
        guardrails = build_trade_guardrails(
            self.make_analysis(),
            build_position_sizing_analysis(22, 3, 5000, 20),
        )

        self.assertTrue(
            any(
                "Cash requirement exceeds entered available capital" in message
                for message in guardrails["messages"]
            )
        )
        self.assertTrue(
            any(
                "Exceeds your entered allocation limit" in message
                for message in guardrails["messages"]
            )
        )
        self.assertTrue(guardrails["cash_limit_exceeded"])
        self.assertTrue(guardrails["allocation_limit_exceeded"])

    def test_partial_account_information_remains_optional(self):
        guardrails = build_trade_guardrails(
            self.make_analysis(),
            build_position_sizing_analysis(22, 1, 10000, None),
        )

        self.assertTrue(
            any("Within entered available capital" in message for message in guardrails["messages"])
        )
        self.assertTrue(
            any(
                "No user-selected allocation limit was entered" in message
                for message in guardrails["messages"]
            )
        )

    def test_guardrails_do_not_duplicate_position_sizing_calculations(self):
        position_sizing = build_position_sizing_analysis(22, 1, 10000, 30)
        with patch("put_calculator.calculate_cash_collateral_required") as mock_collateral_required:
            with patch("put_calculator.calculate_allocation_limit_dollar_value") as mock_allocation_limit:
                build_trade_guardrails(self.make_analysis(), position_sizing)

        mock_allocation_limit.assert_not_called()
        mock_collateral_required.assert_not_called()

    def test_existing_score_and_scenario_results_remain_unchanged(self):
        scorecard = build_trade_quality_score(
            30,
            0.20,
            12.00,
            14.40,
            25,
            24,
            21,
            50,
            45,
            "Retrieved",
        )
        scenario = build_assignment_downside_analysis(
            25,
            22,
            0.60,
            1,
            21.40,
            22.50,
        )

        self.assertEqual(scorecard["maximum"], 100)
        self.assertEqual(scorecard["components"]["Delta"]["points"], 15)
        self.assertAlmostEqual(scenario["scenario_results"]["breakeven"], 0.00)

    def test_display_order_places_guardrails_before_scorecard(self):
        output = StringIO()
        with redirect_stdout(output):
            display_results(
                "SOFI", "Manual", 25, 22, 0.60, 1, 30, 60.00, 21.40,
                2200.00, 2.7273, 33.1818, 12.00, 14.40, 0.20, 45.00,
                50.00, 65.00, 22.50, 11.1111, 2.2222, 24.00, 4.1667,
                21.00, 19.0476, 28.00, -10.7143, 45, None, "Manual", None,
                10000, 30,
            )

        rendered = output.getvalue()
        self.assertLess(
            rendered.index("Assignment & Downside Scenarios"),
            rendered.index("Position Sizing & Account Concentration"),
        )
        self.assertLess(
            rendered.index("Position Sizing & Account Concentration"),
            rendered.index("Trade Guardrails"),
        )
        self.assertLess(
            rendered.index("Trade Guardrails"),
            rendered.index("TRADE QUALITY SCORECARD"),
        )


class PositionSizingTests(unittest.TestCase):
    """Tests for optional account concentration and position sizing."""

    def test_optional_fields_left_blank_are_accepted(self):
        analysis = build_position_sizing_analysis(
            strike_price=22,
            number_of_contracts=1,
            available_capital=None,
            max_allocation_percentage=None,
        )
        self.assertIsNone(analysis["available_capital"])
        self.assertIsNone(analysis["max_allocation_percentage"])
        self.assertIsNone(analysis["collateral_percentage"])
        self.assertFalse(analysis["exceeds_cash_limit"])
        self.assertFalse(analysis["exceeds_allocation_limit"])

    def test_exact_allocation_boundary(self):
        analysis = build_position_sizing_analysis(
            strike_price=22,
            number_of_contracts=1,
            available_capital=10000,
            max_allocation_percentage=22,
        )
        self.assertAlmostEqual(analysis["collateral_required"], 2200.00)
        self.assertAlmostEqual(analysis["allocation_limit_dollar_value"], 2200.00)
        self.assertEqual(analysis["max_contracts_by_cash"], 4)
        self.assertEqual(analysis["max_contracts_by_allocation"], 1)
        self.assertFalse(analysis["exceeds_allocation_limit"])

    def test_collateral_below_allocation_limit(self):
        analysis = build_position_sizing_analysis(
            strike_price=22,
            number_of_contracts=1,
            available_capital=10000,
            max_allocation_percentage=30,
        )
        self.assertAlmostEqual(analysis["collateral_percentage"], 22.00)
        self.assertFalse(analysis["exceeds_allocation_limit"])

    def test_collateral_above_allocation_limit(self):
        analysis = build_position_sizing_analysis(
            strike_price=22,
            number_of_contracts=3,
            available_capital=10000,
            max_allocation_percentage=20,
        )
        self.assertTrue(analysis["exceeds_allocation_limit"])
        self.assertEqual(analysis["max_contracts_by_allocation"], 0)

    def test_insufficient_available_cash(self):
        analysis = build_position_sizing_analysis(
            strike_price=22,
            number_of_contracts=5,
            available_capital=10000,
            max_allocation_percentage=50,
        )
        self.assertTrue(analysis["exceeds_cash_limit"])
        self.assertEqual(analysis["max_contracts_by_cash"], 4)

    def test_multiple_contracts(self):
        analysis = build_position_sizing_analysis(
            strike_price=22,
            number_of_contracts=3,
            available_capital=10000,
            max_allocation_percentage=40,
        )
        self.assertAlmostEqual(analysis["collateral_required"], 6600.00)
        self.assertAlmostEqual(analysis["cash_remaining"], 3400.00)
        self.assertAlmostEqual(analysis["collateral_percentage"], 66.00)

    def test_max_contract_rounding_down(self):
        analysis = build_position_sizing_analysis(
            strike_price=22,
            number_of_contracts=1,
            available_capital=5000,
            max_allocation_percentage=15,
        )
        self.assertEqual(analysis["max_contracts_by_cash"], 2)
        self.assertEqual(analysis["max_contracts_by_allocation"], 0)

    def test_invalid_zero_available_capital(self):
        with self.assertRaises(ValueError):
            build_position_sizing_analysis(
                strike_price=22,
                number_of_contracts=1,
                available_capital=0,
                max_allocation_percentage=20,
            )

    def test_invalid_negative_available_capital(self):
        with self.assertRaises(ValueError):
            build_position_sizing_analysis(
                strike_price=22,
                number_of_contracts=1,
                available_capital=-1,
                max_allocation_percentage=20,
            )

    def test_zero_allocation_percentage_is_invalid(self):
        with self.assertRaises(ValueError):
            build_position_sizing_analysis(
                strike_price=22,
                number_of_contracts=1,
                available_capital=10000,
                max_allocation_percentage=0,
            )

    def test_negative_allocation_percentage_is_invalid(self):
        with self.assertRaises(ValueError):
            build_position_sizing_analysis(
                strike_price=22,
                number_of_contracts=1,
                available_capital=10000,
                max_allocation_percentage=-1,
            )

    def test_allocation_percentage_above_100_is_invalid(self):
        with self.assertRaises(ValueError):
            build_position_sizing_analysis(
                strike_price=22,
                number_of_contracts=1,
                available_capital=10000,
                max_allocation_percentage=101,
            )

    def test_position_sizing_preserves_version_8_0_behavior(self):
        result = calculate_put_results(25, 22, 0.60, 1, 30)
        self.assertAlmostEqual(result[0], 60.00)
        self.assertAlmostEqual(result[1], 21.40)
        self.assertAlmostEqual(result[2], 2200.00)


if __name__ == "__main__":
    unittest.main()
