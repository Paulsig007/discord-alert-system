#!/usr/bin/env python3
"""
Discord Economic Calendar Alert Bot
Sends daily US economic event alerts with stock market impact hints.

Data source : Forex Factory via nfs.faireconomy.media (free, no API key)
Scheduling  : GitHub Actions cron (see .github/workflows/economic_alert.yml)
Setup       : Set DISCORD_WEBHOOK_URL as a GitHub Actions secret (or env var).
"""

import datetime
import json
import os
import sys
from zoneinfo import ZoneInfo

import requests
from dateutil import parser as date_parser

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
ET = ZoneInfo("America/New_York")

# Which impact levels to include in the alert
INCLUDE_IMPACT = {"High", "Medium"}

# ---------------------------------------------------------------------------
# Market-impact hint library
# Match on lowercase substrings in the event title.
# ---------------------------------------------------------------------------

HINTS = [
    {
        "keys": ["non-farm", "nonfarm", "non farm", "nfp"],
        "icon": "🔑",
        "body": "Biggest monthly mover. Strong jobs = bullish (economy growing). Weak = bearish (slowdown).",
        "bullish": "higher than forecast",
    },
    {
        "keys": ["unemployment rate"],
        "icon": "📉",
        "body": "Inverse relationship: lower rate = bullish (tight labor market). Higher = bearish.",
        "bullish": "lower than forecast",
    },
    {
        "keys": ["core cpi"],
        "icon": "🔥",
        "body": "Core inflation (ex food & energy). Fed watches closely. Hot = bearish (rate hike risk). Cool = bullish.",
        "bullish": "at or below forecast / cooling trend",
    },
    {
        "keys": ["cpi", "consumer price index"],
        "icon": "🔥",
        "body": "Headline inflation gauge. Above forecast = bearish (Fed stays hawkish). Below = bullish (rate cuts).",
        "bullish": "at or below forecast",
    },
    {
        "keys": ["core pce"],
        "icon": "🎯",
        "body": "Fed's #1 preferred inflation target (2% goal). Hot = rate hike risk = bearish. Cool = bullish.",
        "bullish": "at/below 2% or below forecast",
    },
    {
        "keys": ["pce", "personal consumption expenditure", "personal spending"],
        "icon": "💳",
        "body": "Consumer spending + Fed's inflation gauge. Above forecast = bearish. Below = bullish.",
        "bullish": "below forecast",
    },
    {
        "keys": ["ppi", "producer price"],
        "icon": "⚙️",
        "body": "Upstream inflation (what factories pay). High PPI → future CPI pressure → bearish.",
        "bullish": "at or below forecast",
    },
    {
        "keys": ["ism manufacturing"],
        "icon": "🏭",
        "body": "Scale: >50 = expansion (bullish), <50 = contraction (bearish). Big mover for industrials & tech.",
        "bullish": "above 50 and above forecast",
    },
    {
        "keys": ["ism services", "ism non-manufacturing"],
        "icon": "🏢",
        "body": "Services = ~70% of US economy. >50 = bullish. Beats here drive broad market rallies.",
        "bullish": "above 50 and above forecast",
    },
    {
        "keys": ["pmi", "purchasing managers"],
        "icon": "🏭",
        "body": "PMI scale: >50 = expansion (bullish), <50 = contraction (bearish). Watch manufacturing vs services.",
        "bullish": "above 50 / above forecast",
    },
    {
        "keys": ["fomc minutes", "fed minutes"],
        "icon": "📋",
        "body": "Transcript of last Fed meeting. Hawkish tone (inflation fear) = bearish. Dovish (cut hints) = bullish.",
        "bullish": "dovish language / rate cut signals",
    },
    {
        "keys": ["fomc", "fed rate", "federal funds", "interest rate decision"],
        "icon": "🏦",
        "body": "Rate cut = bullish (cheaper money). Rate hike = bearish. Watch the statement language too.",
        "bullish": "rate cut or dovish forward guidance",
    },
    {
        "keys": ["fed chair", "powell", "fed speak"],
        "icon": "🎙️",
        "body": "Fed chair comments move markets. Hawkish = bearish. Dovish = bullish. Watch tone carefully.",
        "bullish": "dovish / rate cut signals",
    },
    {
        "keys": ["gdp"],
        "icon": "📊",
        "body": "Economy's report card. Beat = bullish. Miss = bearish. Negative = recession fear → sharp selloff.",
        "bullish": "higher than forecast",
    },
    {
        "keys": ["retail sales"],
        "icon": "🛒",
        "body": "Consumer spending = 70% of GDP. Beat = bullish (consumers healthy). Miss = bearish.",
        "bullish": "higher than forecast",
    },
    {
        "keys": ["adp nonfarm", "adp non-farm", "adp employment"],
        "icon": "👔",
        "body": "Private payrolls preview — released 2 days before NFP. Beat sets bullish expectations for NFP.",
        "bullish": "higher than forecast",
    },
    {
        "keys": ["jolts", "job openings"],
        "icon": "💼",
        "body": "Labor demand. High openings = bullish (employers still hiring). Sharp drop = slowdown signal.",
        "bullish": "higher than forecast",
    },
    {
        "keys": ["initial jobless claims", "jobless claims", "unemployment claims"],
        "icon": "📋",
        "body": "Weekly layoffs tracker. Lower claims = bullish (fewer job losses). Higher = bearish.",
        "bullish": "lower than forecast",
    },
    {
        "keys": ["consumer confidence"],
        "icon": "😊",
        "body": "Spending outlook. Higher = bullish (people feel secure = more spending ahead). Lower = bearish.",
        "bullish": "higher than forecast",
    },
    {
        "keys": ["michigan", "consumer sentiment", "umich"],
        "icon": "📊",
        "body": "Consumer mood. Beat = bullish. Watch embedded inflation expectations — key Fed input.",
        "bullish": "higher than forecast",
    },
    {
        "keys": ["durable goods"],
        "icon": "🔧",
        "body": "Big-ticket orders (aircraft, machines). Beat = bullish for industrials. Very volatile month-to-month.",
        "bullish": "higher than forecast",
    },
    {
        "keys": ["housing starts"],
        "icon": "🏗️",
        "body": "New home construction begins. Beat = bullish for homebuilders & materials. Rate-sensitive.",
        "bullish": "higher than forecast",
    },
    {
        "keys": ["building permits"],
        "icon": "📝",
        "body": "Forward-looking housing signal. More permits = more future supply. Beat = bullish for builders.",
        "bullish": "higher than forecast",
    },
    {
        "keys": ["existing home sales"],
        "icon": "🏡",
        "body": "Used home sales. Beat = bullish for real estate & financials. Sensitive to mortgage rates.",
        "bullish": "higher than forecast",
    },
    {
        "keys": ["new home sales"],
        "icon": "🏠",
        "body": "New construction sales. Beat = bullish. Leading indicator for broader housing activity.",
        "bullish": "higher than forecast",
    },
    {
        "keys": ["trade balance", "current account"],
        "icon": "🌐",
        "body": "Exports minus imports. Narrowing deficit = bullish (more exports). Widening = mild bearish signal.",
        "bullish": "deficit narrows",
    },
    {
        "keys": ["industrial production"],
        "icon": "⚙️",
        "body": "Factory & utility output. Beat = bullish for industrials/energy. Confirms or denies PMI signals.",
        "bullish": "higher than forecast",
    },
    {
        "keys": ["empire state", "philly fed", "chicago pmi", "dallas fed", "richmond fed", "kansas city fed"],
        "icon": "🗺️",
        "body": "Regional manufacturing index. Leading indicator for national ISM. Beat = early bullish signal.",
        "bullish": "above 0 / above forecast",
    },
    {
        "keys": ["crude oil inventories", "oil inventories", "eia crude"],
        "icon": "🛢️",
        "body": "Weekly oil supply. Inventory draw (less supply) = bullish for energy stocks. Build = bearish energy.",
        "bullish": "inventory draw",
    },
    {
        "keys": ["treasury", "bond auction", "note auction"],
        "icon": "💵",
        "body": "Debt demand check. Weak demand = yields rise = bearish growth stocks. Strong demand = yields dip = bullish.",
        "bullish": "strong bid-to-cover ratio",
    },
    {
        "keys": ["factory orders"],
        "icon": "📦",
        "body": "Manufacturing demand. Beat = bullish for industrials. Lags PMI by ~1 month.",
        "bullish": "higher than forecast",
    },
    {
        "keys": ["capacity utilization"],
        "icon": "🔩",
        "body": ">80% = potential inflationary pressure. Rising trend = bullish for industrials.",
        "bullish": "higher than forecast (watch inflation ceiling)",
    },
]

