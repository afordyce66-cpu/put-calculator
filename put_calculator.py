"""Calculate the basic numbers for a cash-secured put option."""

from datetime import date

from market_data import get_market_data
from option_chain import OptionChainError, get_put_contract
from trade_score import build_trade_quality_score


# This function asks the user for the trade and volatility information.
# It converts prices and percentages to decimal numbers and counts to whole
# numbers. Finally, it returns the values so another function can use them.
def get_user_inputs():
    """Ask for and return the details of the put option trade."""

    # Try to retrieve the latest available close and moving averages first.
    ticker = input("Ticker symbol: ").strip().upper()
    next_earnings_date = None
    days_until_earnings = None
    try:
        market_data = get_market_data(ticker)
        ticker = market_data["ticker"]

        stock_price_value = market_data.get("stock_price")
        ma50_value = market_data.get("ma50")
        ma200_value = market_data.get("ma200")
        if not isinstance(stock_price_value, (int, float)):
            raise ValueError("Retrieved stock price was unavailable.")
        if not isinstance(ma50_value, (int, float)):
            raise ValueError("Retrieved 50-day average was unavailable.")
        if not isinstance(ma200_value, (int, float)):
            raise ValueError("Retrieved 200-day average was unavailable.")

        stock_price = float(stock_price_value)
        ma50 = float(ma50_value)
        ma200 = float(ma200_value)
        market_data_source = "Retrieved"

        try:
            next_earnings_date = market_data.get("next_earnings_date")
            days_until_earnings_value = market_data.get("days_until_earnings")
            if not isinstance(days_until_earnings_value, (int, float)):
                raise ValueError("Retrieved earnings timing was unavailable.")
            days_until_earnings = int(days_until_earnings_value)
            if not isinstance(next_earnings_date, date):
                raise ValueError("The retrieved earnings date was malformed.")
            if days_until_earnings < 0:
                raise ValueError("The retrieved earnings date is in the past.")
            earnings_data_source = "Retrieved"
        except (TypeError, ValueError):
            next_earnings_date = None
            days_until_earnings = None
            earnings_data_source = "Manual"

        print("\nMarket data retrieved automatically:")
        print(f"Ticker:               {ticker}")
        print(f"Latest closing price: ${stock_price:,.2f}")
        print(f"50-Day MA:            ${ma50:,.2f}")
        print(f"200-Day MA:           ${ma200:,.2f}")
        if (
            earnings_data_source == "Retrieved"
            and isinstance(next_earnings_date, date)
        ):
            print(f"Next Earnings Date:   {next_earnings_date.isoformat()}")
            print(f"Days Until Earnings:  {days_until_earnings}")
    except Exception:
        # Any provider, connection, ticker, or data-format problem uses fallback.
        print("\nAutomatic market data unavailable.")
        print("Switching to manual entry.")
        stock_price = float(input("Stock price: $"))
        ma50 = float(input("50-day moving average: $"))
        ma200 = float(input("200-day moving average: $"))
        market_data_source = "Manual"
        next_earnings_date = None
        earnings_data_source = "Manual"

    if earnings_data_source == "Manual":
        print("\nAutomatic earnings date unavailable.")
        print("Please enter days until earnings manually.")

    # input() returns text, and float() converts it to a decimal number.
    strike_price = float(input("Strike price: $"))
    premium_received = float(input("Premium received per share: $"))

    # int() converts the user's text to a whole number.
    number_of_contracts = int(input("Number of contracts: "))
    days_to_expiration = int(input("Days to expiration: "))

    # Delta is optional. A conventional negative put delta is normalized to
    # its magnitude so -0.20 and 0.20 receive the same informational context.
    delta_entry = input("Put delta (optional; press Enter if unknown): ").strip()
    delta = None if delta_entry == "" else abs(float(delta_entry))

    # IV percentages are entered as normal numbers, such as 45 for 45%.
    current_iv = float(input("Current IV percentage: "))
    iv_low = float(input("52-week IV low percentage: "))
    iv_high = float(input("52-week IV high percentage: "))
    iv_percentile = float(input("IV Percentile (0 to 100): "))

    # These prices provide technical context entered by the user.
    support_price = float(input("Estimated support price: $"))

    # Resistance and earnings timing are entered manually by the user.
    resistance_price = float(input("Estimated resistance price: $"))
    if earnings_data_source == "Manual":
        days_until_earnings = int(input("Days until earnings: "))

    # Option-chain lookup is optional and never replaces manual trade inputs.
    try:
        option_choice = input(
            "Retrieve automatic put option data? (y/N): "
        ).strip().lower()
    except (EOFError, StopIteration):
        # This also preserves compatibility with older scripted input sequences.
        option_choice = ""

    option_contract_data = None
    if option_choice in ("y", "yes"):
        try:
            option_contract_data = get_put_contract(
                ticker,
                days_to_expiration,
                strike_price,
            )
            print("Automatic option-chain data retrieved.")
            print("Manual strike and premium remain the calculator inputs.")
        except Exception as error:
            print(f"Automatic option data unavailable: {error}")
            print("Continuing with the existing manual workflow.")

    # return sends these values back to the line that called this function.
    return (
        ticker,
        market_data_source,
        stock_price,
        strike_price,
        premium_received,
        number_of_contracts,
        days_to_expiration,
        delta,
        current_iv,
        iv_low,
        iv_high,
        iv_percentile,
        support_price,
        ma50,
        ma200,
        resistance_price,
        days_until_earnings,
        next_earnings_date,
        earnings_data_source,
        option_contract_data,
    )


