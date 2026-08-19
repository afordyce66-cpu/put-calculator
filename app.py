"""Streamlit interface for the beginner cash-secured put analyzer."""

from datetime import date

import streamlit as st

from market_data import get_market_data
from option_chain import get_put_contract
from put_calculator import (
    build_assignment_downside_analysis,
    build_expiration_outcome_guide,
    build_market_snapshot,
    build_option_candidate_analysis,
    build_position_sizing_analysis,
    build_trade_guardrails,
    calculate_iv_rank,
    calculate_put_results,
    calculate_technical_context,
    select_effective_delta,
    validate_inputs,
    validate_position_sizing_inputs,
)
from trade_score import build_trade_quality_score


def calculate_streamlit_analysis(
    values,
    market_data=None,
    option_contract_data=None,
):
    """Build all browser results using the existing calculator engine."""

    if market_data is None:
        market_data = {
            "ticker": values["ticker"].strip().upper(),
            "stock_price": values["stock_price"],
            "ma50": values["ma50"],
            "ma200": values["ma200"],
            "next_earnings_date": values.get("next_earnings_date"),
            "days_until_earnings": values["days_until_earnings"],
        }

    ticker = market_data.get("ticker", values["ticker"]).strip().upper()
    stock_price = float(market_data["stock_price"])
    ma50 = float(market_data["ma50"])
    ma200 = float(market_data["ma200"])
    next_earnings_date = market_data.get("next_earnings_date")
    days_until_earnings = int(market_data["days_until_earnings"])
    earnings_source = values.get("earnings_source", "Manual")
    if market_data.get("source") == "Retrieved" and next_earnings_date is not None:
        earnings_source = "Retrieved"

    validate_inputs(
        stock_price,
        values["strike_price"],
        values["premium_received"],
        values["number_of_contracts"],
        values["days_to_expiration"],
        values["delta"],
        values["iv_low"],
        values["iv_high"],
        values["iv_percentile"],
        values["support_price"],
        ma50,
        ma200,
        values["resistance_price"],
        days_until_earnings,
    )
    validate_position_sizing_inputs(
        values.get("available_capital"),
        values.get("max_allocation_percentage"),
    )

    results = calculate_put_results(
        stock_price,
        values["strike_price"],
        values["premium_received"],
        values["number_of_contracts"],
        values["days_to_expiration"],
    )
    (
        maximum_profit,
        breakeven_price,
        cash_required,
        return_on_capital,
        annualized_return,
        strike_cushion,
        breakeven_cushion,
    ) = results

    iv_rank = calculate_iv_rank(
        values["current_iv"],
        values["iv_low"],
        values["iv_high"],
    )
    (
        support_distance,
        strike_vs_support,
        ma50_distance,
        ma200_distance,
        price_vs_resistance,
    ) = calculate_technical_context(
        stock_price,
        values["strike_price"],
        values["support_price"],
        ma50,
        ma200,
        values["resistance_price"],
    )

    snapshot = build_market_snapshot(
        stock_price,
        ma50,
        ma200,
        next_earnings_date,
        days_until_earnings,
        earnings_source,
    )
    analysis_delta = select_effective_delta(option_contract_data, values["delta"])
    analysis = build_option_candidate_analysis(
        stock_price,
        values["strike_price"],
        values["premium_received"],
        breakeven_price,
        strike_cushion,
        breakeven_cushion,
        values["days_to_expiration"],
        cash_required,
        maximum_profit,
        analysis_delta,
        days_until_earnings,
        earnings_source,
        snapshot,
    )
    assignment = build_assignment_downside_analysis(
        stock_price,
        values["strike_price"],
        values["premium_received"],
        values["number_of_contracts"],
        breakeven_price,
        values["support_price"],
    )
    sizing = build_position_sizing_analysis(
        values["strike_price"],
        values["number_of_contracts"],
        values.get("available_capital"),
        values.get("max_allocation_percentage"),
    )
    guide = build_expiration_outcome_guide(assignment, sizing)
    guardrails = build_trade_guardrails(analysis, sizing)
    spread_percentage = None
    open_interest = None
    volume = None
    if option_contract_data is not None:
        spread_percentage = option_contract_data["spread_percentage"]
        open_interest = option_contract_data["contract"]["open_interest"]
        volume = option_contract_data["contract"]["volume"]
    scorecard = build_trade_quality_score(
        values["days_to_expiration"],
        analysis_delta,
        strike_cushion,
        breakeven_cushion,
        stock_price,
        ma50,
        ma200,
        iv_rank,
        days_until_earnings,
        earnings_source,
        spread_percentage,
        open_interest,
        volume,
    )

    return {
        "ticker": ticker,
        "market_data_source": market_data.get("source", "Manual"),
        "stock_price": stock_price,
        "ma50": ma50,
        "ma200": ma200,
        "next_earnings_date": next_earnings_date,
        "days_until_earnings": days_until_earnings,
        "maximum_profit": maximum_profit,
        "breakeven_price": breakeven_price,
        "cash_required": cash_required,
        "return_on_capital": return_on_capital,
        "annualized_return": annualized_return,
        "strike_cushion": strike_cushion,
        "breakeven_cushion": breakeven_cushion,
        "iv_rank": iv_rank,
        "support_distance": support_distance,
        "strike_vs_support": strike_vs_support,
        "ma50_distance": ma50_distance,
        "ma200_distance": ma200_distance,
        "price_vs_resistance": price_vs_resistance,
        "analysis": analysis,
        "assignment": assignment,
        "sizing": sizing,
        "guide": guide,
        "guardrails": guardrails,
        "scorecard": scorecard,
        "option_contract_data": option_contract_data,
    }


