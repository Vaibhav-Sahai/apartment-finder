"""Scraper for JavaScript-heavy websites using Playwright."""

from playwright.async_api import async_playwright, Browser, Page

from src.scrapers.base import BaseScraper
from src.config.settings import SiteConfig
from src.models.listing import Listing


class PlaywrightScraper(BaseScraper):
    """Scraper for JS-rendered sites that require browser automation."""

    def __init__(self, site_config: SiteConfig):
        super().__init__(site_config)
        self._browser: Browser | None = None
        self._playwright = None

    async def _get_browser(self) -> Browser:
        """Get or create the browser instance."""
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
        return self._browser

    async def scrape(self) -> list[Listing]:
        """Scrape the JS-rendered site and return listings."""
        browser = await self._get_browser()
        page = await browser.new_page()

        try:
            await page.goto(self.config.url, wait_until="networkidle")

            # Wait for specific element if configured
            if self.config.wait_for:
                await page.wait_for_selector(self.config.wait_for, timeout=30000)

            # Extract listings
            listings = await self._extract_listings(page)
            return listings

        finally:
            await page.close()

    async def _extract_listings(self, page: Page) -> list[Listing]:
        """Extract listings from the page using configured selectors."""
        selectors = self.config.selectors
        container_selector = selectors.get("listing_container", ".listing")

        # Get all listing containers
        containers = await page.query_selector_all(container_selector)
        listings = []

        for container in containers:
            listing = await self._parse_listing(container)
            if listing:
                listings.append(listing)

        return listings

    async def _parse_listing(self, container) -> Listing | None:
        """Parse a single listing from its container element."""
        selectors = self.config.selectors

        # Extract title
        title = await self._get_text(container, selectors.get("title", "h2"))
        if not title:
            return None

        # Extract URL
        url = await self._get_href(container, selectors.get("url", "a"))
        if url and url.startswith("/"):
            from urllib.parse import urljoin
            url = urljoin(self.config.url, url)
        url = url or self.config.url

        # Extract price
        price_text = await self._get_text(container, selectors.get("price", ".price"))
        price = self._parse_price(price_text) if price_text else None

        # Extract bedrooms
        beds_text = await self._get_text(container, selectors.get("bedrooms", ".beds"))
        bedrooms = self._parse_int(beds_text) if beds_text else None

        # Extract bathrooms
        baths_text = await self._get_text(container, selectors.get("bathrooms", ".baths"))
        bathrooms = self._parse_float(baths_text) if baths_text else None

        # Extract square footage
        sqft_text = await self._get_text(container, selectors.get("sqft", ".sqft"))
        sqft = self._parse_int(sqft_text) if sqft_text else None

        # Check availability
        available = True
        avail_text = await self._get_text(container, selectors.get("availability", ".availability"))
        if avail_text:
            avail_lower = avail_text.lower()
            available = "unavailable" not in avail_lower and "not available" not in avail_lower

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

    async def _get_text(self, container, selector: str) -> str | None:
        """Get text content from a selector within a container."""
        try:
            elem = await container.query_selector(selector)
            if elem:
                return (await elem.text_content()).strip()
        except Exception:
            pass
        return None

    async def _get_href(self, container, selector: str) -> str | None:
        """Get href attribute from a selector within a container."""
        try:
            elem = await container.query_selector(selector)
            if elem:
                return await elem.get_attribute("href")
        except Exception:
            pass
        return None

    def _parse_price(self, text: str) -> float | None:
        """Extract numeric price from text."""
        import re
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
        """Close browser and playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
