"""Send WhatsApp polls and messages via Green API."""
import logging
import requests

logger = logging.getLogger(__name__)


class GreenApiClient:
    """Client for Green API (greenapi.com)."""

    BASE_URL = "https://api.greenapi.com"

    def __init__(self, instance_id: str, api_token: str):
        self.instance_id = instance_id
        self.api_token = api_token

    def _url(self, method: str) -> str:
        return f"{self.BASE_URL}/waInstance{self.instance_id}/{method}/{self.api_token}"

    def send_poll(self, group_id: str, question: str, options: list[str], multi_select: bool = True) -> dict:
        """
        Send a poll to a WhatsApp group.

        Args:
            group_id: WhatsApp group ID (e.g. "120363XXXXXXXXX@g.us")
            question: The poll question text (max 255 chars).
            options: List of poll option strings (max 12, each max 100 chars).
            multi_select: Allow multiple selections.

        Returns:
            API response dict.
        """
        if len(options) > 12:
            logger.warning(f"Truncating poll options from {len(options)} to 12")
            options = options[:12]

        # Truncate long options
        options = [opt[:97] + "..." if len(opt) > 100 else opt for opt in options]

        # Truncate question
        if len(question) > 255:
            question = question[:252] + "..."

        payload = {
            "chatId": group_id,
            "message": question,
            "options": [{"optionName": opt} for opt in options],
            "multipleAnswers": multi_select,
        }

        logger.info(f"Sending poll: {question}")
        logger.info(f"Options: {options}")

        resp = requests.post(
            self._url("sendPoll"),
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        result = resp.json()
        if "idMessage" in result:
            logger.info(f"Poll sent successfully: {result['idMessage']}")
        else:
            logger.error(f"Failed to send poll: {resp.status_code} — {result}")

        return result

    def send_message(self, group_id: str, text: str) -> dict:
        """
        Send a text message to a WhatsApp group.

        Args:
            group_id: WhatsApp group ID.
            text: Message text.

        Returns:
            API response dict.
        """
        payload = {
            "chatId": group_id,
            "message": text,
        }

        logger.info(f"Sending message to {group_id}")

        resp = requests.post(
            self._url("sendMessage"),
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        result = resp.json()
        if "idMessage" in result:
            logger.info("Message sent successfully")
        else:
            logger.error(f"Failed to send message: {resp.status_code} — {result}")

        return result

    def list_groups(self) -> list[dict]:
        """List all groups the bot is a member of."""
        resp = requests.get(
            self._url("getContacts") + "?group=true",
            timeout=30,
        )

        if resp.status_code == 200:
            contacts = resp.json()
            groups = [c for c in contacts if c.get("type") == "group" or c.get("id", "").endswith("@g.us")]
            return groups
        else:
            logger.error(f"Failed to list groups: {resp.status_code} — {resp.text}")
            return []


if __name__ == "__main__":
    import json
    from pathlib import Path

    config = json.loads((Path(__file__).parent / "config.json").read_text())
    client = GreenApiClient(config["green_api_instance_id"], config["green_api_token"])

    print("Fetching groups...")
    groups = client.list_groups()
    for g in groups:
        name = g.get("name", g.get("contactName", "Unknown"))
        gid = g.get("id", "Unknown")
        print(f"  {name} — {gid}")
