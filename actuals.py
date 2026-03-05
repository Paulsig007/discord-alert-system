#!/usr/bin/env python3
"""
Economic Data Actuals Reporter

Runs ~5 minutes after each major US economic release window and posts
actual results to Discord with beat/miss analysis vs forecast.

Data source : Forex Factory via nfs.faireconomy.media (free, no API key)
Scheduling  : GitHub Actions — see .github/workflows/actuals_check.yml
Setup       : Set DISCORD_WEBHOOK_URL as a GitHub Actions secret.
"""

import datetime
import json
import os
import sys
from zoneinfo import ZoneInfo

import requests
from dateutil import parser as date_parser

CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
ET = ZoneInfo("America/New_York")
MT = ZoneInfo("America/Denver")

INCLUDE_IMPACT = {"High", "Medium"}

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

IMPACT_EMOJI = {"High": "🔴", "Medium": "🟡"}


# ---------------------------------------------------------------------------
# Value parsing — FF uses formatted strings like "248K", "3.2%", "-0.1M"
# ---------------------------------------------------------------------------

def parse_ff_number(s) -> float | None:
    """Parse Forex Factory value strings to float for comparison."""
    if s is None:
        return None
    s = str(s).strip().replace(",", "")
    if not s:
        return None
    multiplier = 1.0
    if s.endswith("%"):
        s = s[:-1]
    elif s.endswith("K"):
        multiplier = 1_000
        s = s[:-1]
    elif s.endswith("M"):
        multiplier = 1_000_000
        s = s[:-1]
    elif s.endswith("B"):
        multiplier = 1_000_000_000
        s = s[:-1]
    try:
        return float(s) * multiplier
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Beat / miss logic
# ---------------------------------------------------------------------------

def lower_is_better(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in LOWER_IS_BETTER_KEYS)


def beat_miss(title: str, actual, forecast) -> tuple[str, int]:
    """Returns (label, discord_color)."""
    a = parse_ff_number(actual)
    f = parse_ff_number(forecast)
    if a is None or f is None:
        return "📊 Released", 9807270  # Gray — no forecast to compare
    if a == f:
        return "➖ In-Line", 9807270
    beat = (a < f) if lower_is_better(title) else (a > f)
    return ("✅ Beat", 5763719) if beat else ("❌ Miss", 15548997)


def fmt(v) -> str:
    """Return value as-is if it's a non-empty string, else 'N/A'."""
    if v is None:
        return "N/A"
    s = str(v).strip()
    return s if s else "N/A"


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_actuals() -> list[dict]:
    """Fetch today's USD events that have actual values within the lookback window."""
    now_et = datetime.datetime.now(ET)
    cutoff = now_et - datetime.timedelta(minutes=LOOKBACK_MINUTES)

    resp = requests.get(
        CALENDAR_URL,
        headers={"User-Agent": "discord-economic-alert-bot/1.0"},
        timeout=15,
    )
    resp.raise_for_status()

    results = []
    for item in resp.json():
        if item.get("country") != "USD":
            continue
        if item.get("impact") not in INCLUDE_IMPACT:
            continue
        actual = item.get("actual")
        if actual is None or str(actual).strip() == "":
            continue
        try:
            dt_et = date_parser.parse(item["date"]).astimezone(ET)
        except Exception:
            continue
        # Only report events released within the lookback window
        if not (cutoff <= dt_et <= now_et):
            continue
        item["_dt_et"] = dt_et
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
        title = ev.get("title", "Unknown")
        actual = ev.get("actual")
        forecast = ev.get("forecast")
        previous = ev.get("previous")
        impact = ev.get("impact", "")
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
            "text": "Source: Forex Factory  •  Times in Mountain Time  •  Not financial advice"
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
