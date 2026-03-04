#!/usr/bin/env python3
"""
Economic Data Actuals Reporter

Runs ~5 minutes after each major US economic release window and posts
actual results to Discord with beat/miss analysis vs forecast.

Data source : Financial Modeling Prep free API (requires FMP_API_KEY)
Scheduling  : GitHub Actions — see .github/workflows/actuals_check.yml
Setup       : Set FMP_API_KEY and DISCORD_WEBHOOK_URL as GitHub secrets.
"""

import datetime
import json
import os
import sys
from zoneinfo import ZoneInfo

import requests

FMP_API_KEY = os.environ.get("FMP_API_KEY", "")
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
ET = ZoneInfo("America/New_York")
MT = ZoneInfo("America/Denver")

INCLUDE_IMPACT = {"high", "medium"}

# Lookback window — wide enough to absorb GitHub Actions latency (~15 min max)
LOOKBACK_MINUTES = 20

# Indicators where LOWER actual vs forecast = beat (bullish outcome)
LOWER_IS_BETTER_KEYS = [
    "unemployment rate",
    "jobless claims", "initial jobless claims", "continuing claims", "unemployment claims",
    "cpi", "consumer price index", "core cpi",
    "ppi", "producer price",
    "pce", "core pce", "personal consumption expenditure",
    "inflation",
]

IMPACT_EMOJI = {"high": "🔴", "medium": "🟡"}


# ---------------------------------------------------------------------------
# Beat / miss logic
# ---------------------------------------------------------------------------

def lower_is_better(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in LOWER_IS_BETTER_KEYS)


def beat_miss(title: str, actual, forecast) -> tuple[str, int]:
    """Returns (label, discord_color)."""
    if forecast is None:
        return "📊 Released", 9807270  # Gray — no forecast to compare
    try:
        a, f = float(actual), float(forecast)
    except (TypeError, ValueError):
        return "📊 Released", 9807270
    if a == f:
        return "➖ In-Line", 9807270
    beat = (a < f) if lower_is_better(title) else (a > f)
    return ("✅ Beat", 5763719) if beat else ("❌ Miss", 15548997)


def fmt(v) -> str:
    """Format a numeric value cleanly (no trailing .0)."""
    if v is None:
        return "N/A"
    try:
        f = float(v)
        return str(int(f)) if f == int(f) else f"{f:g}"
    except (TypeError, ValueError):
        return str(v)


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_actuals() -> list[dict]:
    """Fetch today's USD events that have actual values within the lookback window."""
    now_et = datetime.datetime.now(ET)
    cutoff = now_et - datetime.timedelta(minutes=LOOKBACK_MINUTES)
    date_str = now_et.date().isoformat()

    url = (
        f"https://financialmodelingprep.com/api/v3/economic_calendar"
        f"?from={date_str}&to={date_str}&apikey={FMP_API_KEY}"
    )
    resp = requests.get(
        url,
        headers={"User-Agent": "discord-economic-alert-bot/1.0"},
        timeout=15,
    )
    resp.raise_for_status()

    results = []
    for item in resp.json():
        if item.get("country") != "US":
            continue
        impact = (item.get("impact") or "").lower()
        if impact not in INCLUDE_IMPACT:
            continue
        if item.get("actual") is None:
            continue
        try:
            event_dt = datetime.datetime.strptime(
                item["date"], "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=ET)
        except Exception:
            continue
        # Only report events released within the lookback window
        if not (cutoff <= event_dt <= now_et):
            continue
        item["_dt_et"] = event_dt
        results.append(item)

    results.sort(key=lambda e: e["_dt_et"])
    return results


# ---------------------------------------------------------------------------
# Discord payload
# ---------------------------------------------------------------------------

def build_payload(events: list[dict]) -> dict:
    now_et = datetime.datetime.now(ET)
    today = now_et.date()
    date_str = f"{today.strftime('%A, %B')} {today.day}, {today.year}"

    fields = []
    colors = []

    for ev in events:
        title = ev.get("event", "Unknown")
        actual = ev.get("actual")
        forecast = ev.get("estimate")
        previous = ev.get("previous")
        impact = (ev.get("impact") or "").lower()
        impact_emoji = IMPACT_EMOJI.get(impact, "⚪")

        label, color = beat_miss(title, actual, forecast)
        colors.append(color)

        dt_mt = ev["_dt_et"].astimezone(MT)
        time_str = dt_mt.strftime("%-I:%M %p MT")

        value = (
            f"{impact_emoji} {label}\n"
            f"Actual: **`{fmt(actual)}`**  |  "
            f"Forecast: `{fmt(forecast)}`  |  "
            f"Previous: `{fmt(previous)}`"
        )
        fields.append({
            "name": f"🕐 {time_str}  —  {title}",
            "value": value,
            "inline": False,
        })

    # Embed color: red if any miss, green if all beats, gray if all in-line
    if 15548997 in colors:
        dominant = 15548997   # Red — at least one miss
    elif 5763719 in colors:
        dominant = 5763719    # Green — beats only
    else:
        dominant = 9807270    # Gray — all in-line or no forecasts

    embed = {
        "title": f"📈 Economic Results — {date_str}",
        "description": "Actual numbers just released. **Bold** = actual value.",
        "color": dominant,
        "fields": fields[:25],
        "footer": {
            "text": "Source: Financial Modeling Prep  •  Times in Mountain Time  •  Not financial advice"
        },
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    return {"username": "Economic Calendar", "embeds": [embed]}


def send_webhook(url: str, payload: dict) -> None:
    resp = requests.post(
        url,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    if resp.status_code == 204:
        print("✓ Discord actuals alert sent.")
    else:
        print(f"✗ Discord returned {resp.status_code}: {resp.text}")
        resp.raise_for_status()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if not FMP_API_KEY:
        print("ERROR: FMP_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)
    if not WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK_URL environment variable not set.", file=sys.stderr)
        sys.exit(1)

    print(f"Checking for actuals released in the past {LOOKBACK_MINUTES} minutes...")
    events = fetch_actuals()
    print(f"Found {len(events)} event(s) with actuals in the window.")

    if not events:
        print("Nothing to report — exiting.")
        return

    payload = build_payload(events)
    send_webhook(WEBHOOK_URL, payload)


if __name__ == "__main__":
    main()
