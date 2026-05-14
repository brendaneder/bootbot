"""Fetch upcoming swing events from a public Google Calendar."""
import json
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests

CONFIG_PATH = Path(__file__).parent / "config.json"

LOG_PATH = Path(__file__).parent / "swing.log"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

SWING_BANDS = [
    'Little Elmore Reed Blues Band',
    'Heybale',
    'Bob Wills Night W/the Super Swing Revue',
    'Linda Gail Lewis',
]


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


async def scrape_swing_events() -> list[dict]:
    """Fetch events for the next 7 days using Google Calendar API."""
    config = load_config()
    calendar_id = config.get("swing_google_calendar_id", "")
    api_token = config.get("swing_google_calendar_api_key", "")

    if not calendar_id:
        logger.error("No swing_google_calendar_id found in config.json")
        return []

    if not api_token:
        logger.error("No swing_google_calendar_api_key found in config.json")
        return []

    now = datetime.now(ZoneInfo("America/Chicago"))
    time_min = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    time_max = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

    encoded_calendar_id = quote(calendar_id)
    endpoint = f"https://www.googleapis.com/calendar/v3/calendars/{encoded_calendar_id}/events"
    params = {
        "key": api_token,
        "singleEvents": "true",
        "orderBy": "startTime",
        "timeMin": time_min,
        "timeMax": time_max,
    }

    try:
        response = requests.get(endpoint, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, json.JSONDecodeError) as exc:
        logger.error("Failed to fetch swing calendar events: %s", exc)
        return []
    items = payload.get("items", [])
    if not isinstance(items, list):
        logger.error("Unexpected Google Calendar response shape: missing 'items' list")
        return []

    events: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        start = item.get("start", {})
        end = item.get("end", {})

        events.append(
            {
                "id": item.get("id", ""),
                "summary": item.get("summary", "(No title)"),
                "description": item.get("description", ""),
                "location": item.get("location", ""),
                "start": start.get("dateTime") or start.get("date", ""),
                "end": end.get("dateTime") or end.get("date", ""),
                "html_link": item.get("htmlLink", ""),
            }
        )

    return events


def parse_swing_event(venue: dict) -> str:
    # swing event fields
    raw_start = venue.get("start", "") or venue.get("time", "")
    summary = venue.get("summary", "") or venue.get("name", "")
    location = venue.get("location", "") or venue.get("location", "")
    try:
        if "T" in raw_start:
            dt = datetime.fromisoformat(raw_start)
            label = dt.strftime("%-I:%M")
        else:
            dt = datetime.fromisoformat(raw_start)
            label = dt.strftime("%-I:%M")
    except ValueError:
        label = raw_start
    return f"*{label}*\n{summary} @ {location}"


def build_swing_message(twostep_venues: list[dict], swing_events: list[dict]) -> str:
    lines = ["💃🕺 *Swing dancing today in Austin!*\n"]
    for venue in twostep_venues:
        for venue_event in venue.events:
            if venue_event.name in SWING_BANDS:
                swing_events += [venue_event]

    for venue in swing_events:
        swing_event = parse_swing_event(venue)
        if swing_event:
            lines.append(swing_event)

    lines.append("\nFeedback? Reply to this message or DM Ari Frankel (chat admin)")
    message = "\n\n".join(lines)
    return message
