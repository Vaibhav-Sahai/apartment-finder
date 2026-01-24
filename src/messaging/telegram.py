"""Telegram Bot API client."""

import httpx
import logging

logger = logging.getLogger(__name__)


class TelegramClient:
    """Client for sending messages via Telegram Bot API."""

    BASE_URL = "https://api.telegram.org"

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=f"{self.BASE_URL}/bot{self.bot_token}",
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )
        return self._client

    async def send_message(self, chat_id: str, text: str) -> dict:
        """Send a text message to a chat.

        Args:
            chat_id: Telegram chat ID
            text: Text message to send (supports Markdown)

        Returns:
            API response dict with message info
        """
        client = await self._get_client()

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }

        response = await client.post("/sendMessage", json=payload)
        response.raise_for_status()
        result = response.json()
        logger.info(f"Sent message to {chat_id}: {result.get('ok')}")
        return result

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
