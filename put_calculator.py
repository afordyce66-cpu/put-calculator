"""Calculate the basic numbers for a cash-secured put option."""


# This function asks the user for the trade and volatility information.
# It converts prices and percentages to decimal numbers and counts to whole
# numbers. Finally, it returns the values so another function can use them.
def get_user_inputs():
    """Ask for and return the details of the put option trade."""

    # input() returns text, and float() converts that text to a decimal number.
    stock_price = float(input("Stock price: $"))
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

    # return sends these values back to the line that called this function.
    return (
        stock_price,
        strike_price,
        premium_received,
        number_of_contracts,
        days_to_expiration,
        delta,
        current_iv,
        iv_low,
        iv_high,
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


# This function calculates where current IV sits in its 52-week range.
def calculate_iv_rank(current_iv, iv_low, iv_high):
    """Calculate and return IV Rank as a percentage."""

    return ((current_iv - iv_low) / (iv_high - iv_low)) * 100


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
    stock_price,
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
):
    """Display the trade details and calculated results."""

    # \n starts the heading on a new line.
    print("\n--- Cash-Secured Put Results ---")

    # f-strings insert variable values wherever braces appear.
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


# This is the main function: it coordinates the other functions in order.
# It gets input, validates it, calculates the results, and displays them.
# Putting these steps here provides a clear overview of the whole program.
def main():
    """Run the cash-secured put calculator from beginning to end."""

    # Unpack the returned values into clearly named variables.
    (
        stock_price,
        strike_price,
        premium_received,
        number_of_contracts,
        days_to_expiration,
        delta,
        current_iv,
        iv_low,
        iv_high,
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

    # Pass the input context and calculated values to the display function.
    display_results(
        stock_price,
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
    )


# Python sets __name__ to "__main__" when this file is run directly.
# This check calls main() when running this file, but not when importing it.
if __name__ == "__main__":
    # Show invalid entries as a short, beginner-friendly message.
    try:
        main()
    except ValueError as error:
        print(f"\nError: {error}")
