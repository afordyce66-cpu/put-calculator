"""Calculate the basic numbers for a cash-secured put option."""

from datetime import date

from market_data import get_market_data


# This function asks the user for the trade and volatility information.
# It converts prices and percentages to decimal numbers and counts to whole
# numbers. Finally, it returns the values so another function can use them.
def get_user_inputs():
    """Ask for and return the details of the put option trade."""

    # Try to retrieve the latest available close and moving averages first.
    ticker = input("Ticker symbol: ").strip().upper()
    try:
        market_data = get_market_data(ticker)
        ticker = market_data["ticker"]
        stock_price = float(market_data["stock_price"])
        ma50 = float(market_data["ma50"])
        ma200 = float(market_data["ma200"])
        market_data_source = "Retrieved"

        try:
            next_earnings_date = market_data.get("next_earnings_date")
            days_until_earnings = int(market_data.get("days_until_earnings"))
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
        if earnings_data_source == "Retrieved":
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

    # Delta is entered as an absolute decimal value, such as 0.20.
    delta = float(input("Absolute put delta (0 to 1): "))

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
    if delta < 0 or delta > 1:
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

    if 0.15 <= delta <= 0.30:
        delta_check = "Delta Check: PASS - Within common put-selling range."
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
    )


# Python sets __name__ to "__main__" when this file is run directly.
# This check calls main() when running this file, but not when importing it.
if __name__ == "__main__":
    # Show invalid entries as a short, beginner-friendly message.
    try:
        main()
    except ValueError as error:
        print(f"\nError: {error}")
