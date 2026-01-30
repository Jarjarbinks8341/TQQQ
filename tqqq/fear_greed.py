"""CNN Fear & Greed Index fetcher and formatter."""

import json
import urllib.request
from typing import Dict, Optional

API_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

# Score ranges
RATING_RANGES = [
    (0, 24, "Extreme Fear"),
    (25, 44, "Fear"),
    (45, 55, "Neutral"),
    (56, 74, "Greed"),
    (75, 100, "Extreme Greed"),
]


def _score_to_rating(score: float) -> str:
    """Convert numeric score to rating label."""
    for low, high, label in RATING_RANGES:
        if low <= score <= high:
            return label
    return "Unknown"


def fetch_fear_greed() -> Optional[Dict]:
    """Fetch current CNN Fear & Greed Index data.

    Returns:
        Dict with keys: score, rating, timestamp, previous_close,
        one_week_ago, one_month_ago, one_year_ago, and components.
        Returns None on failure.
    """
    try:
        req = urllib.request.Request(
            API_URL,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.cnn.com/markets/fear-and-greed",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Failed to fetch Fear & Greed Index: {e}")
        return None

    try:
        fg = data.get("fear_and_greed", {})
        score = fg.get("score", 0)
        timestamp = fg.get("timestamp", "")

        result = {
            "score": round(score, 1),
            "rating": _score_to_rating(score),
            "timestamp": timestamp,
        }

        # Historical comparisons
        for key in ("previous_close", "one_week_ago", "one_month_ago", "one_year_ago"):
            val = fg.get(key)
            if val is not None:
                result[key] = {
                    "score": round(val, 1),
                    "rating": _score_to_rating(val),
                }

        # Component indicators
        component_keys = [
            ("market_momentum_sp500", "Market Momentum (S&P 500)"),
            ("stock_price_strength", "Stock Price Strength"),
            ("stock_price_breadth", "Stock Price Breadth"),
            ("put_call_options", "Put/Call Options"),
            ("junk_bond_demand", "Junk Bond Demand"),
            ("market_volatility_vix", "Market Volatility (VIX)"),
            ("safe_haven_demand", "Safe Haven Demand"),
        ]

        components = []
        for api_key, display_name in component_keys:
            comp = data.get(api_key)
            if comp and isinstance(comp, dict):
                comp_score = comp.get("score")
                if comp_score is not None:
                    components.append({
                        "name": display_name,
                        "score": round(comp_score, 1),
                        "rating": _score_to_rating(comp_score),
                    })

        result["components"] = components
        return result

    except Exception as e:
        print(f"Failed to parse Fear & Greed data: {e}")
        return None


def format_fear_greed_message(data: Dict) -> str:
    """Format Fear & Greed data into a readable message.

    Args:
        data: Dict returned by fetch_fear_greed()

    Returns:
        Formatted multi-line string.
    """
    score = data["score"]
    rating = data["rating"]

    # Emoji based on rating
    emoji_map = {
        "Extreme Fear": "😱",
        "Fear": "😰",
        "Neutral": "😐",
        "Greed": "😏",
        "Extreme Greed": "🤑",
    }
    emoji = emoji_map.get(rating, "❓")

    lines = [
        f"{emoji} CNN Fear & Greed Index: {score} ({rating})",
        "",
    ]

    # Historical comparisons
    history_keys = [
        ("previous_close", "Previous Close"),
        ("one_week_ago", "1 Week Ago"),
        ("one_month_ago", "1 Month Ago"),
        ("one_year_ago", "1 Year Ago"),
    ]
    for key, label in history_keys:
        if key in data:
            h = data[key]
            lines.append(f"  {label:16s}: {h['score']:5.1f} ({h['rating']})")

    # Components
    if data.get("components"):
        lines.append("")
        lines.append("Components:")
        for comp in data["components"]:
            lines.append(
                f"  {comp['name']:32s}: {comp['score']:5.1f} ({comp['rating']})"
            )

    return "\n".join(lines)