# This function checks whether the user's entries make sense for the calculator.
# It stops the program with a helpful error if it finds an invalid value.
# A function that only checks values does not need to return a result.
def validate_inputs(
    stock_price,
    strike_price,
    premium_received,
    number_of_contracts,
    days_to_expiration,
    delta,
    iv_low,
    iv_high,
    iv_percentile,
    support_price,
    ma50,
    ma200,
    resistance_price,
    days_until_earnings,
):
    """Raise an error if any input is outside its allowed range."""

    # Stock and strike prices must both be greater than zero.
    if stock_price <= 0 or strike_price <= 0:
        raise ValueError("Stock price and strike price must be greater than zero.")

    # A premium may be zero, but it cannot be negative here.
    if premium_received < 0:
        raise ValueError("Premium received cannot be negative.")

    # The contract count and days to expiration must be positive whole numbers.
    if number_of_contracts <= 0 or days_to_expiration <= 0:
        raise ValueError("Contracts and days to expiration must be greater than zero.")

    # The user enters the absolute value of delta, so it must be from 0 to 1.
    if delta is not None and (delta < 0 or delta > 1):
        raise ValueError("Delta must be between 0 and 1.")

    # IV Rank needs a high that is above the low. Equal values would cause
    # division by zero, while a lower high would make the range invalid.
    if iv_high < iv_low:
        raise ValueError("The 52-week IV high cannot be lower than the IV low.")
    if iv_high == iv_low:
        raise ValueError("The 52-week IV high and IV low cannot be the same.")

    # IV Percentile is entered manually as a percentage from 0 through 100.
    if iv_percentile < 0 or iv_percentile > 100:
        raise ValueError("IV Percentile must be between 0 and 100.")

    # Technical price entries must be positive so their comparisons make sense.
    if support_price <= 0:
        raise ValueError("Support price must be greater than zero.")
    if ma50 <= 0 or ma200 <= 0:
        raise ValueError("Moving averages must be greater than zero.")
    if resistance_price <= 0:
        raise ValueError("Resistance price must be greater than zero.")

    # Zero means earnings are today; negative days are not allowed.
    if days_until_earnings < 0:
        raise ValueError("Days until earnings must be zero or greater.")


# This function calculates where current IV sits in its 52-week range.
def calculate_iv_rank(current_iv, iv_low, iv_high):
    """Calculate and return IV Rank as a percentage."""

    return ((current_iv - iv_low) / (iv_high - iv_low)) * 100


# This function calculates the requested technical price comparisons.
def calculate_technical_context(
    stock_price,
    strike_price,
    support_price,
    ma50,
    ma200,
    resistance_price,
):
    """Calculate distances from technical price levels."""

    support_distance = ((stock_price - support_price) / support_price) * 100
    strike_vs_support = ((support_price - strike_price) / support_price) * 100
    ma50_distance = ((stock_price - ma50) / ma50) * 100
    ma200_distance = ((stock_price - ma200) / ma200) * 100
    price_vs_resistance = (
        (stock_price - resistance_price) / resistance_price
    ) * 100

    return (
        support_distance,
        strike_vs_support,
        ma50_distance,
        ma200_distance,
        price_vs_resistance,
    )


# This helper gives a price comparison simple beginner-friendly wording.
def describe_price_position(distance):
    """Describe whether a price is above, below, or nearly equal."""

    # A difference smaller than 0.01 percentage point is approximately equal.
    if abs(distance) < 0.01:
        return "approximately equal"
    if distance > 0:
        return "above"
    return "below"


# Strike vs support has the opposite wording from the other comparisons:
# a positive calculation means the strike itself is below support.
def describe_strike_position(strike_vs_support):
    """Describe whether the strike is below, at, or above support."""

    if abs(strike_vs_support) < 0.01:
        return "at support"
    if strike_vs_support > 0:
        return "below support"
    return "above support"


# Resistance uses special wording when the stock is at the resistance price.
def describe_resistance_position(price_vs_resistance):
    """Describe whether the stock is below, at, or above resistance."""

    if abs(price_vs_resistance) < 0.01:
        return "at resistance"
    return describe_price_position(price_vs_resistance)