def _money(value):
    return f"${value:,.2f}"


def build_streamlit_scenario_rows(assignment_analysis):
    """Return beginner-friendly scenario rows from existing payoff results."""

    labels = {
        "strike": "At strike",
        "breakeven": "At breakeven",
        "current_minus_10_percent": "Current price minus 10%",
        "support": "At support",
        "zero": "At $0",
    }
    rows = []
    for key, label in labels.items():
        price = assignment_analysis["scenario_prices"].get(key)
        expiration_pl = assignment_analysis["scenario_results"].get(key)
        if price is None or expiration_pl is None:
            continue
        if key == "strike":
            outcome = "Assignment may occur at the strike."
        elif key == "breakeven":
            outcome = "Combined expiration P/L is approximately zero."
        elif expiration_pl >= 0:
            outcome = "Premium offsets the modeled stock decline."
        else:
            outcome = "Modeled expiration loss after assignment exposure."
        rows.append(
            {
                "Scenario": label,
                "Stock price": price,
                "Expiration P/L": expiration_pl,
                "Educational outcome": outcome,
            }
        )
    return tuple(rows)


def _render_snapshot(results, values):
    st.subheader("Trade Snapshot")
    st.caption("Existing calculator results, summarized before the detailed analysis.")
    columns = st.columns(4)
    metrics = (
        ("Strike", _money(values["strike_price"])),
        ("Premium / share", _money(values["premium_received"])),
        ("Breakeven", _money(results["breakeven_price"])),
        ("DTE", str(values["days_to_expiration"])),
        ("Cash collateral", _money(results["cash_required"])),
        ("Max gross premium", _money(results["maximum_profit"])),
        ("Return on capital", f"{results['return_on_capital']:.2f}%"),
        ("Annualized return", f"{results['annualized_return']:.2f}%"),
    )
    for index, (label, value) in enumerate(metrics):
        columns[index % 4].metric(label, value)
    st.info(
        "Maximum gross premium assumes the put expires worthless and excludes "
        "commissions, fees, taxes, and other transaction effects."
    )


def _render_risk_summary(results, values):
    scorecard = results["scorecard"]
    st.subheader("Quick Risk Summary")
    score_columns = st.columns(3)
    score_columns[0].metric("Trade Quality Score", f"{scorecard['total']} / 100")
    score_columns[1].metric("Assessment", scorecard["assessment"])
    score_columns[2].metric("Breakeven cushion", f"{results['breakeven_cushion']:.2f}%")

    for message in results["guardrails"]["messages"]:
        lowered = message.lower()
        if (
            "exceeds" in lowered
            or "worth reviewing" in lowered
            or "warning" in lowered
            or "high event risk" in lowered
        ):
            st.warning(message)
        elif "within" in lowered:
            st.success(message)
        else:
            st.info(message)

    if scorecard["positive_factors"]:
        with st.expander("Positive factors"):
            for factor in scorecard["positive_factors"]:
                st.write(f"- {factor}")
    if scorecard["concerns"]:
        with st.expander("Concerns to review"):
            for concern in scorecard["concerns"]:
                st.write(f"- {concern}")