DEFAULT_HINT = {
    "icon": "📌",
    "body": "Compare actual vs forecast — surprise beats/misses drive short-term volatility.",
    "bullish": "beats forecast",
}

IMPACT_EMOJI = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
IMPACT_COLOR = {
    "High": 15548997,    # Red
    "Medium": 16744272,  # Orange
    "Low": 5763719,      # Green
}


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def get_hint(title: str) -> dict:
    t = title.lower()
    for h in HINTS:
        if any(k in t for k in h["keys"]):
            return h
    return DEFAULT_HINT


def fetch_events(today: datetime.date) -> list[dict]:
    """Return today's USD high/medium impact events, sorted by time."""
    headers = {"User-Agent": "discord-economic-alert-bot/1.0"}
    resp = requests.get(CALENDAR_URL, headers=headers, timeout=15)
    resp.raise_for_status()

    events = []
    for item in resp.json():
        if item.get("country") != "USD":
            continue
        if item.get("impact") not in INCLUDE_IMPACT:
            continue
        try:
            dt_et = date_parser.parse(item["date"]).astimezone(ET)
        except Exception:
            continue
        if dt_et.date() == today:
            item["_dt"] = dt_et
            events.append(item)

    events.sort(key=lambda e: e["_dt"])
    return events


def build_payload(events: list[dict], today: datetime.date) -> dict:
    """Build the Discord webhook payload with embeds."""
    date_str = f"{today.strftime('%A, %B')} {today.day}, {today.year}"

    if not events:
        embed = {
            "title": f"📅 US Economic Calendar — {date_str}",
            "description": "No high or medium impact USD events scheduled today. Clear calendar — focus on price action.",
            "color": 9807270,  # Gray
            "footer": {"text": "Source: Forex Factory  •  Not financial advice"},
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        return {"username": "Economic Calendar", "embeds": [embed]}

    # Dominant color: red if any High impact event, else orange
    color = IMPACT_COLOR["High"] if any(e["impact"] == "High" for e in events) else IMPACT_COLOR["Medium"]
    high_count = sum(1 for e in events if e["impact"] == "High")
    med_count = sum(1 for e in events if e["impact"] == "Medium")

    count_parts = []
    if high_count:
        count_parts.append(f"🔴 {high_count} High")
    if med_count:
        count_parts.append(f"🟡 {med_count} Medium")
    count_str = "  |  ".join(count_parts)

    fields = []
    for ev in events[:25]:  # Discord hard limit: 25 fields
        dt: datetime.datetime = ev["_dt"]
        time_str = dt.strftime("%-I:%M %p ET")
        hint = get_hint(ev["title"])
        forecast = ev.get("forecast") or "N/A"
        previous = ev.get("previous") or "N/A"
        emoji = IMPACT_EMOJI.get(ev["impact"], "⚪")

        value = (
            f"{emoji} **{ev['impact']} Impact**\n"
            f"`Forecast: {forecast}`  |  `Previous: {previous}`\n"
            f"{hint['icon']} {hint['body']}\n"
            f"> ✅ Bullish if: *{hint['bullish']}*"
        )
        fields.append({
            "name": f"🕐 {time_str}  —  {ev['title']}",
            "value": value,
            "inline": False,
        })

    embed = {
        "title": f"📊 US Economic Calendar — {date_str}",
        "description": (
            f"{count_str}\n\n"
            "Surprise beats/misses vs forecast drive short-term volatility.\n"
            "Release times are Eastern — most data drops at **8:30 AM** or **10:00 AM ET**."
        ),
        "color": color,
        "fields": fields,
        "footer": {"text": "Source: Forex Factory  •  Times in US Eastern  •  Not financial advice"},
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
        print("✓ Discord alert sent successfully.")
    else:
        print(f"✗ Discord returned {resp.status_code}: {resp.text}")
        resp.raise_for_status()


def main() -> None:
    if not WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK_URL environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    today = datetime.datetime.now(ET).date()
    print(f"Fetching economic events for {today} (ET)...")

    events = fetch_events(today)
    print(f"Found {len(events)} USD high/medium impact event(s).")

    payload = build_payload(events, today)
    send_webhook(WEBHOOK_URL, payload)


if __name__ == "__main__":
    main()
