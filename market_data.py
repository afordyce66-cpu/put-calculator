"""Retrieve basic stock-price data for the put calculator."""

from datetime import date, datetime

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


def find_next_earnings_date(earnings_dates, today=None):
    """Return the earliest valid future earnings date from provider data."""

    if today is None:
        today = date.today()

    if earnings_dates is None or earnings_dates.empty:
        raise MarketDataError("No earnings dates were returned.")

    future_dates = []
    for value in earnings_dates.index:
        try:
            # yfinance normally supplies datetime-like values in the index.
            if isinstance(value, datetime):
                earnings_date = value.date()
            elif isinstance(value, date):
                earnings_date = value
            else:
                earnings_date = datetime.fromisoformat(str(value)).date()
        except (TypeError, ValueError):
            continue

        if earnings_date >= today:
            future_dates.append(earnings_date)

    if not future_dates:
        raise MarketDataError("No valid future earnings date was returned.")

    return min(future_dates)


def calculate_days_until_earnings(next_earnings_date, today=None):
    """Calculate calendar days from today through the earnings date."""

    if today is None:
        today = date.today()
    if not isinstance(next_earnings_date, date):
        raise MarketDataError("The earnings date was not valid.")

    days_until_earnings = (next_earnings_date - today).days
    if days_until_earnings < 0:
        raise MarketDataError("The earnings date is already in the past.")
    return days_until_earnings


def get_market_data(ticker):
    """Retrieve daily history and return price and moving-average data."""

    normalized_ticker = normalize_ticker(ticker)

    try:
        # Two years normally provides more than the required 200 trading days.
        stock = yf.Ticker(normalized_ticker)
        history = stock.history(period="2y", interval="1d", auto_adjust=False)
        market_data = calculate_prices_from_history(normalized_ticker, history)

        # Earnings data is optional. Price data remains usable if this fails.
        try:
            earnings_dates = stock.get_earnings_dates(limit=12)
            next_earnings_date = find_next_earnings_date(earnings_dates)
            market_data["next_earnings_date"] = next_earnings_date
            market_data["days_until_earnings"] = calculate_days_until_earnings(
                next_earnings_date
            )
        except Exception:
            market_data["next_earnings_date"] = None
            market_data["days_until_earnings"] = None

        return market_data
    except MarketDataError:
        raise
    except Exception as error:
        # Convert provider and format errors into one predictable app error.
        raise MarketDataError("Market data could not be retrieved.") from error
