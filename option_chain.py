"""Retrieve and normalize optional put option-chain data."""

from datetime import date, datetime
import math

import yfinance as yf


class OptionChainError(Exception):
    """Raised when usable option-chain data cannot be retrieved."""


def normalize_ticker(ticker):
    """Normalize and validate a ticker symbol for option lookup."""

    normalized = ticker.strip().upper()
    if not normalized:
        raise OptionChainError("A ticker symbol is required for option data.")
    return normalized


def parse_expiration(expiration):
    """Convert a provider expiration value to a calendar date."""

    try:
        if isinstance(expiration, datetime):
            return expiration.date()
        if isinstance(expiration, date):
            return expiration
        return datetime.strptime(str(expiration), "%Y-%m-%d").date()
    except (TypeError, ValueError) as error:
        raise OptionChainError("An option expiration date was malformed.") from error


def select_closest_expiration(expirations, requested_dte, today=None):
    """Select the listed expiration whose DTE is closest to the request."""

    if today is None:
        today = date.today()
    if not expirations:
        raise OptionChainError("No option expiration dates were available.")

    available = []
    for expiration in expirations:
        try:
            expiration_date = parse_expiration(expiration)
        except OptionChainError:
            continue
        actual_dte = (expiration_date - today).days
        if actual_dte >= 0:
            available.append((expiration_date, actual_dte))

    if not available:
        raise OptionChainError("No useful future expiration was available.")

    # If two dates are equally close, prefer the earlier expiration.
    return min(available, key=lambda item: (abs(item[1] - requested_dte), item[0]))


def optional_number(value):
    """Return a finite float or None for missing/malformed provider values."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def normalize_put_contract(row, expiration_date):
    """Normalize one provider row into the calculator's simple structure."""

    strike = optional_number(row.get("strike"))
    if strike is None or strike <= 0:
        raise OptionChainError("A put contract had no valid strike.")

    delta = optional_number(row.get("delta"))
    if delta is not None and abs(delta) > 1:
        delta = None

    return {
        "strike": strike,
        "bid": optional_number(row.get("bid")),
        "ask": optional_number(row.get("ask")),
        "last_price": optional_number(row.get("lastPrice")),
        "implied_volatility": optional_number(row.get("impliedVolatility")),
        "volume": optional_number(row.get("volume")),
        "open_interest": optional_number(row.get("openInterest")),
        "in_the_money": row.get("inTheMoney") if "inTheMoney" in row else None,
        "expiration_date": expiration_date,
        "delta": delta,
    }


def select_nearest_strike(contracts, requested_strike):
    """Select the listed put contract closest to the requested strike."""

    if not contracts:
        raise OptionChainError("No usable put contracts were available.")
    return min(contracts, key=lambda contract: abs(contract["strike"] - requested_strike))


def calculate_midpoint(bid, ask):
    """Calculate a quote midpoint only when both quotes are usable."""

    bid = optional_number(bid)
    ask = optional_number(ask)
    if bid is None or ask is None or bid < 0 or ask < bid:
        return None
    return (bid + ask) / 2


def calculate_spread(bid, ask):
    """Return absolute and midpoint-relative bid/ask spreads."""

    midpoint = calculate_midpoint(bid, ask)
    if midpoint is None or midpoint <= 0:
        return None, None
    spread = float(ask) - float(bid)
    return spread, (spread / midpoint) * 100


def classify_spread(spread_percentage):
    """Describe spread width without promising an execution price."""

    if spread_percentage is None:
        return "Spread unavailable"
    if spread_percentage < 5:
        return "Narrower spread"
    if spread_percentage <= 15:
        return "Moderate spread"
    return "Wide spread - execution price may matter significantly"


def describe_liquidity(contract, spread_percentage):
    """Build descriptive, non-scored liquidity context messages."""

    messages = []
    if contract["volume"] in (None, 0):
        messages.append("No trading volume reported for this contract.")
    if contract["open_interest"] is None:
        messages.append("Open interest was not reported.")
    elif contract["open_interest"] < 100:
        messages.append("Open interest is relatively limited.")
    messages.append(classify_spread(spread_percentage))
    return tuple(messages)


def get_put_contract(ticker, requested_dte, requested_strike, today=None):
    """Retrieve one option chain and select the nearest expiration and strike."""

    normalized_ticker = normalize_ticker(ticker)
    if today is None:
        today = date.today()

    try:
        stock = yf.Ticker(normalized_ticker)
        expiration_date, actual_dte = select_closest_expiration(
            stock.options,
            requested_dte,
            today,
        )

        # Retrieve the selected expiration exactly once during this lookup.
        chain = stock.option_chain(expiration_date.isoformat())
        puts = chain.puts
        if puts is None or puts.empty:
            raise OptionChainError("The selected expiration had no put contracts.")

        contracts = []
        for _, row in puts.iterrows():
            try:
                contracts.append(normalize_put_contract(row, expiration_date))
            except OptionChainError:
                continue

        contract = select_nearest_strike(contracts, requested_strike)
        midpoint = calculate_midpoint(contract["bid"], contract["ask"])
        spread, spread_percentage = calculate_spread(
            contract["bid"], contract["ask"]
        )

        return {
            "ticker": normalized_ticker,
            "requested_dte": requested_dte,
            "expiration_date": expiration_date,
            "actual_dte": actual_dte,
            "requested_strike": requested_strike,
            "contract": contract,
            "midpoint": midpoint,
            "spread": spread,
            "spread_percentage": spread_percentage,
            "spread_context": classify_spread(spread_percentage),
            "liquidity_context": describe_liquidity(contract, spread_percentage),
        }
    except OptionChainError:
        raise
    except Exception as error:
        raise OptionChainError("Option-chain data could not be retrieved.") from error
