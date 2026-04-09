# BootBot Architecture

This document explains how the bot works so you (or an LLM) can modify it or replicate the pattern for a different use case.

## Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│ austin2step  │────>│  scraper.py  │────>│    bot.py        │────>│  Green API   │
│   .com       │     │  (Playwright)│     │  (orchestrator)  │     │  (WhatsApp)  │
└─────────────┘     └──────────────┘     └─────────────────┘     └──────────────┘
   Website            Headless browser      Formats poll &          Sends poll to
   (JS-rendered)      scrapes & parses      sends via API           WhatsApp group
```

## Component Details

### 1. `scraper.py` — Web Scraper

**Purpose:** Fetch today's dance events from austin2step.com.

**Why Playwright?** The site is a JavaScript single-page app (React/MUI). A simple HTTP GET returns only `<noscript>` content. Playwright launches a headless Chromium browser that executes the JS and renders the full page.

**How it works:**

1. Launches headless Chromium, navigates to the pro-calendar page
2. Waits for `networkidle` (all API calls complete) + 3 seconds for rendering
3. Extracts the full rendered HTML via `page.content()`
4. Finds today's date section by searching for `/calendar/YYYY-MM-DD` links in the HTML
5. Within that section, finds venue headers (`<span style="font-size: 125%;">`)
6. For each venue, extracts events using two regex patterns:
   - **Favorite events** (bolded, with artist links): `<strong>TIME</strong><strong><a href="/artist/...">NAME</a></strong>`
   - **Non-favorite events** (plain text): `<strong>TIME</strong>NAME<span>`
7. Deduplicates events (same time + name at same venue)
8. Returns a list of `Venue` objects, each containing `Event` objects

**Lesson name simplification:**

Dance lessons are simplified to save space in poll options:
- "Hill Country Two Step Lessons: Advanced" → `HC Lesson (adv)`
- "Double Or Nothing Two Step Lessons" → `DoN Lesson`
- "Dancin Austin Two Step Lesson" → `DA Lesson`
- "Native Texan Two Step - Intermediate" → `NT Lesson (int)`
- "Neon Rainbows Queer Line Dance Lessons" → `NR Lesson`
- "Free Dance Lessons" → `Free Lesson`

Levels: `(adv)` = advanced, `(int)` = intermediate, `(beg)` = beginner.

**Poll question:** A random witty title is chosen from a pool, with day-specific options mixed in (e.g. "Two-step Tuesday — where to?" on Tuesdays).

**Key constraints:**
- WhatsApp poll options max out at **100 characters** — options are truncated with `...` if needed
- WhatsApp polls support max **12 options**
- Event order is preserved from the website (not re-sorted)

### 2. `whatsapp_api.py` — Green API Client

**Purpose:** Send WhatsApp polls and messages via HTTP API. No browser automation needed.

**API used:** [Green API](https://green-api.com/) — a third-party WhatsApp API service.

**Why Green API?**
- Free tier supports 3 chats (enough for 1 group)
- Unlimited poll sends per month on free tier
- Simple REST API — no webhooks or complex OAuth
- Much cheaper than alternatives (Whapi.Cloud = $30/mo, official WhatsApp Business API = $1300/mo)

**Authentication:** URL-based — instance ID and token are embedded in the URL path:
```
https://api.greenapi.com/waInstance{ID}/{method}/{TOKEN}
```

**Methods used:**
- `sendPoll` — creates a WhatsApp poll with question + options
- `sendMessage` — sends a follow-up text message
- `getContacts` — lists groups to find the target group ID

**The poll payload:**
```json
{
  "chatId": "120363XXXXXXXXX@g.us",
  "message": "Boot scootin' roll call!",
  "options": [
    {"optionName": "Sagebrush: 7p HC Lesson, 9p Theo Lawrence"},
    {"optionName": "Whitehorse: 7p DA Lesson, 8p Missy Beth"}
  ],
  "multipleAnswers": true
}
```

### 3. `bot.py` — Orchestrator

**Purpose:** Ties scraping and sending together. Handles CLI flags and config.

**Modes:**
- `python bot.py` — scrape + send poll + send follow-up message
- `python bot.py --dry-run` — scrape only, print what would be sent
- `python bot.py --list-groups` — list all WhatsApp groups to find the group ID

**Flow:**
1. Load config (API credentials, group ID)
2. Call `scrape_today_events()` → list of venues
3. Call `format_poll_question(venues)` → question string + list of option strings
4. Call `client.send_poll(group_id, question, options)`
5. Call `client.send_message(group_id, follow_up_text)`
6. Log everything to `bot.log`

### 4. `config.json` — Configuration (not committed)

```json
{
  "green_api_instance_id": "YOUR_INSTANCE_ID",
  "green_api_token": "YOUR_API_TOKEN",
  "group_id": "YOUR_GROUP_ID@g.us",
  "calendar_url": "https://austin2step.com/where-to-dance/pro-calendar"
}
```

## Hosting & Scheduling

The bot runs on a cheap Linux VPS (Vultr, $5/mo) scheduled via cron:

```
45 16 * * * cd /root/bot && /root/botenv/bin/python bot.py >> /root/bot/bot.log 2>&1
```

- `45 16` = 16:45 UTC = 11:45 AM Central
- Runs daily, logs to `bot.log`
- Python virtual environment at `/root/botenv/` contains all dependencies

**Server dependencies:**
```bash
apt install python3-pip python3-venv
python3 -m venv /root/botenv
/root/botenv/bin/pip install playwright requests
/root/botenv/bin/playwright install chromium
/root/botenv/bin/playwright install-deps
```

## Adapting This Bot

To build a similar bot for a different website or messaging platform:

### Replace the scraper

1. Copy `scraper.py` as your starting point
2. Change the URL and parsing logic for your target website
3. Keep the `Venue` and `Event` dataclasses (or replace with your own data model)
4. Return your data from a `scrape_today_events()` function
5. Implement `format_poll_question()` to return `(question, options)`

If your target site is static HTML (not JS-rendered), you can replace Playwright with `requests` + `BeautifulSoup` for a simpler, faster scraper that doesn't need a browser.

### Replace the messaging layer

The `whatsapp_api.py` file is a thin wrapper around Green API. To use a different platform:

- **Telegram:** Use the [Bot API](https://core.telegram.org/bots/api) — native poll support, free, no phone needed
- **Discord:** Use [discord.py](https://discordpy.readthedocs.io/) — polls via reactions or slash commands
- **Slack:** Use the [Slack API](https://api.slack.com/) — no native polls, but you can use emoji reactions
- **SMS:** Use [Twilio](https://www.twilio.com/) — no polls, but can send formatted text

### Keep the orchestrator

`bot.py` barely changes — just swap the import and client class. The scrape → format → send flow stays the same.
