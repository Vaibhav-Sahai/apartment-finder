"""Base scraper interface."""

from abc import ABC, abstractmethod

from src.config.settings import SiteConfig
from src.models.listing import Listing


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    def __init__(self, site_config: SiteConfig):
        self.config = site_config

    @abstractmethod
    async def scrape(self) -> list[Listing]:
        """Scrape the site and return a list of listings.

        Returns:
            List of Listing objects found on the site.
        """
        pass

    @abstractmethod
    async def close(self):
        """Clean up any resources (browsers, connections, etc.)."""
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
