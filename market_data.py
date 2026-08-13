"""Retrieve basic stock-price data for the put calculator."""

import yfinance as yf


class MarketDataError(Exception):
    """Raised when usable market data cannot be retrieved."""


def normalize_ticker(ticker):
    """Remove extra spaces and convert a ticker symbol to uppercase."""

    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        raise MarketDataError("A ticker symbol is required.")
    return normalized_ticker


def calculate_prices_from_history(ticker, history):
    """Build the market-data result from retrieved daily price history."""

    if history is None or history.empty or "Close" not in history.columns:
        raise MarketDataError("No closing-price history was returned.")

    # Remove missing closing prices before counting trading days.
    closing_prices = history["Close"].dropna()
    if len(closing_prices) < 200:
        raise MarketDataError(
            "At least 200 trading days are needed for the 200-day average."
        )

    # The latest available close is not guaranteed to be a real-time quote.
    stock_price = float(closing_prices.iloc[-1])
    ma50 = float(closing_prices.tail(50).mean())
    ma200 = float(closing_prices.tail(200).mean())

    if stock_price <= 0 or ma50 <= 0 or ma200 <= 0:
        raise MarketDataError("The retrieved prices were not valid.")

    return {
        "ticker": ticker,
        "stock_price": stock_price,
        "ma50": ma50,
        "ma200": ma200,
    }


def get_market_data(ticker):
    """Retrieve daily history and return price and moving-average data."""

    normalized_ticker = normalize_ticker(ticker)

    try:
        # Two years normally provides more than the required 200 trading days.
        stock = yf.Ticker(normalized_ticker)
        history = stock.history(period="2y", interval="1d", auto_adjust=False)
        return calculate_prices_from_history(normalized_ticker, history)
    except MarketDataError:
        raise
    except Exception as error:
        # Convert provider and format errors into one predictable app error.
        raise MarketDataError("Market data could not be retrieved.") from error
