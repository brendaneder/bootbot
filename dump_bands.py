"""One-time script: scrape all band names from the full pro-calendar and save to a file."""
import asyncio
import re
from collections import Counter
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Loading calendar...")
        await page.goto(
            "https://austin2step.com/where-to-dance/pro-calendar",
            wait_until="networkidle",
            timeout=30000,
        )
        await page.wait_for_timeout(3000)
        html = await page.content()
        await browser.close()

    # Find all band names (favorites, with artist links)
    fav_pattern = re.compile(
        r'<strong[^>]*>\d+(?::\d+)?</strong>'
        r'<strong><a[^>]*href="/artist/[^"]*">([^<]+)</a></strong>'
    )
    # Non-favorite events (plain text)
    nonfav_pattern = re.compile(
        r'<strong[^>]*>\d+(?::\d+)?</strong>'
        r'(?!<strong><a)([^<]{2,})<span'
    )

    all_names = []
    for m in fav_pattern.finditer(html):
        name = m.group(1).strip().replace("&amp;", "&")
        all_names.append(name)
    for m in nonfav_pattern.finditer(html):
        name = m.group(1).strip().replace("&amp;", "&")
        if name and not name.startswith("<"):
            all_names.append(name)

    # Count occurrences, keep unique
    counts = Counter(all_names)
    unique_names = sorted(counts.keys(), key=lambda x: (-counts[x], x))

    print(f"Found {len(all_names)} total events, {len(unique_names)} unique names")

    with open("band_names.txt", "w", encoding="utf-8") as f:
        f.write(f"# {len(unique_names)} unique band/event names from austin2step.com\n")
        f.write(f"# Format: [count] name\n\n")
        for name in unique_names:
            f.write(f"[{counts[name]}] {name}\n")

    print("Saved to band_names.txt")

    # Also print the longest names (the ones most likely to need truncation)
    print("\nLongest 20 names:")
    longest = sorted(unique_names, key=len, reverse=True)[:20]
    for name in longest:
        print(f"  ({len(name)}) {name}")


asyncio.run(main())