def _render_outcomes(results):
    st.subheader("Assignment and Expiration Outcomes")
    assignment = results["assignment"]
    guide = results["guide"]
    st.write(
        f"If assigned, the effective cost basis is {_money(guide['effective_assigned_cost_basis'])} "
        f"per share for {assignment['total_shares']:.0f} shares."
    )
    for _, message in guide["states"]:
        st.write(f"- {message}")
    st.dataframe(
        build_streamlit_scenario_rows(assignment),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Stock price": st.column_config.NumberColumn(format="$%.2f"),
            "Expiration P/L": st.column_config.NumberColumn(format="$%.2f"),
        },
    )
    with st.expander("Downside scenario details"):
        st.write(
            f"Maximum theoretical loss at $0: {_money(assignment['maximum_theoretical_loss'])}."
        )


def _render_capital(results):
    st.subheader("Position Sizing and Account Concentration")
    sizing = results["sizing"]
    columns = st.columns(3)
    columns[0].metric("Collateral required", _money(sizing["collateral_required"]))
    columns[1].metric(
        "Capital used",
        "Not calculated"
        if sizing["collateral_percentage"] is None
        else f"{sizing['collateral_percentage']:.2f}%",
    )
    columns[2].metric(
        "Cash remaining",
        "Not calculated"
        if sizing["cash_remaining"] is None
        else _money(sizing["cash_remaining"]),
    )
    if sizing["available_capital"] is None:
        st.info("Available capital was not entered; account sizing remains informational.")
    else:
        st.write(f"Maximum contracts by cash: {sizing['max_contracts_by_cash']}")
        st.write(
            "Maximum contracts by allocation: "
            f"{sizing['max_contracts_by_allocation']}"
        )


def _render_market_context(results, values):
    st.subheader("Market and Technical Context")
    columns = st.columns(3)
    columns[0].metric("Stock price", _money(results["stock_price"]))
    columns[1].metric("50-day average", _money(results["ma50"]))
    columns[2].metric("200-day average", _money(results["ma200"]))
    st.write(
        f"Strike versus support: {results['strike_vs_support']:.2f}%. "
        f"Price versus resistance: {results['price_vs_resistance']:.2f}%."
    )
    st.write(
        f"IV Rank: {results['iv_rank']:.2f}%. "
        f"IV Percentile: {values['iv_percentile']:.2f}%."
    )
    if results["next_earnings_date"] is None:
        st.write("Earnings timing: manual estimate or unavailable.")
    else:
        st.write(
            f"Next earnings: {results['next_earnings_date'].isoformat()} "
            f"({results['days_until_earnings']} days)."
        )


def _render_option_reference(results):
    option_data = results["option_contract_data"]
    if option_data is None:
        st.info("No option-chain reference data was requested or available.")
        return
    contract = option_data["contract"]
    with st.expander("Option-chain reference data"):
        st.write(f"Selected expiration: {option_data['expiration_date'].isoformat()}")
        st.write(f"Listed strike: {_money(contract['strike'])}")
        st.write(
            f"Bid / ask: {_money(contract['bid'])} / {_money(contract['ask'])}"
        )
        st.write(f"Spread context: {option_data['spread_context']}")
        st.write(
            "Volume: "
            f"{contract['volume'] if contract['volume'] is not None else 'Unavailable'}"
        )
        st.write(
            "Open interest: "
            f"{contract['open_interest'] if contract['open_interest'] is not None else 'Unavailable'}"
        )


def _load_market_data(ticker):
    """Load market data for the form while preserving manual fallback."""

    market_data = get_market_data(ticker)
    market_data["source"] = "Retrieved"
    return market_data