# This function reports whether earnings occur during the option trade.
def earnings_occur_during_trade(days_until_earnings, days_to_expiration):
    """Return True when earnings occur on or before option expiration."""

    return days_until_earnings <= days_to_expiration


# This helper describes the earnings timing comparison for the user.
def describe_earnings_risk(days_until_earnings, days_to_expiration):
    """Return an informational warning about earnings timing."""

    if earnings_occur_during_trade(days_until_earnings, days_to_expiration):
        return "WARNING - Earnings occur before option expiration."
    return "Clear - Earnings occur after option expiration."


def require_number(value: object, field_name: str) -> float:
    """Return a numeric internal value after explicit type narrowing."""

    if isinstance(value, (int, float)):
        return float(value)
    raise ValueError(f"{field_name} must be a number.")


# These helpers build a simple technical snapshot from existing market data.
def calculate_percent_from_average(stock_price, moving_average):
    """Calculate how far price is above or below a moving average."""

    return ((stock_price - moving_average) / moving_average) * 100


def classify_trend(percent_from_average):
    """Classify price using a transparent plus-or-minus 2% range."""

    if percent_from_average > 2:
        return "Bullish"
    if percent_from_average < -2:
        return "Bearish"
    return "Neutral"


def classify_earnings_risk(days_until_earnings):
    """Classify near-term earnings timing without making a recommendation."""

    if days_until_earnings is None:
        return "UNKNOWN - verify manually"
    if days_until_earnings <= 7:
        return "HIGH earnings risk"
    if days_until_earnings <= 21:
        return "CAUTION"
    return "Lower near-term earnings risk"


def build_market_snapshot(
    stock_price,
    ma50,
    ma200,
    next_earnings_date,
    days_until_earnings,
    earnings_data_source,
):
    """Return the calculated values used by the Market Snapshot."""

    price_vs_ma50 = calculate_percent_from_average(stock_price, ma50)
    price_vs_ma200 = calculate_percent_from_average(stock_price, ma200)

    return {
        "stock_price": stock_price,
        "ma50": ma50,
        "ma200": ma200,
        "price_vs_ma50": price_vs_ma50,
        "price_vs_ma200": price_vs_ma200,
        "short_term_trend": classify_trend(price_vs_ma50),
        "long_term_trend": classify_trend(price_vs_ma200),
        "next_earnings_date": next_earnings_date,
        "days_until_earnings": days_until_earnings,
        "earnings_source": earnings_data_source.lower(),
        "earnings_risk": classify_earnings_risk(
            days_until_earnings if next_earnings_date is not None else None
        ),
    }


def build_put_seller_view(snapshot):
    """Return plain-English market context for a novice put seller."""

    if snapshot["price_vs_ma50"] > 0:
        ma50_message = "✓ Price is above the 50-day moving average"
    else:
        ma50_message = "⚠ Price is below the 50-day moving average"

    if snapshot["price_vs_ma200"] > 2:
        ma200_message = "✓ Price is above the 200-day moving average"
    else:
        ma200_message = "⚠ Price is near or below the 200-day moving average"

    days_until_earnings = snapshot["days_until_earnings"]
    if snapshot["next_earnings_date"] is None:
        earnings_message = "⚠ Earnings date is unknown"
    elif days_until_earnings <= 21:
        earnings_message = "⚠ Earnings are within 21 days"
    else:
        earnings_message = "✓ Earnings are more than 21 days away"

    return (ma50_message, ma200_message, earnings_message)


def display_market_snapshot(snapshot):
    """Print the Market Snapshot and informational Put Seller View."""

    price_vs_ma50 = require_number(
        snapshot["price_vs_ma50"],
        "Price versus 50-day average",
    )
    price_vs_ma200 = require_number(
        snapshot["price_vs_ma200"],
        "Price versus 200-day average",
    )

    print("\nMARKET SNAPSHOT")
    print(f"Current price:        ${snapshot['stock_price']:,.2f}")
    print(f"50-day average:       ${snapshot['ma50']:,.2f}")
    print(f"200-day average:      ${snapshot['ma200']:,.2f}")
    print(
        f"Price vs 50-day:      {abs(price_vs_ma50):.2f}% "
        f"{describe_price_position(price_vs_ma50)}"
    )
    print(
        f"Price vs 200-day:     {abs(price_vs_ma200):.2f}% "
        f"{describe_price_position(price_vs_ma200)}"
    )
    print(f"Short-term trend:     {snapshot['short_term_trend']}")
    print(f"Long-term trend:      {snapshot['long_term_trend']}")

    next_earnings_date = snapshot["next_earnings_date"]
    if next_earnings_date is None:
        print("Next earnings:        Unknown")
        print("Days until earnings: Unknown")
    else:
        print(f"Next earnings:        {next_earnings_date.isoformat()}")
        print(f"Days until earnings:  {snapshot['days_until_earnings']}")
    print(f"Earnings source:      {snapshot['earnings_source']}")
    print(f"Earnings risk level:  {snapshot['earnings_risk']}")
    print("Technical classifications are informational, not predictions.")

    print("\nPUT SELLER VIEW")
    for message in build_put_seller_view(snapshot):
        print(message)


