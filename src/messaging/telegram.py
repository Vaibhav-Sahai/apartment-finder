"""Telegram Bot API client."""

import httpx
import logging

logger = logging.getLogger(__name__)

TELEGRAM_MAX_LENGTH = 4096


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

    def _split_message(self, text: str, max_length: int = TELEGRAM_MAX_LENGTH) -> list[str]:
        """Split long messages at newline boundaries.

        Args:
            text: The text to split
            max_length: Maximum length per chunk

        Returns:
            List of message chunks
        """
        if len(text) <= max_length:
            return [text]

        chunks = []
        current = ""
        for line in text.split("\n"):
            if len(current) + len(line) + 1 > max_length:
                if current:
                    chunks.append(current.rstrip())
                current = line + "\n"
            else:
                current += line + "\n"
        if current:
            chunks.append(current.rstrip())
        return chunks

    async def send_message(self, chat_id: str, text: str) -> dict:
        """Send a text message to a chat.

        Args:
            chat_id: Telegram chat ID
            text: Text message to send (supports Markdown)

        Returns:
            API response dict with message info
        """
        if not text or not text.strip():
            logger.warning("Attempted to send empty message")
            return {"ok": False, "error": "empty message"}

        client = await self._get_client()
        chunks = self._split_message(text)
        result = {}

        for chunk in chunks:
            payload = {
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "HTML",
            }

            logger.info(f"Sending message to Telegram:\n{chunk}")
            response = await client.post("/sendMessage", json=payload)
            if not response.is_success:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
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
