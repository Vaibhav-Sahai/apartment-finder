"""Scraper for JavaScript-heavy websites using Playwright."""

import re
from datetime import date

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
        import asyncio

        browser = await self._get_browser()
        page = await browser.new_page()

        try:
            # Use "load" instead of "networkidle" for faster initial load
            await page.goto(self.config.url, wait_until="load", timeout=60000)

            # Wait for specific element if configured
            if self.config.wait_for:
                await page.wait_for_selector(self.config.wait_for, timeout=30000)

            # Give JS time to populate data after skeleton loads
            await asyncio.sleep(2)

            # Handle click_each if configured - click through elements to reveal more content
            if self.config.click_each:
                return await self._scrape_with_clicks(page)
            else:
                return await self._extract_listings(page)

        finally:
            await page.close()

    async def _scrape_with_clicks(self, page: Page) -> list[Listing]:
        """Click through elements and aggregate all listings."""
        import asyncio

        click_config = self.config.click_each
        elements = await page.query_selector_all(click_config.selector)

        all_listings = []
        seen_ids = set()

        for element in elements:
            await element.click(force=True)
            await asyncio.sleep(click_config.wait_after / 1000)

            listings = await self._extract_listings(page)
            for listing in listings:
                if listing.id not in seen_ids:
                    seen_ids.add(listing.id)
                    all_listings.append(listing)

        return all_listings

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

        # Initialize optional fields
        bedrooms = None
        bathrooms = None
        sqft = None

        # Check for combined details field (e.g., "1 bed 1 bath 803 sq. ft.")
        details_text = await self._get_text(container, selectors.get("details", ""))
        if details_text:
            bedrooms, bathrooms, sqft = self._parse_combined_details(details_text)
        else:
            # Fall back to individual selectors
            beds_text = await self._get_text(container, selectors.get("bedrooms", ".beds"))
            bedrooms = self._parse_int(beds_text) if beds_text else None

            baths_text = await self._get_text(container, selectors.get("bathrooms", ".baths"))
            bathrooms = self._parse_float(baths_text) if baths_text else None

            sqft_text = await self._get_text(container, selectors.get("sqft", ".sqft"))
            sqft = self._parse_int(sqft_text) if sqft_text else None

        # Check availability and extract move-in date
        available = True
        move_in_date = None
        avail_text = await self._get_text(container, selectors.get("availability", ".availability"))
        if avail_text:
            avail_lower = avail_text.lower()
            available = "unavailable" not in avail_lower and "not available" not in avail_lower
            move_in_date = self._parse_move_in_date(avail_text)

        return Listing(
            site_name=self.config.name,
            title=title,
            url=url,
            price=price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            sqft=sqft,
            available=available,
            move_in_date=move_in_date,
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

    def _parse_combined_details(self, text: str) -> tuple[int | None, float | None, int | None]:
        """Parse combined details text like '1 bed 1 bath 803 sq. ft.'"""
        text_lower = text.lower()

        # Extract bedrooms
        beds_match = re.search(r"(\d+)\s*(?:bed|br|bedroom)", text_lower)
        bedrooms = int(beds_match.group(1)) if beds_match else None

        # Extract bathrooms
        baths_match = re.search(r"([\d.]+)\s*(?:bath|ba|bathroom)", text_lower)
        bathrooms = float(baths_match.group(1)) if baths_match else None

        # Extract square footage
        sqft_match = re.search(r"([\d,]+)\s*(?:sq\.?\s*ft\.?|sqft|sf)", text_lower)
        sqft = int(sqft_match.group(1).replace(",", "")) if sqft_match else None

        return bedrooms, bathrooms, sqft

    def _parse_move_in_date(self, text: str):
        """Parse move-in date from availability text like 'Available 01/28/25' or 'Available Now'."""
        text_lower = text.lower()

        # Check for "now" or "today"
        if "now" in text_lower or "today" in text_lower:
            return date.today()

        month_names = {
            "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
            "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
            "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
            "nov": 11, "november": 11, "dec": 12, "december": 12,
        }

        # Match various date formats: MM/DD/YY, MM/DD/YYYY, MM-DD-YY, etc.
        date_match = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})", text)
        if date_match:
            month = int(date_match.group(1))
            day = int(date_match.group(2))
            year = int(date_match.group(3))
            # Handle 2-digit years
            if year < 100:
                year += 2000
            try:
                return date(year, month, day)
            except ValueError:
                pass

        # Match "January 28, 2025" or "Jan 28 2025" style (with year)
        month_pattern = "|".join(month_names.keys())
        text_match = re.search(rf"({month_pattern})\w*\.?\s+(\d{{1,2}})\w*,?\s*(\d{{4}})", text_lower)
        if text_match:
            month = month_names.get(text_match.group(1)[:3])
            day = int(text_match.group(2))
            year = int(text_match.group(3))
            if month:
                try:
                    return date(year, month, day)
                except ValueError:
                    pass

        # Match "Feb 7th" or "February 7" style (without year - use current year)
        text_match = re.search(rf"({month_pattern})\w*\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:\s|$|,)", text_lower)
        if text_match:
            month = month_names.get(text_match.group(1)[:3])
            day = int(text_match.group(2))
            year = date.today().year
            if month:
                try:
                    return date(year, month, day)
                except ValueError:
                    pass

        return None

    async def close(self):
        """Close browser and playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