# These helpers provide transparent context for one put option candidate.
def calculate_strike_distance(stock_price, strike_price):
    """Calculate strike distance as a percentage of the stock price."""

    return ((stock_price - strike_price) / stock_price) * 100


def calculate_breakeven_cushion(stock_price, breakeven_price):
    """Calculate the percentage decline from stock price to breakeven."""

    return ((stock_price - breakeven_price) / stock_price) * 100


def classify_strike_distance(strike_distance):
    """Describe how far the put strike is below the current stock price."""

    if strike_distance < 0:
        return "In-the-money strike - assignment exposure is higher"
    if strike_distance < 2:
        return "Very close to current price"
    if strike_distance < 5:
        return "Moderate distance below current price"
    if strike_distance < 10:
        return "Meaningful downside cushion"
    return "Large distance below current price"


def classify_delta(delta):
    """Describe optional delta using its magnitude, not as a probability."""

    if delta is None:
        return "Unknown - enter manually if available"

    delta_magnitude = abs(delta)
    if delta_magnitude > 1:
        raise ValueError("Delta magnitude must be between 0 and 1.")
    if delta_magnitude <= 0.15:
        return "Lower-delta / more conservative strike"
    if delta_magnitude <= 0.25:
        return "Moderate delta"
    if delta_magnitude <= 0.35:
        return "Higher assignment exposure"
    return "Aggressive delta / materially higher assignment exposure"


def classify_contract_earnings_risk(
    days_until_earnings,
    days_to_expiration,
    earnings_source="Retrieved",
):
    """Compare earnings timing with the option expiration window."""

    # Accept the earlier Boolean argument form so existing callers remain valid.
    if earnings_source is True:
        earnings_source = "Retrieved"
    elif earnings_source is False:
        earnings_source = "Unknown"

    if days_until_earnings is None or earnings_source == "Unknown":
        return "UNKNOWN - verify earnings manually"

    if earnings_source == "Manual":
        if days_until_earnings <= days_to_expiration:
            return (
                "MANUAL WARNING - earnings are estimated to be approximately "
                f"{days_until_earnings} days away and may occur during or by "
                f"this {days_to_expiration}-day option expiration. Verify the "
                "earnings date independently."
            )
        return (
            "MANUAL ESTIMATE - earnings are approximately "
            f"{days_until_earnings} days away, which is after this "
            f"{days_to_expiration}-day option expiration. Verify the earnings "
            "date independently."
        )

    if days_until_earnings <= days_to_expiration:
        return "HIGH EVENT RISK - earnings occur during the option contract"
    if days_until_earnings <= days_to_expiration + 7:
        return "CAUTION - earnings occur shortly after expiration"
    return "No earnings event during the option contract"


def build_option_candidate_analysis(
    stock_price,
    strike_price,
    premium_received,
    breakeven_price,
    strike_distance,
    breakeven_cushion,
    days_to_expiration,
    cash_required,
    maximum_profit,
    delta,
    days_until_earnings,
    earnings_source,
    snapshot,
):
    """Build informational context while reusing existing calculations."""

    return {
        "stock_price": stock_price,
        "strike_price": strike_price,
        "premium_received": premium_received,
        "breakeven_price": breakeven_price,
        "strike_distance": strike_distance,
        "breakeven_cushion": breakeven_cushion,
        "days_to_expiration": days_to_expiration,
        "cash_required": cash_required,
        "maximum_profit": maximum_profit,
        "strike_context": classify_strike_distance(strike_distance),
        "delta": delta,
        "delta_context": classify_delta(delta),
        "earnings_context": classify_contract_earnings_risk(
            days_until_earnings,
            days_to_expiration,
            earnings_source,
        ),
        "snapshot": snapshot,
    }


