# BootBot — Austin Two-Step Dance Poll Bot

A bot that scrapes tonight's dance events from [austin2step.com](https://austin2step.com/where-to-dance/pro-calendar) and sends a WhatsApp poll to a group so dancers can vote on where they're headed.

## What It Does

Every day at a scheduled time, BootBot:

1. **Scrapes** the austin2step.com pro-calendar using a headless browser (Playwright)
2. **Parses** all venues and events for today, simplifying lesson names and deduplicating
3. **Formats** each venue as a poll option (e.g. `Sagebrush: 7p HC Lesson, 9p Theo Lawrence`)
4. **Sends** a WhatsApp poll to your group via the [Green API](https://green-api.com/)
5. **Follows up** with a short message crediting BootBot

## Example Output

```
Poll: Boot scootin' roll call!

1) ABGB: 7p Warren Hood
2) Broken Spoke: 9p Bakersfield Tx
3) Continental Club: 2:30p Marshall Hood, 6:30p Heybale, 9:30p Willie Pipkin & Friends
4) Sagebrush: 7p HC Lesson (adv), 8p HC Lesson (int), 9p Theo Lawrence
5) Whitehorse: 7p DA Lesson, 8p Missy Beth & The Morning Afters, 10p Sentimental Family Band
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for a detailed breakdown of how each component works.

## Quick Start

### Prerequisites

- Python 3.10+
- A WhatsApp account on a spare phone number (prepaid SIM works)
- A [Green API](https://console.green-api.com/) account (free tier works)

### 1. Install dependencies

```bash
pip install playwright requests
playwright install chromium
playwright install-deps  # Linux only
```

### 2. Configure

```bash
cp config.example.json config.json
```

Edit `config.json`:
- `green_api_instance_id` — from your Green API dashboard
- `green_api_token` — from your Green API dashboard
- `group_id` — run `python bot.py --list-groups` to find it

### 3. Link WhatsApp

In the Green API dashboard, scan the QR code with your spare phone's WhatsApp (Settings > Linked Devices > Link a Device).

### 4. Test

```bash
# Preview what the poll will look like
python bot.py --dry-run

# Send for real
python bot.py
```

### 5. Schedule (Linux server)

```bash
# Edit crontab
crontab -e

# Add this line (11:45 AM Central = 16:45 UTC)
45 16 * * * cd /path/to/bot && /path/to/python bot.py >> bot.log 2>&1
```

## Hosting

This bot runs on a **$5/mo Vultr VPS** (or any cheap Linux server). It only needs to run for ~30 seconds per day, so the cheapest tier is more than enough.

### Server setup (Debian/Ubuntu)

```bash
apt update && apt install -y python3-pip python3-venv
python3 -m venv /root/botenv
/root/botenv/bin/pip install playwright requests
/root/botenv/bin/playwright install chromium
/root/botenv/bin/playwright install-deps
```

Upload bot files and set up cron as described above.

## Adapting for Other Use Cases

This bot is specifically built for Austin's two-step dance scene, but the pattern is reusable:

1. **Replace `scraper.py`** with your own scraper for any website
2. **Keep `whatsapp_api.py`** as-is — it's a generic Green API client
3. **Modify `bot.py`** to change the poll question, follow-up message, or scheduling logic

See [ARCHITECTURE.md](ARCHITECTURE.md) for details on each component.

## Costs

| Item | Cost |
|------|------|
| Green API (free tier) | $0/mo |
| VPS (Vultr cheapest) | $5/mo |
| Digital SIM | $8/mo |
| **Total** | **$13/mo** |

## Files

| File | Purpose |
|------|---------|
| `bot.py` | Main entry point — orchestrates scraping and sending |
| `scraper.py` | Scrapes austin2step.com, parses events, formats poll options |
| `whatsapp_api.py` | Green API client — sends polls and messages |
| `config.json` | API credentials and group ID (not committed, see `config.example.json`) |
| `requirements.txt` | Python dependencies |
