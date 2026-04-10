"""Scrape today's dance events from austin2step.com pro-calendar."""
import random
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from playwright.async_api import async_playwright


@dataclass
class Event:
    time: str
    name: str
    is_favorite: bool
    tip: bool = False


@dataclass
class Venue:
    name: str
    events: list[Event] = field(default_factory=list)

    @property
    def has_favorite(self) -> bool:
        return any(e.is_favorite for e in self.events)

    def format_poll_option_short(self) -> str:
        """Shorter format for poll option (WhatsApp has character limits)."""
        # Simplify lesson names, preserve website order
        simplified = []
        for e in self.events:
            t = _format_time(e.time)
            name = _simplify_lesson(e.name)
            simplified.append((t, name))

        # Merge consecutive lessons of the same brand into one entry
        merged = []
        seen_lessons = set()
        for t, n in simplified:
            if "Lesson" in n:
                if n not in seen_lessons:
                    # First occurrence of this lesson brand — keep it
                    seen_lessons.add(n)
                    merged.append((t, n))
                # Skip duplicates of same brand
            else:
                merged.append((t, n))

        parts = [f"{t} {n}" for t, n in merged]
        result = f"{self.name}: {', '.join(parts)}"

        # Truncate to fit WhatsApp's ~100 char poll option limit
        if len(result) > 100:
            result = result[:97] + "..."

        return result


def _simplify_lesson(name: str) -> str:
    """Simplify lesson event names."""
    lower = name.lower()
    if "lesson" not in lower and "native texan" not in lower:
        return name

    # Determine the lesson brand
    if "native texan" in lower:
        brand = "NT"
    elif "hill country" in lower:
        brand = "HC"
    elif "dancin austin" in lower or "dancin' austin" in lower:
        brand = "DA"
    elif "double or nothing" in lower:
        brand = "DoN"
    elif "neon rainbow" in lower:
        brand = "NR"
    elif "free" in lower:
        brand = "Free"
    else:
        brand = None

    # Determine the level
    if "advanced" in lower:
        level = " (adv)"
    elif "intermediate" in lower:
        level = " (int)"
    elif "beginner" in lower:
        level = " (beg)"
    else:
        level = ""

    if brand:
        return f"{brand} Lesson{level}"
    return f"Lesson{level}"


def _format_time(raw: str) -> str:
    """Convert raw time like '7' or '6:30' to '7p' or '6:30p'."""
    return raw + "p"


def _time_sort_key(time_str: str) -> int:
    """Convert time string to minutes for sorting.

    The calendar uses bare hours (no AM/PM). All events are PM or after midnight.
    The schedule runs roughly: 12pm noon → 1pm → ... → 11pm → 12am → 1am → 2am.

    We map to a continuous timeline starting at noon:
    - 12 (noon/matinee) → 12
    - 1-5 (afternoon) → 13-17
    - 6-11 (evening) → 18-23
    - 12 (midnight, after 11pm acts) → 24
    - 1-2 (after midnight) → 25-26

    Heuristic: if hour is 12, it could be noon or midnight. We check context
    by position — but since we can't here, we treat 12 as noon (most common
    for matinee shows). After-midnight 12am shows are rare and usually listed
    as the last event at a venue anyway.
    """
    parts = time_str.split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    # Convert to 24-hour continuous timeline starting at noon
    if hour == 12:
        hour = 12  # noon
    elif 1 <= hour <= 5:
        hour += 12  # 1pm=13, 2pm=14, ..., 5pm=17
    else:
        hour += 12  # 6pm=18, 7pm=19, ..., 11pm=23
    return hour * 60 + minute


