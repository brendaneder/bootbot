# Adapting This Bot for a Different Site

Forking BootBot for a different website (or different group/poll style)?
Here's the short version.

## What this bot does

1. **Scrapes** a website with a headless browser
2. **Builds** a WhatsApp poll from the scraped data
3. **Sends** the poll to a WhatsApp group via Green API
4. **Appends** an optional daily trivia fact

You'll change steps 1–2; steps 3–4 mostly stay the same.

## Setup (15 minutes)

```bash
# 1. Clone and install
git clone <your-fork-url>
cd <your-fork>
pip install -r requirements.txt
playwright install chromium

# 2. Set up Green API account (free tier works fine)
#    - Sign up at https://console.green-api.com/
#    - Create an instance, scan the QR with a spare phone's WhatsApp
#    - Copy instance_id and api_token

# 3. Configure
cp config.example.json config.json
# Edit config.json with your Green API credentials

# 4. Find your group ID
python bot.py --list-groups
# Copy the desired group_id into config.json

# 5. Test
python bot.py --dry-run
python bot.py
```

## Adapting the scraper to a different site

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

## Adapting the poll output

Each `Venue` becomes one poll option. Customize the formatting in
`Venue.format_poll_option_short()`:

- Has a 100-char hard limit (WhatsApp constraint)
- Can drop, abbreviate, or merge entries to fit
- Returns the final string for one option

The `format_poll_question(venues)` function picks a random title from
`WITTY_TITLES` / `DAY_TITLES`. Edit those constants for your tone.

WhatsApp polls cap at **12 options**; if you have more, the bot sends
multiple polls labeled "(part 1)", "(part 2)" automatically.

## Adapting the follow-up message

In `bot.py`, look for `default_signoff`. Change the text, emojis, and URL.

Or override per-deployment via `config.json`:

```json
{
    "follow_up_message": "Custom signoff goes here.\nSecond line."
}
```

## Trivia (optional)

The bot includes a daily trivia feature pulling from `facts.json`.

- **To disable**: set `start_date` in `facts.json` to a date far in the past
  (e.g. `"1900-01-01"`) — the bot will silently skip trivia.
- **To customize**: replace the contents of `facts.json` with your own list.
  Each entry is `{"category": "...", "text": "..."}`. Categories rotate
  per day-of-week. The bot picks fact #N where N is days since `start_date`.
- **To extend past the final fact**: add more entries; the "everything is
  known" sign-off only fires on the last fact.

## Deploying to a server (~$5/mo)

Any cheap Linux VPS works (Vultr, DigitalOcean, Hetzner, etc.). After
SSHing in:

```bash
sudo apt update && sudo apt install -y python3-pip python3-venv
python3 -m venv /root/botenv
/root/botenv/bin/pip install playwright requests
/root/botenv/bin/playwright install chromium
/root/botenv/bin/playwright install-deps

# Copy your bot files (from your PC):
# scp -r /local/path/* root@SERVER_IP:/root/bot/

# Schedule via cron (this example: 9:30 AM US Central, which is 14:30 UTC)
crontab -e
# Add:
30 14 * * * cd /root/bot && /root/botenv/bin/python bot.py >> /root/bot/bot.log 2>&1
```

## Keeping the linked WhatsApp account alive

The bot's WhatsApp number must stay "active" — the linked phone needs to
check in within ~14 days or WhatsApp disconnects the linked device. Best
practices:

- Use a spare phone or run WhatsApp as a second account on your daily phone
- Keep the device powered on with WiFi
- If it disconnects, re-scan the QR in the Green API dashboard

## Files at a glance

| File | What it does |
|------|--------------|
| `bot.py` | Entry point — orchestrates scrape → poll → send |
| `scraper.py` | Site-specific scraping logic. **Most edits go here.** |
| `whatsapp_api.py` | Green API client (poll, message, list groups) |
| `facts.py` | Trivia helper — picks today's fact |
| `facts.json` | Trivia data (or empty/disabled) |
| `config.json` | Your credentials and group ID (gitignored) |
| `config.example.json` | Template — copy to `config.json` |

That's it. See [ARCHITECTURE.md](ARCHITECTURE.md) if you need deeper details.
