# Economic Data Actuals — Setup Guide

Sends a Discord alert ~5 minutes after each major US economic data release, showing the actual number vs forecast with a beat/miss result.

This is a companion to the evening preview system. The preview tells you what's coming — this tells you what the number was.

---

## How It Works

1. GitHub Actions runs `actuals.py` automatically, 5 minutes after each major release window
2. The script calls the Financial Modeling Prep (FMP) API to get today's economic calendar
3. It filters for events where the `actual` field is now populated (data has dropped) and the release was within the past 20 minutes
4. If events are found, it posts a Discord embed showing actual vs forecast vs previous, color-coded by beat/miss
5. If nothing was released in that window, the script exits silently — no noise

---

## Prerequisites

- The evening preview system already set up (see `SETUP.md`)
- A free FMP account → [financialmodelingprep.com](https://site.financialmodelingprep.com/register)

---

## Step 1 — Get a Free FMP API Key

1. Go to [financialmodelingprep.com](https://site.financialmodelingprep.com/register) and create a free account
2. After signing in, go to your **Dashboard**
3. Copy your **API Key** from the dashboard

**Free tier limits:** 250 requests/day. This system uses at most 6 API calls per weekday (one per cron trigger), well within the limit.

---

## Step 2 — Add the FMP Key as a GitHub Secret

1. Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Set:
   - **Name:** `FMP_API_KEY`
   - **Value:** your FMP API key
4. Click **Add secret**

You should now have two secrets:
- `DISCORD_WEBHOOK_URL` *(from the preview setup)*
- `FMP_API_KEY` *(just added)*

---

## Step 3 — Push the New Files

```bash
git add .
git commit -m "add actuals reporting"
git push
```

The workflow activates automatically once pushed.

---

## Step 4 — Test It

From the GitHub **Actions** tab → **Economic Data Actuals Check** → **Run workflow**.

> **Note:** If you trigger it manually outside of a release window, it will likely report nothing (no actuals in the past 20 minutes). To see it work, trigger it within 20 minutes of a real economic release, or wait for the next scheduled run.

---

## Release Windows Covered

The system fires 5 minutes after each of these standard US release times:

| Release time (ET) | What it covers |
|---|---|
| **8:30 AM** | NFP, CPI, Core CPI, PPI, GDP, Retail Sales, Housing Starts, Building Permits, Trade Balance, Jobless Claims, PCE |
| **10:00 AM** | ISM Manufacturing PMI, ISM Services PMI, Consumer Confidence, JOLTS Job Openings, Existing/New Home Sales |
| **2:00 PM** | FOMC Rate Decision |

Occasional releases outside these windows (e.g. EIA crude oil at 10:30 AM, some Treasury auctions at 3:00 PM) will not be caught automatically. These are lower-priority events and can be added later if needed.

---

## What the Alert Looks Like

```
📈 Economic Results — Friday, March 7, 2026
Actual numbers just released. Bold = actual value.

────────────────────────────────────────
🕐 6:30 AM MT — Non-Farm Employment Change
🔴 ✅ Beat
Actual: 227  |  Forecast: 170  |  Previous: 143

🕐 6:30 AM MT — Unemployment Rate
🔴 ❌ Miss
Actual: 4.2  |  Forecast: 4.0  |  Previous: 4.0

🕐 6:30 AM MT — Average Hourly Earnings m/m
🟡 ➖ In-Line
Actual: 0.3  |  Forecast: 0.3  |  Previous: 0.4
────────────────────────────────────────
Source: Financial Modeling Prep  •  Times in Mountain Time  •  Not financial advice
```

**Embed colors:**
- 🟢 Green — all released events beat their forecasts
- 🔴 Red — at least one event missed its forecast
- ⚫ Gray — all in-line, or no forecasts available to compare

---

## How Beat / Miss Is Determined

For most indicators, **higher actual = beat** (economy growing faster than expected = bullish).

For the following indicators, **lower actual = beat** (less inflation / fewer job losses = bullish):

- Unemployment Rate
- Initial / Continuing Jobless Claims
- CPI / Core CPI
- PPI / Producer Price
- PCE / Core PCE
- Any event title containing "inflation"

---

## How DST Is Handled

Each release window has two cron entries — one for Eastern Daylight Time (EDT, summer) and one for Eastern Standard Time (EST, winter). The script uses a 20-minute lookback window, so only the run that fires close to the actual release time will find events. The other run finds nothing and exits silently.

| Release | EDT cron (UTC) | EST cron (UTC) |
|---|---|---|
| 8:30 AM ET | `35 12 * * 1-5` | `35 13 * * 1-5` |
| 10:00 AM ET | `5 14 * * 1-5` | `5 15 * * 1-5` |
| 2:00 PM ET | `5 18 * * 1-5` | `5 19 * * 1-5` |

---

## Troubleshooting

**No message appeared after a major release**
- Check the Actions run log for errors (Actions tab → the run → expand "Check and report actuals")
- Verify `FMP_API_KEY` secret is set correctly
- FMP occasionally takes a few minutes to populate the `actual` field. The 20-minute window should absorb this, but very rarely data is delayed longer

**Getting an API error from FMP**
- Verify your API key is active at [financialmodelingprep.com](https://financialmodelingprep.com)
- Free tier allows 250 requests/day — this system uses at most 6/day, so limits should never be hit

**Seeing duplicate messages for the same event**
- This shouldn't happen — the 20-minute lookback windows are designed to be non-overlapping across the two DST crons
- If it does occur, check that both cron entries for the same window aren't both firing within 20 minutes of each other (they're scheduled 1 hour apart, so this would only happen if GitHub Actions is severely delayed)

**Event released at an unusual time (e.g. 10:30 AM, 3:00 PM)**
- The system covers the three most common release windows. Events outside these windows won't be caught automatically
- You can add additional cron pairs to `actuals_check.yml` following the same EDT/EST pattern if needed

---

## Files

```
discord-alert-system/
├── actuals.py                              # Actuals reporter script
└── .github/
    └── workflows/
        └── actuals_check.yml               # GitHub Actions scheduler for actuals
```
