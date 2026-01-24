"""Handle incoming Telegram webhook messages."""

import logging
from typing import Callable, Awaitable

from src.messaging.formatter import format_site_list

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Handle incoming Telegram messages and route to commands."""

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
        """Extract message text and chat ID from Telegram webhook payload.

        Args:
            payload: The webhook payload from Telegram

        Returns:
            Tuple of (chat_id, message_text) or None if not a message
        """
        try:
            message = payload.get("message")
            if not message:
                return None

            chat = message.get("chat", {})
            chat_id = chat.get("id")
            text = message.get("text", "")

            if chat_id and text:
                return (str(chat_id), text)

        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing webhook payload: {e}")

        return None
