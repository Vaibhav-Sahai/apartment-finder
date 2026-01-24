"""WhatsApp Business API client using Meta Graph API."""

import httpx
import logging

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """Client for sending messages via Meta WhatsApp Business API."""

    BASE_URL = "https://graph.facebook.com/v21.0"

    def __init__(self, phone_number_id: str, access_token: str):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=f"{self.BASE_URL}/{self.phone_number_id}",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def send_message(self, to: str, message: str) -> dict:
        """Send a text message to a phone number.

        Args:
            to: Phone number in international format (e.g., '14155238886')
            message: Text message to send

        Returns:
            API response dict with message ID
        """
        client = await self._get_client()

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": message},
        }

        response = await client.post("/messages", json=payload)
        response.raise_for_status()
        result = response.json()
        logger.info(f"Sent message to {to}: {result}")
        return result

    async def send_template(
        self,
        to: str,
        template_name: str,
        language_code: str = "en_US",
        components: list[dict] | None = None,
    ) -> dict:
        """Send a template message.

        Template messages are required for initiating conversations.

        Args:
            to: Phone number in international format
            template_name: Name of the approved message template
            language_code: Language code for the template
            components: Optional list of template components (header, body params)

        Returns:
            API response dict with message ID
        """
        client = await self._get_client()

        template = {
            "name": template_name,
            "language": {"code": language_code},
        }
        if components:
            template["components"] = components

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": template,
        }

        response = await client.post("/messages", json=payload)
        response.raise_for_status()
        result = response.json()
        logger.info(f"Sent template '{template_name}' to {to}: {result}")
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
