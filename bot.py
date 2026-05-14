"""
Austin 2-Step Dance Bot v2 — Headless, API-based
Scrapes today's dance events and sends a WhatsApp poll via Green API.

Usage:
    python bot.py                       # Scrape + send poll
    python bot.py --dry-run             # Scrape only, print what would be sent
    python bot.py --list-groups         # List all groups (to find your group ID)
    python bot.py --preview-fact [date] # Preview today's (or a specific date's) trivia fact
"""
import asyncio
import argparse
import json
import logging
from datetime import date
from pathlib import Path

import facts
from scraper import scrape_today_events, format_poll_question
from swing import scrape_swing_events, build_swing_message
from whatsapp_api import GreenApiClient

CONFIG_PATH = Path(__file__).parent / "config.json"
LOG_PATH = Path(__file__).parent / "bot.log"

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Austin 2-Step Dance Bot: scrape events and send WhatsApp updates."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape only and print what would be sent.",
    )
    parser.add_argument(
        "--list-groups",
        action="store_true",
        help="List available groups to find your group ID.",
    )
    parser.add_argument(
        "--swing",
        action="store_true",
        help="Send swing weekly roundup instead of the daily poll.",
    )
    parser.add_argument(
        "--preview-fact-date",
        nargs="?",
        const=date.today().isoformat(),
        metavar="DATE",
        type=date.fromisoformat,
        help="Preview trivia fact for a specific ISO date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--preview-fact",
        action="store_true",
        help="Preview trivia fact for today. Provide --preview-fact-date to specify date for fact.",
    )
    return parser.parse_args()


def load_and_validate_config() -> dict:
    with open(CONFIG_PATH) as f:
        config = json.load(f)
        instance_id = config.get("green_api_instance_id", "")
        api_token = config.get("green_api_token", "")
        group_id = config.get("group_id", "")

        if not instance_id or not api_token:
            logger.error("Green API credentials not set in config.json.")
            logger.error("  Sign up at https://console.green-api.com/")
            logger.error("  Create an instance and link your WhatsApp number")
            logger.error("  Copy instance_id and api_token to config.json")
            raise Exception("Missing Green API credentials")

        if not group_id:
            logger.error("Group ID not set in config.json.")
            logger.error("  Run: python bot.py --list-groups")
            raise Exception("Missing group_id")

        return config


async def gather_events(swing_mode: bool) -> tuple[list[dict], list[dict]]:
    logger.info("Scraping today's 2step events...")
    twostep_venues = await scrape_today_events()
    swing_events = []
    if swing_mode:
        swing_events = await scrape_swing_events()
    return twostep_venues, swing_events


async def main(args: argparse.Namespace):
    dry_run = args.dry_run

    if args.preview_fact:
        return facts.preview_fact(args.preview_fact_date)

    config = load_and_validate_config()
    if not config and not dry_run:
        return

    client = GreenApiClient(config["green_api_instance_id"], config["green_api_token"])
    group_id = config["swing_group_id"] if args.swing else config["group_id"]

    if args.list_groups:
        return client.list_groups()

    twostep_venues, swing_events = await gather_events(args.swing)

    if args.swing:
        message = build_swing_message(twostep_venues, swing_events)

        if dry_run:
            logging.info("\n[DRY RUN] Swing message:\n")
            logging.info(message)
        else:
            client.send_message(group_id, message)
            logger.info("Swing weekly roundup sent.")
    else:
        question, option_chunks = format_poll_question(twostep_venues)

        for chunk_idx, options in enumerate(option_chunks):
            label = f" (part {chunk_idx + 1})" if len(option_chunks) > 1 else ""
            logger.info(f"Poll{label}: {question}")
            for i, opt in enumerate(options, 1 + chunk_idx * 12):
                logger.info(f"  {i}) {opt}")

        # Send poll(s)
        for chunk_idx, options in enumerate(option_chunks):
            label = f" (part {chunk_idx + 1})" if len(option_chunks) > 1 else ""
            poll_question = f"{question}{label}"
            logger.info(f"Sending poll{label} to {group_id}...")
            if dry_run:
                logging.info("\n[DRY RUN] Poll:\n")
                logging.info(poll_question)
                logging.info(options)
            else:
                result = client.send_poll(group_id, poll_question, options)

                if "idMessage" not in result:
                    logger.error(f"Poll{label} failed: {result}")
                    return

        # Build the follow-up message: trivia fact + BootBot sign-off
        default_signoff = (
            "\U0001f97e\U0001f916 This poll and (hopefully correct) trivia was autogenerated by BootBot.\n"
            "See any issues? Comment below!\n"
            "Full calendar: https://austin2step.com/"
        )
        signoff = config.get("follow_up_message", default_signoff)

        fact = facts.get_fact()
        parts = []
        if fact is not None:
            parts.append(facts.format_fact(fact))
        parts.append(signoff)
        follow_up = "\n\n".join(parts)
        if dry_run:
            logging.info("\n[DRY RUN] Follow-up message:\n")
            logging.info(follow_up)
        else:
            client.send_message(group_id, follow_up)

    logger.info("Done!")


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