def build_contract_risk_checklist(analysis):
    """Return independent risk-context messages without scoring the trade."""

    messages = []
    strike_distance = analysis["strike_distance"]
    if strike_distance < 0:
        messages.append("WARNING: Strike is above the current stock price")
    elif strike_distance < 2:
        messages.append("WARNING: Strike is very close to the current stock price")
    else:
        messages.append("CHECK: Strike is below the current stock price")

    breakeven_cushion = analysis["breakeven_cushion"]
    if breakeven_cushion >= 0:
        messages.append(
            f"CHECK: Breakeven provides {breakeven_cushion:.2f}% downside cushion"
        )
    else:
        messages.append("WARNING: Breakeven is above the current stock price")

    earnings_context = analysis["earnings_context"]
    if earnings_context.startswith("UNKNOWN"):
        messages.append("WARNING: Earnings date is unknown")
    elif earnings_context.startswith(("HIGH", "MANUAL WARNING")):
        messages.append("WARNING: Earnings occur before expiration")
    elif earnings_context.startswith("CAUTION"):
        messages.append("WARNING: Earnings occur shortly after expiration")
    else:
        messages.append("CHECK: Earnings are outside the option contract")

    snapshot = analysis["snapshot"]
    if snapshot["price_vs_ma50"] < 0:
        messages.append("WARNING: Stock is below the 50-day moving average")
    if snapshot["price_vs_ma200"] < 0:
        messages.append("WARNING: Stock is below the 200-day moving average")
    else:
        messages.append("CHECK: Stock is above the 200-day moving average")

    delta = analysis["delta"]
    if delta is None:
        messages.append("WARNING: Delta is unknown")
    elif abs(delta) > 0.25:
        messages.append("WARNING: Delta indicates higher assignment exposure")

    return tuple(messages)


def display_option_candidate_analysis(analysis):
    """Print the option candidate analysis and contract risk checklist."""

    strike_distance = require_number(
        analysis["strike_distance"],
        "Strike distance",
    )
    strike_position = "below" if strike_distance >= 0 else "above"

    print("\nOPTION CANDIDATE ANALYSIS")
    print(f"Stock price:             ${analysis['stock_price']:,.2f}")
    print(f"Put strike:              ${analysis['strike_price']:,.2f}")
    print(
        f"Strike distance:         {abs(strike_distance):.2f}% "
        f"{strike_position} stock price"
    )
    print(f"Strike context:          {analysis['strike_context']}")
    print(f"Premium per share:       ${analysis['premium_received']:,.2f}")
    print(f"Breakeven price:         ${analysis['breakeven_price']:,.2f}")
    print(f"Breakeven cushion:       {analysis['breakeven_cushion']:.2f}%")
    print(f"Days to expiration:      {analysis['days_to_expiration']}")
    print(f"Cash secured:            ${analysis['cash_required']:,.2f}")
    print(f"Maximum premium:         ${analysis['maximum_profit']:,.2f}")

    if analysis["breakeven_cushion"] >= 0:
        print(
            "Breakeven context:       Stock can decline approximately "
            f"{analysis['breakeven_cushion']:.2f}% before reaching breakeven."
        )
    else:
        print("Breakeven context:       Breakeven is currently above the stock price.")
    print(
        "Below breakeven, losses can become substantial if shares are assigned."
    )
    print(f"Earnings context:        {analysis['earnings_context']}")

    analysis_delta = analysis["delta"]
    if analysis_delta is None:
        print("Delta:                  Unknown - enter manually if available")
    else:
        delta_value = require_number(analysis_delta, "Delta")
        print(f"Delta:                   {abs(delta_value):.2f}")
        print(f"Delta context:           {analysis['delta_context']}")
    print(
        "Delta is not an exact assignment probability and changes with price, "
        "volatility, and time."
    )
    print("Strike distance alone does not determine whether a trade is safe.")

    print("\nCONTRACT RISK CHECKLIST")
    for message in build_contract_risk_checklist(analysis):
        print(message)


def format_optional_money(value):
    """Format an optional provider price for beginner-friendly output."""

    return "Unavailable" if value is None else f"${value:,.2f}"


def display_option_contract_snapshot(option_data, manual_delta):
    """Print normalized option data without changing manual calculator inputs."""

    if option_data is None:
        return

    contract = option_data["contract"]
    print("\nOPTION CONTRACT SNAPSHOT")
    print(f"Ticker:                 {option_data['ticker']}")
    print(f"Requested DTE:          {option_data['requested_dte']}")
    print(f"Expiration selected:    {option_data['expiration_date'].isoformat()}")
    print(f"Actual DTE:             {option_data['actual_dte']}")
    print(f"Requested strike:       ${option_data['requested_strike']:,.2f}")
    print(f"Listed strike selected: ${contract['strike']:,.2f}")
    if contract["strike"] != option_data["requested_strike"]:
        print("The listed strike differs from the requested calculator strike.")

    print(f"Bid:                    {format_optional_money(contract['bid'])}")
    print(f"Ask:                    {format_optional_money(contract['ask'])}")
    print(f"Midpoint:               {format_optional_money(option_data['midpoint'])}")
    print(f"Last price:             {format_optional_money(contract['last_price'])}")

    if option_data["spread"] is None:
        print("Bid/ask spread:         Unavailable")
    else:
        print(
            f"Bid/ask spread:         ${option_data['spread']:.2f} "
            f"({option_data['spread_percentage']:.1f}% of midpoint)"
        )
    print(f"Spread context:         {option_data['spread_context']}")
    print("The midpoint is descriptive and is not a guaranteed fill price.")

    contract_iv = contract["implied_volatility"]
    if contract_iv is None:
        print("Contract IV:            Unavailable")
    else:
        print(f"Contract IV:            {contract_iv * 100:.1f}%")
    print(
        "Volume:                 "
        + ("Unavailable" if contract["volume"] is None else f"{contract['volume']:.0f}")
    )
    print(
        "Open interest:          "
        + (
            "Unavailable"
            if contract["open_interest"] is None
            else f"{contract['open_interest']:.0f}"
        )
    )

    provider_delta = contract["delta"]
    if provider_delta is not None:
        print(f"Delta:                  {provider_delta:.2f} (provider value)")
    elif manual_delta is not None:
        print(f"Delta:                  {manual_delta:.2f} (manually entered)")
    else:
        print("Delta:                  Unknown")

    for message in option_data["liquidity_context"]:
        print(f"Liquidity context:      {message}")
    print("Manual premium remains in use for all calculator return calculations.")


