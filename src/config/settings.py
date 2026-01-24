"""Settings management - loads from .env and sites.yaml."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
import os


@dataclass
class ClickEachConfig:
    """Configuration for clicking through elements to reveal more content."""

    selector: str
    wait_after: int = 2000  # milliseconds to wait after each click

    @classmethod
    def from_dict(cls, data: dict) -> "ClickEachConfig":
        return cls(
            selector=data["selector"],
            wait_after=data.get("wait_after", 2000),
        )


@dataclass
class SiteConfig:
    """Configuration for a single site to scrape."""

    name: str
    url: str
    scraper_type: Literal["static", "playwright"]
    selectors: dict[str, str]
    wait_for: str | None = None  # CSS selector to wait for (playwright only)
    click_each: ClickEachConfig | None = None  # Click through elements to reveal content

    @classmethod
    def from_dict(cls, data: dict) -> "SiteConfig":
        click_each = None
        if "click_each" in data:
            click_each = ClickEachConfig.from_dict(data["click_each"])

        return cls(
            name=data["name"],
            url=data["url"],
            scraper_type=data.get("scraper_type", "static"),
            selectors=data.get("selectors", {}),
            wait_for=data.get("wait_for"),
            click_each=click_each,
        )


@dataclass
class Settings:
    """Application settings loaded from environment and config files."""

    # Telegram Bot API
    telegram_bot_token: str
    telegram_chat_id: str

    # Schedule
    daily_scrape_time: str  # HH:MM format

    # Database
    db_path: str

    # Server
    host: str
    port: int

    # Sites to scrape
    sites: list[SiteConfig] = field(default_factory=list)

    @classmethod
    def load(cls, env_path: str | None = None, sites_path: str | None = None) -> "Settings":
        """Load settings from .env file and sites.yaml."""
        # Load environment variables
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()

        # Load sites configuration
        sites = []
        sites_file = Path(sites_path) if sites_path else Path("config/sites.yaml")
        if sites_file.exists():
            with open(sites_file) as f:
                sites_data = yaml.safe_load(f)
                if sites_data and "sites" in sites_data:
                    sites = [SiteConfig.from_dict(s) for s in sites_data["sites"]]

        return cls(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            daily_scrape_time=os.getenv("DAILY_SCRAPE_TIME", "09:00"),
            db_path=os.getenv("DB_PATH", "listings.db"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            sites=sites,
        )

    def get_site(self, name: str) -> SiteConfig | None:
        """Get a site config by name (case-insensitive)."""
        name_lower = name.lower()
        for site in self.sites:
            if site.name.lower() == name_lower:
                return site
        return None

    def validate(self) -> list[str]:
        """Validate settings and return list of errors."""
        errors = []
        if not self.telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        if not self.telegram_chat_id:
            errors.append("TELEGRAM_CHAT_ID is required")
        if not self.sites:
            errors.append("No sites configured in sites.yaml")
        return errors
