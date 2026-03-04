# Discord Economic Calendar Alert — Setup Guide

Sends a daily Discord message every weekday morning listing US economic events (NFP, CPI, PMI, etc.) with stock market impact hints.

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

The alert fires automatically at **12:30 UTC every Monday–Friday**, which is:

| Season | Local time |
|---|---|
| Eastern Standard Time (EST, Nov–Mar) | 7:30 AM ET |
| Eastern Daylight Time (EDT, Mar–Nov) | 8:30 AM ET |

This is before US market open (9:30 AM ET), giving you time to review upcoming events.

> **Note:** GitHub's scheduler can run up to ~15 minutes late during high-traffic periods. This is normal.

To change the time, edit the `cron` line in `.github/workflows/economic_alert.yml`:

```yaml
- cron: '30 12 * * 1-5'   # minute hour day month weekday (UTC)
```

Examples:
```
'0 13 * * 1-5'   →  1:00 PM UTC  =  9:00 AM ET
'0 14 * * 1-5'   →  2:00 PM UTC  =  10:00 AM ET
'0 9 * * 1-5'    →  9:00 AM UTC  =  5:00 AM ET
```

---

## What the Alert Looks Like

```
📊 US Economic Calendar — Friday, March 7, 2026
🔴 2 High  |  🟡 1 Medium

Surprise beats/misses vs forecast drive short-term volatility.
Release times are Eastern — most data drops at 8:30 AM or 10:00 AM ET.

────────────────────────────────────────
🕐 8:30 AM ET — Non-Farm Employment Change
🔴 High Impact
Forecast: 170K  |  Previous: 143K
🔑 Biggest monthly mover. Strong jobs = bullish. Weak = bearish.
✅ Bullish if: higher than forecast

🕐 8:30 AM ET — Unemployment Rate
🔴 High Impact
Forecast: 4.1%  |  Previous: 4.0%
📉 Inverse relationship: lower rate = bullish. Higher = bearish.
✅ Bullish if: lower than forecast

🕐 10:00 AM ET — ISM Services PMI
🟡 Medium Impact
Forecast: 52.8  |  Previous: 52.1
🏢 Services = ~70% of US economy. >50 = bullish. Beats here drive broad rallies.
✅ Bullish if: above 50 and above forecast
────────────────────────────────────────
Source: Forex Factory  •  Times in US Eastern  •  Not financial advice
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
- This is a known limitation of the free Forex Factory feed — it only shows scheduled/expected data
- Actual released values require a paid API (e.g. Financial Modeling Prep)
- For the purpose of a morning briefing, forecast + previous is all you need

---

## Files Overview

```
discord-alert-system/
├── alert.py                          # Main script
├── requirements.txt                  # Python dependencies
├── SETUP.md                          # This file
└── .github/
    └── workflows/
        └── economic_alert.yml        # GitHub Actions scheduler
```