def display_trade_quality_scorecard(scorecard):
    """Print a transparent educational score and its component explanations."""

    print("\nTRADE QUALITY SCORECARD")
    for name, result in scorecard["components"].items():
        print(
            f"{name + ':':<22}{result['points']:>2} / {result['maximum']:<2}  "
            f"{result['detail']}"
        )

    print(f"\nTOTAL:                {scorecard['total']} / 100")
    print(f"ASSESSMENT:           {scorecard['assessment']}")

    if scorecard["concerns"]:
        print("\nKey concerns:")
        for concern in scorecard["concerns"]:
            print(f"- {concern}")
    if scorecard["positive_factors"]:
        print("\nPositive factors:")
        for factor in scorecard["positive_factors"]:
            print(f"- {factor}")

    print("\nEducational screening only - not a prediction of profit or safety.")


def select_effective_delta(option_data, manual_delta):
    """Use provider Delta only when the normalized contract actually has it."""

    if option_data is not None:
        provider_delta = option_data["contract"].get("delta")
        if provider_delta is not None:
            return abs(provider_delta)
    return manual_delta


# This function creates independent, informational checklist messages.
def create_trade_checklist(
    delta,
    iv_rank,
    iv_percentile,
    strike_price,
    support_price,
    days_until_earnings,
    days_to_expiration,
    stock_price,
    ma50,
    ma200,
):
    """Return the six neutral trade-checklist messages."""

    if delta is not None and 0.15 <= delta <= 0.30:
        delta_check = "Delta Check: PASS - Within common put-selling range."
    elif delta is None:
        delta_check = "Delta Check: REVIEW - Delta is unknown."
    else:
        delta_check = (
            "Delta Check: REVIEW - Outside the 0.15 to 0.30 reference range."
        )

    if iv_rank >= 30:
        iv_rank_check = (
            "IV Rank Check: PASS - Volatility is relatively elevated."
        )
    else:
        iv_rank_check = "IV Rank Check: REVIEW - IV Rank is below 30."

    if iv_percentile >= 50:
        iv_percentile_check = (
            "IV Percentile Check: PASS - Current IV is above much of its "
            "recent history."
        )
    else:
        iv_percentile_check = (
            "IV Percentile Check: REVIEW - Current IV is below the 50th "
            "percentile."
        )

    if strike_price < support_price:
        support_check = "Support Check: PASS - Strike is below estimated support."
    else:
        support_check = (
            "Support Check: REVIEW - Strike is at or above estimated support."
        )

    if earnings_occur_during_trade(days_until_earnings, days_to_expiration):
        earnings_check = (
            "Earnings Check: WARNING - Earnings occur during the trade."
        )
    else:
        earnings_check = "Earnings Check: PASS - Earnings occur after expiration."

    if stock_price > ma50 and stock_price > ma200:
        trend_check = "Trend Check: PASS - Price is above both moving averages."
    else:
        trend_check = (
            "Trend Check: REVIEW - Price is not above both moving averages."
        )

    return (
        delta_check,
        iv_rank_check,
        iv_percentile_check,
        support_check,
        earnings_check,
        trend_check,
    )


