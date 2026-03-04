# Discord Economic Calendar Alert — Setup Guide

This is **Part 1** of a two-part system:

| Part | What it does | Guide |
|---|---|---|
| **1 — Evening Preview** *(this file)* | Sends a message at 6 PM MT previewing the next day's events with market impact hints | `SETUP.md` |
| **2 — Actuals Reporter** | Sends a message ~5 min after each economic release with the actual number vs forecast | `ACTUALS_SETUP.md` |

Set up Part 1 first, then follow `ACTUALS_SETUP.md` to add the actuals reporter.

**Cost: $0. No server required.**

---

## How It Works

1. GitHub Actions runs a Python script every weekday at ~7:30 AM ET (free cloud scheduler)
2. The script fetches that week's economic events from Forex Factory (free, no API key)
3. It filters for USD events with High or Medium market impact scheduled for today
4. Each event gets a plain-English hint explaining what a beat/miss means for stocks
5. The result is posted to your Discord channel via a webhook

---

## Prerequisites

- A GitHub account (free) → [github.com](https://github.com)
- A Discord server where you have admin or "Manage Webhooks" permission
- Git installed on your machine → [git-scm.com](https://git-scm.com)

---

## Step 1 — Get a Discord Webhook URL

1. Open Discord and go to the channel you want alerts in
2. Click the gear icon (**Edit Channel**) next to the channel name
3. Go to **Integrations** → **Webhooks** → **New Webhook**
4. Give it a name (e.g. `Economic Calendar`) and click **Copy Webhook URL**
5. Save this URL — you'll need it in Step 4

---

## Step 2 — Create a GitHub Repository

1. Go to [github.com/new](https://github.com/new)
2. Name it something like `discord-alert-system`
3. Leave it **Public** (free GitHub Actions minutes are unlimited for public repos)
   > Private repos get 2,000 free minutes/month — more than enough, but public is simpler
4. Click **Create repository**

---

## Step 3 — Push the Files to GitHub

Open a terminal in this project folder and run:

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USERNAME/discord-alert-system.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

---

## Step 4 — Add the Discord Webhook as a Secret

GitHub needs your webhook URL to send messages. Store it as a secret (never put it directly in code).

1. Go to your repo on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Set:
   - **Name:** `DISCORD_WEBHOOK_URL`
   - **Value:** the webhook URL you copied in Step 1
5. Click **Add secret**

---

## Step 5 — Test It Manually

Don't wait until tomorrow morning — trigger it right now:

1. Go to your repo → **Actions** tab
2. Click **Daily Economic Calendar Alert** in the left sidebar
3. Click **Run workflow** → **Run workflow**
4. Wait ~30 seconds, then check your Discord channel

If you see a message, you're done. ✓

---

## Schedule

The alert fires every **Monday–Friday at 6:00 PM Mountain Time**, previewing the next day's events.

| Season | MT time | UTC time |
|---|---|---|
| Mountain Daylight Time (MDT, Mar–Nov) | 6:00 PM MDT | 00:00 UTC (next day) |
| Mountain Standard Time (MST, Nov–Mar) | 6:00 PM MST | 01:00 UTC (next day) |

**How DST is handled:** Two cron schedules run (00:00 and 01:00 UTC). The Python script checks the actual Mountain Time clock on each trigger and silently exits if it isn't 6 PM — so only the correct one fires each day, all year round.

> **Note:** GitHub's scheduler can run up to ~15 minutes late during high-traffic periods. This is normal.

To change the delivery time, update both cron lines in `.github/workflows/economic_alert.yml` and the hour check in `alert.py` (`if now_mt.hour != 18`). Use [worldtimeserver.com](https://www.worldtimeserver.com) to convert your desired MT time to UTC.

---

## What the Alert Looks Like

```
📊 Tomorrow's US Economic Events — Friday, March 7, 2026
🔴 2 High  |  🟡 1 Medium

Surprise beats/misses vs forecast drive short-term volatility.
Most data drops at 6:30 AM or 8:00 AM MT.

────────────────────────────────────────
🕐 6:30 AM MT — Non-Farm Employment Change
🔴 High Impact
Forecast: 170K  |  Previous: 143K
🔑 Biggest monthly mover. Strong jobs = bullish. Weak = bearish.
✅ Bullish if: higher than forecast

🕐 6:30 AM MT — Unemployment Rate
🔴 High Impact
Forecast: 4.1%  |  Previous: 4.0%
📉 Inverse relationship: lower rate = bullish. Higher = bearish.
✅ Bullish if: lower than forecast

🕐 8:00 AM MT — ISM Services PMI
🟡 Medium Impact
Forecast: 52.8  |  Previous: 52.1
🏢 Services = ~70% of US economy. >50 = bullish. Beats here drive broad rallies.
✅ Bullish if: above 50 and above forecast
────────────────────────────────────────
Source: Forex Factory  •  Times in Mountain Time  •  Not financial advice
```

---

## Covered Indicators

The alert includes impact hints for 30+ US economic events, including:

| Indicator | Why It Matters |
|---|---|
| Non-Farm Payrolls (NFP) | Biggest monthly market mover |
| CPI / Core CPI | Inflation gauge — drives Fed rate expectations |
| Core PCE | Fed's preferred inflation target (2% goal) |
| FOMC Rate Decision | Most powerful single event |
| GDP | Economy's report card |
| ISM Manufacturing / Services PMI | Expansion vs contraction signals |
| Retail Sales | Consumer health (70% of GDP) |
| Unemployment Rate | Labor market health |
| Jobless Claims | Weekly layoff tracker |
| ADP Employment | NFP preview (2 days early) |
| JOLTS Job Openings | Labor demand signal |
| Consumer Confidence / Michigan Sentiment | Spending outlook |
| PPI | Upstream inflation (leads CPI) |
| Durable Goods Orders | Manufacturing demand |
| Housing Starts / Building Permits | Construction activity |
| Fed Chair / FOMC Minutes | Rate path signals |

Any event not in the hint library still appears with a generic "compare actual vs forecast" note.

---

## Troubleshooting

**No message appeared after manual trigger**
- Check the Actions run log for errors (click the run → expand the "Send economic calendar alert" step)
- Verify the `DISCORD_WEBHOOK_URL` secret is set correctly (no extra spaces)
- Make sure the webhook wasn't deleted in Discord

**Scheduled runs stopped working**
- GitHub disables scheduled workflows on repos with **no activity for 60 days**
- Fix: push any small change (even a space in the README), or just trigger it manually from the Actions tab to reset the timer

**Wrong timezone / time**
- The script always uses US Eastern time (ET) for filtering and display
- GitHub Actions runs in UTC — the cron schedule is in UTC (see Schedule section above)

**Events missing from the feed**
- The Forex Factory feed covers the current week only; it refreshes each week
- On Mondays, the previous week's events are replaced with the new week's data
- Very rarely, the feed may be temporarily unavailable — the script will fail with an error visible in the Actions log

**The feed shows forecast/previous but not actual values**
- This is expected — the Forex Factory feed is pre-release only (scheduled events and forecasts)
- Actual numbers are reported by the companion actuals system — see `ACTUALS_SETUP.md`

---

## What's Next

Once the evening preview is working, set up the actuals reporter to receive real-time results as data drops throughout the trading day → **see `ACTUALS_SETUP.md`**

---

## Files Overview

```
discord-alert-system/
├── alert.py                              # Evening preview script
├── actuals.py                            # Actuals reporter script
├── requirements.txt                      # Python dependencies (shared)
├── SETUP.md                              # This file — evening preview setup
├── ACTUALS_SETUP.md                      # Actuals reporter setup
└── .github/
    └── workflows/
        ├── economic_alert.yml            # Cron: evening preview (6 PM MT weekdays)
        └── actuals_check.yml             # Cron: actuals check (5 min after each release)
```
