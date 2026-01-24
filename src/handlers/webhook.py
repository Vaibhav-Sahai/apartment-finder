"""Handle incoming WhatsApp webhook messages."""

import logging
from typing import Callable, Awaitable

from src.messaging.formatter import format_site_list

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Handle incoming WhatsApp messages and route to commands."""

    HELP_TEXT = """*Available Commands:*

- *scrape* - Scrape all configured sites
- *scrape <site>* - Scrape a specific site
- *status* - Get bot status
- *list* - List configured sites
- *help* - Show this message"""

    def __init__(
        self,
        site_names: list[str],
        on_scrape_all: Callable[[], Awaitable[str]],
        on_scrape_site: Callable[[str], Awaitable[str]],
        on_status: Callable[[], Awaitable[str]],
    ):
        """Initialize the webhook handler.

        Args:
            site_names: List of configured site names
            on_scrape_all: Async callback to scrape all sites
            on_scrape_site: Async callback to scrape a specific site
            on_status: Async callback to get status
        """
        self.site_names = site_names
        self._on_scrape_all = on_scrape_all
        self._on_scrape_site = on_scrape_site
        self._on_status = on_status

    async def handle_message(self, message_body: str) -> str:
        """Parse and handle an incoming message.

        Args:
            message_body: The text content of the message

        Returns:
            Response message to send back
        """
        text = message_body.strip().lower()
        logger.info(f"Handling command: {text}")

        if text == "help":
            return self.HELP_TEXT

        if text == "list":
            return format_site_list(self.site_names)

        if text == "status":
            return await self._on_status()

        if text == "scrape":
            return await self._on_scrape_all()

        if text.startswith("scrape "):
            site_name = message_body.strip()[7:].strip()  # Preserve original case
            return await self._on_scrape_site(site_name)

        # Unknown command
        return f"Unknown command: '{text}'\n\n{self.HELP_TEXT}"

    @staticmethod
    def extract_message_from_webhook(payload: dict) -> tuple[str, str] | None:
        """Extract message text and sender from webhook payload.

        Args:
            payload: The webhook payload from Meta

        Returns:
            Tuple of (sender_phone, message_text) or None if not a message
        """
        try:
            entry = payload.get("entry", [])
            if not entry:
                return None

            changes = entry[0].get("changes", [])
            if not changes:
                return None

            value = changes[0].get("value", {})
            messages = value.get("messages", [])
            if not messages:
                return None

            message = messages[0]
            if message.get("type") != "text":
                return None

            sender = message.get("from")
            text = message.get("text", {}).get("body", "")

            if sender and text:
                return (sender, text)

        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing webhook payload: {e}")

        return None