# This function performs all seven requested calculations.
# It accepts the values needed for the formulas and returns the seven results.
def calculate_put_results(
    stock_price,
    strike_price,
    premium_received,
    number_of_contracts,
    days_to_expiration,
):
    """Calculate the profit, capital, return, and price-cushion results."""

    # One standard U.S. stock option contract represents 100 shares.
    shares_per_contract = 100

    # Find the total number of shares represented by all contracts.
    total_shares = number_of_contracts * shares_per_contract

    # Maximum profit is the total premium received if the put expires worthless.
    maximum_profit = premium_received * total_shares

    # Breakeven is the strike price minus the premium received per share.
    breakeven_price = strike_price - premium_received

    # If assigned, the seller buys every represented share at the strike price.
    cash_required = strike_price * total_shares

    # Divide profit by required cash, then multiply by 100 for a percentage.
    return_on_capital = (maximum_profit / cash_required) * 100

    # Annualize the return by multiplying it by the number of equal option
    # periods that would fit into 365 days.
    # Formula: Return on Capital * (365 / Days to Expiration)
    annualized_return = return_on_capital * (365 / days_to_expiration)

    # Strike cushion measures how far the strike price is below the current
    # stock price, expressed as a percentage of the current stock price.
    # Formula: ((Stock Price - Strike Price) / Stock Price) * 100
    strike_cushion = ((stock_price - strike_price) / stock_price) * 100

    # Breakeven cushion measures how far the breakeven price is below the
    # current stock price, expressed as a percentage of the current stock price.
    # Formula: ((Stock Price - Breakeven Price) / Stock Price) * 100
    breakeven_cushion = ((stock_price - breakeven_price) / stock_price) * 100

    # Send all seven calculated values back to the caller.
    return (
        maximum_profit,
        breakeven_price,
        cash_required,
        return_on_capital,
        annualized_return,
        strike_cushion,
        breakeven_cushion,
    )


# This function prints the original inputs and calculated results neatly.
# Keeping display code separate makes the calculation function easier to reuse.
# The formatting after each colon controls commas and decimal places.
def display_results(
    ticker,
    market_data_source,
    stock_price,
    strike_price,
    premium_received,
    days_to_expiration,
    maximum_profit,
    breakeven_price,
    cash_required,
    return_on_capital,
    annualized_return,
    strike_cushion,
    breakeven_cushion,
    delta,
    current_iv,
    iv_rank,
    iv_percentile,
    support_price,
    support_distance,
    strike_vs_support,
    ma50,
    ma50_distance,
    ma200,
    ma200_distance,
    resistance_price,
    price_vs_resistance,
    days_until_earnings,
    next_earnings_date,
    earnings_data_source,
    option_contract_data,
):
    """Display the trade details and calculated results."""

    # \n starts the heading on a new line.
    print("\n--- Cash-Secured Put Results ---")

    # f-strings insert variable values wherever braces appear.
    print(f"Ticker:               {ticker}")
    print(f"Market data source:   {market_data_source}")
    print(f"Current stock price:  ${stock_price:,.2f}")
    print(f"Days to expiration:   {days_to_expiration}")
    print(f"Maximum profit:       ${maximum_profit:,.2f}")
    print(f"Breakeven price:      ${breakeven_price:,.2f} per share")
    print(f"Cash required:        ${cash_required:,.2f}")
    print(f"Return on capital:    {return_on_capital:.2f}%")
    print(f"Annualized return:    {annualized_return:.2f}%")
    print(f"Strike cushion:       {strike_cushion:.2f}%")
    print(f"Breakeven cushion:    {breakeven_cushion:.2f}%")
    if delta is None:
        print("Delta:                Unknown")
    else:
        print(f"Delta:                {delta:.2f}")
    print(f"Current IV:           {current_iv:.2f}%")
    print(f"IV Rank:              {iv_rank:.2f}%")
    print(f"IV Percentile:        {iv_percentile:.2f}%")
    print(f"Support Price:        ${support_price:,.2f}")
    print(
        f"Price vs Support:     {abs(support_distance):.2f}% "
        f"{describe_price_position(support_distance)}"
    )
    print(
        f"Strike vs Support:    {abs(strike_vs_support):.2f}% "
        f"{describe_strike_position(strike_vs_support)}"
    )
    print(f"50-Day MA:            ${ma50:,.2f}")
    print(
        f"Price vs 50-Day MA:   {abs(ma50_distance):.2f}% "
        f"{describe_price_position(ma50_distance)}"
    )
    print(f"200-Day MA:           ${ma200:,.2f}")
    print(
        f"Price vs 200-Day MA:  {abs(ma200_distance):.2f}% "
        f"{describe_price_position(ma200_distance)}"
    )
    print(f"Resistance Price:     ${resistance_price:,.2f}")

    resistance_position = describe_resistance_position(price_vs_resistance)
    if resistance_position == "at resistance":
        print("Price vs Resistance:  at resistance")
    else:
        print(
            f"Price vs Resistance:  {abs(price_vs_resistance):.2f}% "
            f"{resistance_position}"
        )

    earnings_risk = describe_earnings_risk(
        days_until_earnings,
        days_to_expiration,
    )
    print(f"Earnings Risk:        {earnings_risk}")
    if earnings_data_source == "Retrieved":
        print(f"Next Earnings Date:   {next_earnings_date.isoformat()}")
        print(f"Days Until Earnings:  {days_until_earnings}")
        print("Earnings data:        Retrieved automatically")
        print("Earnings dates can change; verify before placing a real trade.")
    else:
        print("Earnings data:        Manual entry")

    # Each checklist item is informational and is displayed independently.
    checklist = create_trade_checklist(
        delta,
        iv_rank,
        iv_percentile,
        strike_price,
        support_price,
        days_until_earnings,
        days_to_expiration,
        stock_price,
        ma50,
        ma200,
    )
    print("\n--- Informational Trade Checklist ---")
    for checklist_item in checklist:
        print(checklist_item)

    # Reuse the existing values; no additional market-data request is made.
    snapshot = build_market_snapshot(
        stock_price,
        ma50,
        ma200,
        next_earnings_date,
        days_until_earnings,
        earnings_data_source,
    )
    display_market_snapshot(snapshot)

    display_option_contract_snapshot(option_contract_data, delta)

    analysis_delta = select_effective_delta(option_contract_data, delta)

    analysis = build_option_candidate_analysis(
        stock_price,
        strike_price,
        premium_received,
        breakeven_price,
        strike_cushion,
        breakeven_cushion,
        days_to_expiration,
        cash_required,
        maximum_profit,
        analysis_delta,
        days_until_earnings,
        earnings_data_source,
        snapshot,
    )
    display_option_candidate_analysis(analysis)

    spread_percentage = None
    open_interest = None
    volume = None
    if option_contract_data is not None:
        spread_percentage = option_contract_data["spread_percentage"]
        open_interest = option_contract_data["contract"]["open_interest"]
        volume = option_contract_data["contract"]["volume"]

    scorecard = build_trade_quality_score(
        days_to_expiration,
        analysis_delta,
        strike_cushion,
        breakeven_cushion,
        stock_price,
        ma50,
        ma200,
        iv_rank,
        days_until_earnings,
        earnings_data_source,
        spread_percentage,
        open_interest,
        volume,
    )
    display_trade_quality_scorecard(scorecard)