async def scrape_today_events() -> list[Venue]:
    """Scrape today's events from all venues."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(
            "https://austin2step.com/where-to-dance/pro-calendar",
            wait_until="networkidle",
            timeout=30000,
        )
        await page.wait_for_timeout(3000)

        html = await page.content()
        await browser.close()

    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    # Find today's section using calendar date links
    today_pattern = f"/calendar/{today_str}"
    tomorrow = today + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    tomorrow_pattern = f"/calendar/{tomorrow_str}"

    start = html.find(today_pattern)
    end = html.find(tomorrow_pattern)

    if start < 0:
        print(f"Could not find today's date ({today_str}) on the calendar.")
        return []

    if end < 0:
        end = len(html)

    day_start = html.rfind('<div', max(0, start - 5000), start)
    section = html[day_start:end]

    # Parse venues and events
    venues = []
    venue_pattern = re.compile(
        r'<span style="font-size: 125%;">([^<]+)</span>'
    )
    venue_matches = list(venue_pattern.finditer(section))

    for i, match in enumerate(venue_matches):
        venue_name = match.group(1).strip().replace("&amp;", "&")
        v_start = match.end()
        v_end = venue_matches[i + 1].start() if i + 1 < len(venue_matches) else len(section)
        venue_section = section[v_start:v_end]

        venue = Venue(name=venue_name)

        # Favorite events (with artist link)
        fav_pattern = re.compile(
            r'<strong[^>]*>(\d+(?::\d+)?)</strong>'
            r'<strong><a[^>]*href="/artist/[^"]*">([^<]+)</a></strong>'
        )
        # Non-favorite events (plain text after time)
        nonfav_pattern = re.compile(
            r'<strong[^>]*>(\d+(?::\d+)?)</strong>'
            r'(?!<strong><a)([^<]{2,})<span'
        )

        # Collect all events with their HTML position so we can sort by appearance order
        all_matches = []

        for m in fav_pattern.finditer(venue_section):
            time_str = m.group(1)
            name = m.group(2).strip().replace("&amp;", "&")
            tip = "Tip" in venue_section[m.end():m.end() + 300]
            all_matches.append((m.start(), Event(time=time_str, name=name, is_favorite=True, tip=tip)))

        for m in nonfav_pattern.finditer(venue_section):
            # Skip if this position was already matched as a favorite
            if any(m.start() == pos for pos, _ in all_matches):
                continue
            time_str = m.group(1)
            name = m.group(2).strip().replace("&amp;", "&")
            if not name or name.startswith("<"):
                continue
            all_matches.append((m.start(), Event(time=time_str, name=name, is_favorite=False)))

        # Sort by HTML position (= website order)
        all_matches.sort(key=lambda x: x[0])
        for _, event in all_matches:
            venue.events.append(event)

        # Remove exact duplicates (same time + name), preserve website order
        seen = set()
        deduped = []
        for e in venue.events:
            key = (e.time, e.name.lower())
            if key not in seen:
                seen.add(key)
                deduped.append(e)
        venue.events = deduped

        if venue.events:
            venues.append(venue)

    return venues


WITTY_TITLES = [
    "Where are your boots headed tonight?",
    "Pick your poison (dance floor edition)",
    "Who's scootin' where tonight?",
    "Tonight's two-step destination?",
    "Where we honky-tonkin' tonight?",
    "Dust off them boots — where to?",
    "Which dance floor gets your boots tonight?",
    "Where's the two-step taking you?",
    "Saddle up — where we dancing?",
    "Boot scootin' roll call!",
    "Dance card check — where y'all headed?",
    "Tonight's shuffle spot?",
    "Where we wearing out the hardwood tonight?",
    "Alright dancers, what's the move?",
    "Which honky-tonk gets your heart tonight?",
    "The hardwood is calling — which floor?",
    "Spin cycle tonight — where we landing?",
    "Dance floor GPS — set your destination!",
]

DAY_TITLES = {
    "Monday": ["Monday night two-step — who's brave?", "Starting the week right — where we dancing?"],
    "Tuesday": ["Two-step Tuesday — where to?", "Taco Tuesday but make it two-step"],
    "Wednesday": ["Midweek mosey — pick your spot!", "Hump day honky-tonk — where to?"],
    "Thursday": ["Thursday throwdown — where we at?", "Almost Friday — where we warming up?"],
    "Friday": ["Friday night lights (dance floor edition)", "TGIF — which dance floor?"],
    "Saturday": ["Saturday night fever — where to?", "Big night — where we at?"],
    "Sunday": ["Sunday scoot — who's in?", "Sunday Funday — where we shufflin'?"],
}


def format_poll_question(venues: list[Venue]) -> tuple[str, list[str]]:
    """Format venues into a WhatsApp poll question and options."""
    today = datetime.now()
    day_name = today.strftime("%A")

    candidates = DAY_TITLES.get(day_name, []) + WITTY_TITLES
    question = random.choice(candidates)

    options = []
    for v in venues:
        options.append(v.format_poll_option_short())

    # WhatsApp polls max out at 12 options — split into multiple polls if needed
    option_chunks = [options[i:i+12] for i in range(0, len(options), 12)]

    return question, option_chunks


if __name__ == "__main__":
    import asyncio

    async def main():
        venues = await scrape_today_events()
        if not venues:
            print("No venues with dancer favorites found for today.")
            return

        question, options = format_poll_question(venues)
        print(f"Poll Question: {question}")
        print(f"\nPoll Options ({len(options)}):")
        for i, opt in enumerate(options, 1):
            print(f"  {i}) {opt}")

    asyncio.run(main())
