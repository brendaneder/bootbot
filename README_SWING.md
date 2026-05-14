# Swing Mode

By default, BootBot sends a daily **poll** of today's 2-step events. With the `--swing` flag, it sends a **formatted message** listing swing dancing events instead.

## Key Differences

| Aspect | Default (Poll) | Swing Mode |
|--------|----------------|------------|
| **Data source** | Scrapes austin2step.com | Google Calendar API |
| **Output** | WhatsApp poll (vote on venue) | Formatted message (informational) |
| **Trivia** | Included | Not included |

## Setup

1. **Create a public Google Calendar** with swing events (or use an existing one).
2. **Get your Google Calendar API key:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Calendar API
   - Create an API key (restrict to Calendar API)
3. **Add to `config.json`:**
   ```json
   {
       "swing_google_calendar_id": "your-calendar-id@group.calendar.google.com",
       "swing_google_calendar_api_key": "YOUR_API_KEY"
   }
   ```
   (The calendar ID is visible in Calendar settings → Integrate calendar → Calendar ID)

## Running

```bash
python bot.py --swing --dry-run        # Preview what would be sent
python bot.py --swing                  # Send the swing message
```

## Event Filtering

Swing mode filters events for bands in the `SWING_BANDS` list in `swing.py`. Edit this list to match your calendar's band names.