# This is the main function: it coordinates the other functions in order.
# It gets input, validates it, calculates the results, and displays them.
# Putting these steps here provides a clear overview of the whole program.
def main():
    """Run the cash-secured put calculator from beginning to end."""

    # Unpack the returned values into clearly named variables.
    (
        ticker,
        market_data_source,
        stock_price,
        strike_price,
        premium_received,
        number_of_contracts,
        days_to_expiration,
        delta,
        current_iv,
        iv_low,
        iv_high,
        iv_percentile,
        support_price,
        ma50,
        ma200,
        resistance_price,
        days_until_earnings,
        next_earnings_date,
        earnings_data_source,
        option_contract_data,
    ) = get_user_inputs()

    # Check all inputs before using them in calculations.
    validate_inputs(
        stock_price,
        strike_price,
        premium_received,
        number_of_contracts,
        days_to_expiration,
        delta,
        iv_low,
        iv_high,
        iv_percentile,
        support_price,
        ma50,
        ma200,
        resistance_price,
        days_until_earnings,
    )

    # Run the formulas and unpack the seven returned results.
    (
        maximum_profit,
        breakeven_price,
        cash_required,
        return_on_capital,
        annualized_return,
        strike_cushion,
        breakeven_cushion,
    ) = calculate_put_results(
        stock_price,
        strike_price,
        premium_received,
        number_of_contracts,
        days_to_expiration,
    )

    # Calculate IV Rank after validation confirms that the IV range is valid.
    iv_rank = calculate_iv_rank(current_iv, iv_low, iv_high)

    # Calculate the technical comparisons after validating all price inputs.
    (
        support_distance,
        strike_vs_support,
        ma50_distance,
        ma200_distance,
        price_vs_resistance,
    ) = calculate_technical_context(
        stock_price,
        strike_price,
        support_price,
        ma50,
        ma200,
        resistance_price,
    )

    # Pass the input context and calculated values to the display function.
    display_results(
        ticker,
        market_data_source,
        stock_price,
        strike_price,
        premium_received,
        days_to_expiration,
        maximum_profit,
        breakeven_price,
        cash_required,
        return_on_capital,
        annualized_return,
        strike_cushion,
        breakeven_cushion,
        delta,
        current_iv,
        iv_rank,
        iv_percentile,
        support_price,
        support_distance,
        strike_vs_support,
        ma50,
        ma50_distance,
        ma200,
        ma200_distance,
        resistance_price,
        price_vs_resistance,
        days_until_earnings,
        next_earnings_date,
        earnings_data_source,
        option_contract_data,
    )


# Python sets __name__ to "__main__" when this file is run directly.
# This check calls main() when running this file, but not when importing it.
if __name__ == "__main__":
    # Show invalid entries as a short, beginner-friendly message.
    try:
        main()
    except ValueError as error:
        print(f"\nError: {error}")
