"""Deterministic, network-free report from a fictional fixture, not API data."""

import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path


DEFAULT_FIXTURE = Path(__file__).resolve().parents[1] / "examples/fixtures/demo.json"
NUMBERS = ("revenue_current_usd", "revenue_previous_usd", "call_premium_usd", "put_premium_usd")


def load_fixture(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError("Fixture exceeds 64 KiB")
    return json.loads(raw)


def render_brief(data, source="examples/fixtures/demo.json"):
    if not isinstance(data, dict) or data.get("synthetic") is not True:
        raise ValueError("This runner accepts synthetic fixtures only")
    ticker = data.get("ticker", "")
    if not isinstance(ticker, str) or not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,11}", ticker):
        raise ValueError("Ticker must contain 1–12 uppercase letters, digits, dots or hyphens")
    try:
        stamp = datetime.fromisoformat(data["as_of"])
    except (KeyError, ValueError, TypeError):
        raise ValueError("as_of must be an ISO timestamp with timezone") from None
    if stamp.tzinfo is None:
        raise ValueError("as_of must include a timezone")
    for key in ("revenue_period_current", "revenue_period_previous"):
        value = data.get(key, "")
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-Q[1-4]", value):
            raise ValueError(f"{key} must have the form YYYY-Q1 through YYYY-Q4")
    values = {}
    for key in NUMBERS:
        value = data.get(key)
        if value is None:
            values[key] = None
            continue
        if type(value) not in (int, float):
            raise ValueError(f"{key} must be a number or null")
        number = Decimal(str(value))
        if not number.is_finite() or not 0 <= number <= Decimal("1e15"):
            raise ValueError(f"{key} must be finite and between 0 and 1e15")
        values[key] = number
    current, previous, calls, puts = (values[key] for key in NUMBERS)
    revenue = "Revenue comparison unavailable: missing value or zero prior revenue."
    if current is not None and previous is not None and previous > 0:
        change = (current - previous) / previous * 100
        revenue = f"Revenue change: {change:.2f}% ({data['revenue_period_previous']} → {data['revenue_period_current']}). [1]"
    mix = "Premium mix unavailable: missing values or zero total premium."
    if calls is not None and puts is not None and calls + puts > 0:
        mix = f"Call share of observed premium: {calls / (calls + puts) * 100:.2f}%. [1]"
    # JSON string encoding keeps a user-chosen path on one line; never render it as HTML.
    source_label = json.dumps(str(source), ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e")
    return "\n".join([
        f"# {ticker} · Ticker Investigator", "", "**SYNTHETIC DEMO — all values are fictional.**",
        f"Fixture timestamp: {stamp.isoformat()}", "", "## Observations", "",
        f"- {revenue}", f"- {mix}",
        "- Premium mix alone does not establish trade direction or investor intent.",
        "", "## Gaps", "", "No live Skylit data, SEC filings, prices or recommendations are included.",
        "", "## Sources", "", f"[1] Synthetic fixture: {source_label}.",
        "Revenue fields illustrate filing facts; premium fields illustrate market observations.",
        "This fixture is not an API response schema.", "", "## Usage", "",
        "0 network requests · 0 model calls · 0 Skylit credits", "",
    ])
