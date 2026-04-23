"""TwoStep Trivia — load facts.json and pick today's fact."""
import json
from datetime import date
from pathlib import Path

FACTS_PATH = Path(__file__).parent / "facts.json"


def get_fact(today: date | None = None) -> dict | None:
    """
    Returns today's fact as {number, category, text, is_final, name}, or None if:
      - today is before the start_date
      - we've run past the last fact
    """
    if today is None:
        today = date.today()

    data = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    start = date.fromisoformat(data["start_date"])
    facts = data["facts"]
    name = data.get("name", "TwoStep Trivia")

    days_elapsed = (today - start).days
    if days_elapsed < 0:
        return None
    number = days_elapsed + 1
    if number > len(facts):
        return None

    entry = facts[number - 1]
    return {
        "number": number,
        "category": entry["category"],
        "text": entry["text"],
        "is_final": number == len(facts),
        "name": name,
    }


def format_fact(fact: dict) -> str:
    """Render a fact as the trivia portion of a WhatsApp message."""
    line = f"{fact['name']} #{fact['number']} ({fact['category']}): {fact['text']}"
    if fact["is_final"]:
        line += (
            "\n\n\U0001f393 And that's it — the final fact stored! "
            "Everything there is to know about Texas two-step has now been shared. "
            "No more facts to learn; you are officially enlightened. "
            "Hang up your lesson boots (but never your dancing boots)."
        )
    return line


if __name__ == "__main__":
    # Quick preview — show today's fact, or a specific date
    import sys
    if len(sys.argv) > 1:
        d = date.fromisoformat(sys.argv[1])
    else:
        d = date.today()
    fact = get_fact(d)
    if fact is None:
        data = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
        start = date.fromisoformat(data["start_date"])
        days_elapsed = (d - start).days
        if days_elapsed < 0:
            print(f"No fact for {d} — start date is {start} ({-days_elapsed} days away).")
        else:
            print(f"No fact for {d} — ran past the final fact at day {len(data['facts'])}.")
    else:
        print(f"Date: {d}")
        print(format_fact(fact))
