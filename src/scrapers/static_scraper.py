"""Scraper for static HTML websites using httpx + BeautifulSoup."""

import httpx
from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper
from src.config.settings import SiteConfig
from src.models.listing import Listing


class StaticScraper(BaseScraper):
    """Scraper for static HTML sites that don't require JavaScript."""

    def __init__(self, site_config: SiteConfig):
        super().__init__(site_config)
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
                follow_redirects=True,
                timeout=30.0,
            )
        return self._client

    async def scrape(self) -> list[Listing]:
        """Scrape the static HTML site and return listings."""
        client = await self._get_client()
        response = await client.get(self.config.url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        listings = []

        # Get the container selector for individual listings
        container_selector = self.config.selectors.get("listing_container", ".listing")
        containers = soup.select(container_selector)

        for container in containers:
            listing = self._parse_listing(container)
            if listing:
                listings.append(listing)

        return listings

    def _parse_listing(self, container: BeautifulSoup) -> Listing | None:
        """Parse a single listing from its container element."""
        selectors = self.config.selectors

        # Extract title
        title_elem = container.select_one(selectors.get("title", "h2"))
        title = title_elem.get_text(strip=True) if title_elem else None
        if not title:
            return None

        # Extract URL
        url_elem = container.select_one(selectors.get("url", "a"))
        if url_elem and url_elem.get("href"):
            url = url_elem["href"]
            # Handle relative URLs
            if url.startswith("/"):
                from urllib.parse import urljoin
                url = urljoin(self.config.url, url)
        else:
            url = self.config.url

        # Extract price
        price = None
        price_elem = container.select_one(selectors.get("price", ".price"))
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price = self._parse_price(price_text)

        # Extract bedrooms
        bedrooms = None
        beds_elem = container.select_one(selectors.get("bedrooms", ".beds"))
        if beds_elem:
            bedrooms = self._parse_int(beds_elem.get_text(strip=True))

        # Extract bathrooms
        bathrooms = None
        baths_elem = container.select_one(selectors.get("bathrooms", ".baths"))
        if baths_elem:
            bathrooms = self._parse_float(baths_elem.get_text(strip=True))

        # Extract square footage
        sqft = None
        sqft_elem = container.select_one(selectors.get("sqft", ".sqft"))
        if sqft_elem:
            sqft = self._parse_int(sqft_elem.get_text(strip=True))

        # Check availability
        available = True
        avail_elem = container.select_one(selectors.get("availability", ".availability"))
        if avail_elem:
            avail_text = avail_elem.get_text(strip=True).lower()
            available = "unavailable" not in avail_text and "not available" not in avail_text

        return Listing(
            site_name=self.config.name,
            title=title,
            url=url,
            price=price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            sqft=sqft,
            available=available,
        )

    def _parse_price(self, text: str) -> float | None:
        """Extract numeric price from text like '$1,500/mo'."""
        import re
        # Remove common non-numeric characters except decimal
        cleaned = re.sub(r"[^\d.]", "", text)
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None

    def _parse_int(self, text: str) -> int | None:
        """Extract integer from text."""
        import re
        match = re.search(r"\d+", text)
        return int(match.group()) if match else None

    def _parse_float(self, text: str) -> float | None:
        """Extract float from text."""
        import re
        match = re.search(r"[\d.]+", text)
        try:
            return float(match.group()) if match else None
        except ValueError:
            return None

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
