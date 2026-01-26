"""Main server - orchestrates scraping, scheduling, and Telegram integration."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Request

from src.config.settings import Settings, SiteConfig
from src.models.database import Database
from src.models.listing import Listing
from src.scrapers.base import BaseScraper
from src.scrapers.playwright_scraper import PlaywrightScraper
from src.scrapers.static_scraper import StaticScraper
from src.messaging.telegram import TelegramClient
from src.messaging.formatter import (
    format_status,
    format_listings_by_site,
    format_scrape_summary,
)
from src.handlers.webhook import WebhookHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ApartmentFinderServer:
    """Main server class that orchestrates all components."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.load()
        self.db = Database(self.settings.db_path)
        self.telegram = TelegramClient(self.settings.telegram_bot_token)
        self.scheduler = AsyncIOScheduler()
        self.webhook_handler: WebhookHandler | None = None
        self._last_scrape: datetime | None = None

    def _create_scraper(self, site_config: SiteConfig) -> BaseScraper:
        """Create the appropriate scraper for a site."""
        if site_config.scraper_type == "playwright":
            return PlaywrightScraper(site_config)
        return StaticScraper(site_config)

    async def scrape_site(self, site_config: SiteConfig) -> tuple[list[Listing], list[Listing]]:
        """Scrape a single site and return new and removed listings."""
        logger.info(f"Scraping {site_config.name}...")

        async with self._create_scraper(site_config) as scraper:
            all_listings = await scraper.scrape()

        # Filter to only new listings and save all
        new_listings = []
        for listing in all_listings:
            if await self.db.is_new_listing(listing.id):
                new_listings.append(listing)
            await self.db.save_listing(listing)

        # Remove stale listings (units no longer available)
        current_ids = {listing.id for listing in all_listings}
        removed_listings = await self.db.remove_stale_listings(site_config.name, current_ids)
        if removed_listings:
            logger.info(f"Removed {len(removed_listings)} stale listings from {site_config.name}")

        logger.info(f"Found {len(new_listings)} new listings from {site_config.name}")
        return new_listings, removed_listings

    async def scrape_all(self) -> tuple[list[Listing], list[Listing]]:
        """Scrape all configured sites and return new and removed listings."""
        all_new_listings = []
        all_removed_listings = []

        for site in self.settings.sites:
            try:
                new_listings, removed_listings = await self.scrape_site(site)
                all_new_listings.extend(new_listings)
                all_removed_listings.extend(removed_listings)
            except Exception as e:
                logger.error(f"Error scraping {site.name}: {e}")

        self._last_scrape = datetime.now()
        return all_new_listings, all_removed_listings

    async def scrape_and_notify(self):
        """Scrape all sites and send Telegram notification."""
        logger.info("Starting scheduled scrape...")
        new_listings, removed_listings = await self.scrape_all()

        # Always send a message with scrape summary
        message = format_scrape_summary(new_listings, removed_listings)
        await self.telegram.send_message(self.settings.telegram_chat_id, message)
        logger.info(f"Sent notification: {len(new_listings)} new, {len(removed_listings)} removed")

    async def _handle_scrape_all(self) -> str:
        """Handle 'scrape' command from Telegram."""
        new_listings, removed_listings = await self.scrape_all()
        return format_scrape_summary(new_listings, removed_listings)

    async def _handle_scrape_site(self, site_name: str) -> str:
        """Handle 'scrape <site>' command from Telegram."""
        site = self.settings.get_site(site_name)
        if not site:
            available = ", ".join(s.name for s in self.settings.sites)
            return f"Site '{site_name}' not found.\n\nAvailable sites: {available}"

        try:
            new_listings, removed_listings = await self.scrape_site(site)
            return format_scrape_summary(new_listings, removed_listings, site.name)
        except Exception as e:
            logger.error(f"Error scraping {site_name}: {e}")
            return f"Error scraping {site_name}: {str(e)}"

    async def _handle_status(self) -> str:
        """Handle 'status' command from Telegram."""
        listing_count = await self.db.get_listing_count()
        last_scrape = self._last_scrape.isoformat() if self._last_scrape else "Never"
        return format_status(
            total_sites=len(self.settings.sites),
            total_listings=listing_count,
            last_scrape=last_scrape,
        )

    async def _handle_ls(self) -> str:
        """Handle 'ls' command from Telegram - list all scraped listings."""
        listings = await self.db.get_all_listings()
        return format_listings_by_site(listings)

    async def startup(self):
        """Initialize server components."""
        # Validate settings
        errors = self.settings.validate()
        if errors:
            for error in errors:
                logger.warning(f"Config warning: {error}")

        # Connect to database
        await self.db.connect()

        # Initialize webhook handler
        self.webhook_handler = WebhookHandler(
            site_names=[s.name for s in self.settings.sites],
            on_scrape_all=self._handle_scrape_all,
            on_scrape_site=self._handle_scrape_site,
            on_status=self._handle_status,
            on_ls=self._handle_ls,
        )

        # Schedule daily scrape
        hour, minute = map(int, self.settings.daily_scrape_time.split(":"))
        job = self.scheduler.add_job(
            self.scrape_and_notify,
            CronTrigger(hour=hour, minute=minute),
            id="daily_scrape",
            replace_existing=True,
        )
        self.scheduler.start()
        next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S %Z") if job.next_run_time else "unknown"
        logger.info(f"Scheduled daily scrape at {self.settings.daily_scrape_time} (next run: {next_run})")

    async def shutdown(self):
        """Clean up server components."""
        self.scheduler.shutdown(wait=False)
        await self.db.close()
        await self.telegram.close()


# Global server instance
server: ApartmentFinderServer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan handler."""
    global server
    server = ApartmentFinderServer()
    await server.startup()
    yield
    await server.shutdown()


app = FastAPI(title="Apartment Finder", lifespan=lifespan)


@app.post("/webhook")
async def handle_webhook(request: Request):
    """Handle incoming webhook messages from Telegram."""
    # Verify secret token if configured
    if server.settings.telegram_webhook_secret:
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if token != server.settings.telegram_webhook_secret:
            logger.warning("Webhook request with invalid secret token")
            return {"status": "unauthorized"}

    payload = await request.json()

    # Extract message from payload
    result = WebhookHandler.extract_message_from_webhook(payload)
    if result:
        chat_id, text = result
        logger.info(f"Received message from {chat_id}: {text}")

        # Handle the message
        response = await server.webhook_handler.handle_message(text)

        # Send response back
        await server.telegram.send_message(chat_id, response)

    return {"status": "ok"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/scrape")
async def trigger_scrape():
    """Manual scrape trigger endpoint."""
    new_listings, removed_listings = await server.scrape_all()
    return {
        "status": "ok",
        "new_listings": len(new_listings),
        "removed_listings": len(removed_listings),
        "listings": [l.to_dict() for l in new_listings],
        "removed": [l.to_dict() for l in removed_listings],
    }


def main():
    """Entry point for running the server."""
    import uvicorn

    settings = Settings.load()
    uvicorn.run(
        "src.server:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
