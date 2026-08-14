"""Deterministic educational scoring for a cash-secured put setup."""


WEIGHTS = {
    "DTE": 10,
    "Delta": 15,
    "Strike distance": 10,
    "Breakeven cushion": 10,
    "Trend": 15,
    "IV Rank": 10,
    "Earnings": 10,
    "Bid/ask liquidity": 10,
    "Open interest": 5,
    "Volume": 5,
}


def component(points, maximum, detail):
    """Return one consistently structured score component."""

    return {"points": points, "maximum": maximum, "detail": detail}


def score_dte(dte):
    if 25 <= dte <= 45:
        return component(10, 10, "25-45 day reference range")
    if 15 <= dte <= 24 or 46 <= dte <= 60:
        return component(6, 10, "Outside the strongest DTE range")
    return component(0, 10, "Well outside the 25-45 day reference range")


def score_delta(delta):
    if delta is None:
        return component(0, 15, "Unknown - not fully evaluated")
    magnitude = abs(delta)
    if 0.15 <= magnitude <= 0.30:
        return component(15, 15, "Within the preferred reference range")
    if 0.10 <= magnitude < 0.15 or 0.30 < magnitude <= 0.35:
        return component(8, 15, "Near the preferred reference range")
    return component(3, 15, "Very low or more aggressive Delta")


def score_strike_distance(distance):
    if distance < 0:
        return component(0, 10, "Strike is above the stock price")
    if distance < 2:
        return component(2, 10, "Strike is very close to the stock price")
    if distance < 5:
        return component(6, 10, "Moderate distance below stock price")
    if distance < 10:
        return component(10, 10, "Meaningful distance below stock price")
    return component(8, 10, "Large distance; other risks still matter")


def score_breakeven_cushion(cushion):
    if cushion < 0:
        return component(0, 10, "Breakeven is above the stock price")
    if cushion < 2:
        return component(2, 10, "Very limited breakeven cushion")
    if cushion < 5:
        return component(5, 10, "Moderate breakeven cushion")
    if cushion < 10:
        return component(8, 10, "Meaningful breakeven cushion")
    return component(10, 10, "Larger breakeven cushion")


def score_trend(stock_price, ma50, ma200):
    if stock_price > ma50 and stock_price > ma200:
        return component(15, 15, "Price is above both moving averages")
    if stock_price > ma200:
        return component(9, 15, "Above 200-day but not above 50-day MA")
    if stock_price > ma50:
        return component(5, 15, "Below 200-day despite short-term strength")
    return component(2, 15, "Price is below the 200-day moving average")


def score_iv_rank(iv_rank):
    if iv_rank is None:
        return component(2, 10, "Unknown - not fully evaluated")
    if 30 <= iv_rank <= 70:
        return component(10, 10, "Elevated without being at an extreme")
    if 20 <= iv_rank < 30 or 70 < iv_rank <= 90:
        return component(6, 10, "Outside the balanced reference range")
    return component(3, 10, "Very low or extremely elevated IV Rank")


def score_earnings(days_until_earnings, dte, source):
    if days_until_earnings is None or source not in ("Retrieved", "Manual"):
        return component(1, 10, "Unknown - verify earnings manually")
    if days_until_earnings <= dte:
        label = "Manual/unverified" if source == "Manual" else "Retrieved"
        return component(0, 10, f"{label} earnings occur during the contract")
    if source == "Manual":
        return component(7, 10, "Manual/unverified estimate after expiration")
    return component(10, 10, "Retrieved earnings timing is after expiration")


def score_liquidity(spread_percentage):
    if spread_percentage is None:
        return component(2, 10, "Unknown - bid/ask spread unavailable")
    if spread_percentage < 5:
        return component(10, 10, "Narrower spread")
    if spread_percentage <= 15:
        return component(7, 10, "Moderate spread")
    if spread_percentage <= 30:
        return component(3, 10, "Wide spread")
    return component(0, 10, "Very wide spread")


def score_open_interest(open_interest):
    if open_interest is None:
        return component(1, 5, "Unknown - not reported")
    if open_interest >= 500:
        return component(5, 5, "Higher open interest")
    if open_interest >= 100:
        return component(3, 5, "Moderate open interest")
    return component(1, 5, "Limited open interest")


def score_volume(volume):
    if volume is None:
        return component(1, 5, "Unknown - not reported")
    if volume >= 100:
        return component(5, 5, "Higher reported volume")
    if volume >= 20:
        return component(3, 5, "Moderate reported volume")
    return component(1, 5, "Limited or no reported volume")


def classify_assessment(total):
    """Map a bounded total to the three educational assessment bands."""

    if total >= 80:
        return "STRONG SETUP"
    if total >= 60:
        return "CAUTION"
    return "HIGH RISK"


def build_trade_quality_score(
    dte,
    delta,
    strike_distance,
    breakeven_cushion,
    stock_price,
    ma50,
    ma200,
    iv_rank,
    days_until_earnings,
    earnings_source,
    spread_percentage=None,
    open_interest=None,
    volume=None,
):
    """Build the complete transparent scorecard from existing calculator data."""

    components = {
        "DTE": score_dte(dte),
        "Delta": score_delta(delta),
        "Strike distance": score_strike_distance(strike_distance),
        "Breakeven cushion": score_breakeven_cushion(breakeven_cushion),
        "Trend": score_trend(stock_price, ma50, ma200),
        "IV Rank": score_iv_rank(iv_rank),
        "Earnings": score_earnings(days_until_earnings, dte, earnings_source),
        "Bid/ask liquidity": score_liquidity(spread_percentage),
        "Open interest": score_open_interest(open_interest),
        "Volume": score_volume(volume),
    }

    raw_total = sum(item["points"] for item in components.values())
    total = max(0, min(100, raw_total))

    concerns = [
        f"{name}: {item['detail']}"
        for name, item in components.items()
        if item["points"] < item["maximum"] * 0.6
    ][:5]
    positive_factors = [
        f"{name}: {item['detail']}"
        for name, item in components.items()
        if item["points"] >= item["maximum"] * 0.8
    ][:5]

    return {
        "components": components,
        "total": total,
        "maximum": 100,
        "assessment": classify_assessment(total),
        "concerns": concerns,
        "positive_factors": positive_factors,
    }