def main():
    st.set_page_config(page_title="StockPut Analyzer", page_icon="📊", layout="wide")
    st.title("StockPut Analyzer")
    st.caption("A beginner-friendly cash-secured put calculator. Educational analysis only.")

    with st.form("put_analysis_form"):
        st.subheader("Ticker and Market Data")
        ticker = st.text_input("Ticker symbol", value="SOFI").strip().upper()
        use_market_data = st.checkbox("Retrieve market data automatically", value=True)
        use_option_chain = st.checkbox(
            "Retrieve optional option-chain reference data",
            value=False,
        )

        st.subheader("Put Contract Inputs")
        contract_columns = st.columns(4)
        stock_price = contract_columns[0].number_input("Stock price", min_value=0.01, value=25.0)
        strike_price = contract_columns[1].number_input("Strike price", min_value=0.01, value=22.0)
        premium_received = contract_columns[2].number_input("Premium per share", min_value=0.0, value=0.60)
        number_of_contracts = contract_columns[3].number_input("Contracts", min_value=1, value=1, step=1)
        days_to_expiration = st.number_input("Days to expiration", min_value=1, value=30, step=1)

        st.subheader("Volatility and Technical Inputs")
        volatility_columns = st.columns(4)
        delta_available = volatility_columns[0].checkbox("Delta available", value=True)
        delta = volatility_columns[1].number_input("Put delta", min_value=0.0, max_value=1.0, value=0.20, disabled=not delta_available)
        current_iv = volatility_columns[2].number_input("Current IV (%)", min_value=0.0, value=45.0)
        iv_percentile = volatility_columns[3].number_input("IV Percentile (%)", min_value=0.0, max_value=100.0, value=65.0)
        range_columns = st.columns(4)
        iv_low = range_columns[0].number_input("52-week IV low (%)", min_value=0.0, value=25.0)
        iv_high = range_columns[1].number_input("52-week IV high (%)", min_value=0.0, value=65.0)
        support_price = range_columns[2].number_input("Estimated support", min_value=0.01, value=22.50)
        resistance_price = range_columns[3].number_input("Estimated resistance", min_value=0.01, value=28.0)
        average_columns = st.columns(2)
        ma50 = average_columns[0].number_input("50-day moving average", min_value=0.01, value=24.0)
        ma200 = average_columns[1].number_input("200-day moving average", min_value=0.01, value=21.0)
        days_until_earnings = st.number_input("Days until earnings", min_value=0, value=45, step=1)

        st.subheader("Optional Account and Allocation Inputs")
        account_columns = st.columns(2)
        account_available = account_columns[0].checkbox("Enter available capital", value=False)
        available_capital = account_columns[1].number_input("Available capital", min_value=0.01, value=10000.0, disabled=not account_available)
        allocation_available = st.checkbox("Enter a maximum allocation percentage", value=False)
        max_allocation_percentage = st.number_input("Maximum allocation (%)", min_value=0.01, max_value=100.0, value=30.0, disabled=not allocation_available)
        submitted = st.form_submit_button("Analyze put")

    if not submitted:
        st.info("Enter the trade details and select Analyze put to see the existing calculator analysis.")
        return

    values = {
        "ticker": ticker,
        "stock_price": stock_price,
        "ma50": ma50,
        "ma200": ma200,
        "strike_price": strike_price,
        "premium_received": premium_received,
        "number_of_contracts": number_of_contracts,
        "days_to_expiration": days_to_expiration,
        "delta": delta if delta_available else None,
        "current_iv": current_iv,
        "iv_low": iv_low,
        "iv_high": iv_high,
        "iv_percentile": iv_percentile,
        "support_price": support_price,
        "resistance_price": resistance_price,
        "days_until_earnings": days_until_earnings,
        "earnings_source": "Manual",
        "available_capital": available_capital if account_available else None,
        "max_allocation_percentage": max_allocation_percentage if allocation_available else None,
    }

    market_data = None
    if use_market_data:
        try:
            market_data = _load_market_data(ticker)
            st.success("Market data retrieved automatically.")
        except Exception as error:
            st.warning(f"Automatic market data unavailable; using manual values. ({error})")

    option_contract_data = None
    if use_option_chain:
        try:
            option_contract_data = get_put_contract(
                ticker,
                days_to_expiration,
                strike_price,
            )
            st.success(
                "Option-chain reference data retrieved. Manual strike and premium remain in use."
            )
        except Exception as error:
            st.warning(f"Option-chain reference data unavailable. ({error})")

    try:
        results = calculate_streamlit_analysis(
            values,
            market_data,
            option_contract_data,
        )
    except ValueError as error:
        st.error(str(error))
        return

    _render_snapshot(results, values)
    _render_risk_summary(results, values)
    _render_outcomes(results)
    _render_capital(results)
    _render_market_context(results, values)
    _render_option_reference(results)

    with st.expander("Detailed Trade Quality Score"):
        for name, component in results["scorecard"]["components"].items():
            st.write(f"{name}: {component['points']} / {component['maximum']} - {component['detail']}")
    st.caption("The existing score is an educational screening tool, not a prediction or recommendation.")


if __name__ == "__main__":
    main()
