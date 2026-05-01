# BootBot — Austin Two-Step Dance Poll Bot

A bot that scrapes tonight's dance events from [austin2step.com](https://austin2step.com/where-to-dance/pro-calendar) and sends a WhatsApp poll to a group so dancers can vote on where they're headed.

## What It Does

Every day at a scheduled time, BootBot:

1. **Scrapes** a website with a headless browser (Playwright)
2. **Builds** a WhatsApp poll from the scraped data
3. **Sends** the poll to a WhatsApp group via the [Green API](https://green-api.com/)
4. **Appends** a daily trivia fact + short sign-off

If you fork this repo for a different site, you'll mostly only edit step 1.

## Example Output

```
Poll: Boot scootin' roll call!

1) ABGB: 7p Warren Hood
2) Broken Spoke: 9p Bakersfield Tx
3) Continental Club: 2:30p Marshall Hood, 6:30p Heybale, 9:30p Willie Pipkin & Friends
4) Sagebrush: 7p HC Lesson (adv), 8p HC Lesson (int), 9p Theo Lawrence
5) Whitehorse: 7p DA Lesson, 8p Missy Beth & The Morning Afters, 10p Sentimental Family Band
```

## Quick Start (15 minutes)

```bash
# 1. Clone and install
git clone <your-fork-url>
cd <your-fork>
pip install playwright requests
playwright install chromium
playwright install-deps  # Linux only

# 2. Set up Green API (free tier works fine)
#    - Sign up at https://console.green-api.com/
#    - Create an instance, scan the QR with a spare phone's WhatsApp
#      (Settings > Linked Devices > Link a Device)
#    - Copy the instance_id and api_token

# 3. Configure
cp config.example.json config.json
# Edit config.json with your Green API credentials

# 4. Find your WhatsApp group ID
python bot.py --list-groups
# Copy the desired group_id into config.json

# 5. Test
python bot.py --dry-run
python bot.py
```

## Adapting for a Different Site

### Adapt the scraper

Edit **`scraper.py`**. The main function is `scrape_today_events()`. It needs to:

1. Load the page (Playwright handles JS-rendered sites)
2. Parse out the data you want
3. Return a `list[Venue]` (rename to whatever your domain calls "groupings")

```python
async def scrape_today_events() -> list[Venue]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://your-site.example/page")
        await page.wait_for_load_state("networkidle")
        html = await page.content()
        await browser.close()

    # Parse `html` however you like (regex, BeautifulSoup, or
    # parse Playwright DOM directly without grabbing full HTML).
    # Build and return your list of Venue (or whatever domain object).
```

If the site is **not** JS-rendered, you can drop Playwright entirely and use
`requests` + `BeautifulSoup` — much faster.

### Adapt the poll output

Each `Venue` becomes one poll option. Customize the formatting in
`Venue.format_poll_option_short()`:

- 100-character hard limit per option (WhatsApp constraint)
- Can drop, abbreviate, or merge entries to fit
- Returns the final string for one option

`format_poll_question(venues)` picks a random title from `WITTY_TITLES` /
`DAY_TITLES` constants — edit those for your tone.

WhatsApp polls cap at **12 options**; if you have more, the bot sends
multiple polls labeled "(part 1)", "(part 2)" automatically.

### Adapt the follow-up message

In `bot.py`, edit `default_signoff` directly — or override per-deployment
via `config.json`:

```json
{
    "follow_up_message": "Custom signoff goes here.\nSecond line."
}
```

### Trivia (optional)

The bot includes a daily trivia feature pulling from `facts.json`:

- **Disable**: set `start_date` in `facts.json` to a date far in the past
  (e.g. `"1900-01-01"`) — the bot will silently skip trivia.
- **Customize**: replace the contents of `facts.json` with your own list.
  Each entry is `{"category": "...", "text": "..."}`. Categories rotate
  per day-of-week. The bot picks fact #N where N = days since `start_date`.
- **Extend past the final fact**: add more entries; the "everything is
  known" sign-off only fires on the last fact.

## Deploying to a Server (~$5/mo)

Any cheap Linux VPS works (Vultr, DigitalOcean, Hetzner, etc.).

> **Tip:** Vultr currently offers $250 in signup credits for new accounts.
> At the cheapest $5/mo plan that's effectively ~4 years of free hosting.

After SSHing in:

```bash
sudo apt update && sudo apt install -y python3-pip python3-venv
python3 -m venv /root/botenv
/root/botenv/bin/pip install playwright requests
/root/botenv/bin/playwright install chromium
/root/botenv/bin/playwright install-deps

# Copy your bot files (from your PC):
# scp -r /local/path/* root@SERVER_IP:/root/bot/

# Schedule via cron (this example: 9:30 AM US Central = 14:30 UTC)
crontab -e
# Add:
30 14 * * * cd /root/bot && /root/botenv/bin/python bot.py >> /root/bot/bot.log 2>&1
```

## Keeping the Linked WhatsApp Account Alive

The bot's WhatsApp number must stay "active" — the linked phone needs to
check in within ~14 days or WhatsApp disconnects the linked device. Best
practices:

- Use a spare phone or run WhatsApp as a second account on your daily phone
- Keep the device powered on with WiFi
- If it disconnects, re-scan the QR in the Green API dashboard

## Costs

| Item | Cost |
|------|------|
| Green API (free tier) | $0/mo |
| VPS (Vultr cheapest) | $5/mo (or free with $250 signup credit) |
| Digital SIM | $8/mo |
| **Total** | **~$13/mo** (or ~$8/mo while Vultr credit lasts) |

## Files

| File | What it does |
|------|--------------|
| `bot.py` | Entry point — orchestrates scrape → poll → send |
| `scraper.py` | Site-specific scraping logic. **Most edits go here.** |
| `whatsapp_api.py` | Green API client (poll, message, list groups) |
| `facts.py` | Trivia helper — picks today's fact |
| `facts.json` | Trivia data (disable via `start_date`) |
| `config.json` | Your credentials and group ID (gitignored) |
| `config.example.json` | Template — copy to `config.json` |

For a deeper dive into the architecture, see [ARCHITECTURE.md](ARCHITECTURE.md).
