"""Scraper implementations for different website types."""

from src.scrapers.base import BaseScraper
from src.scrapers.playwright_scraper import PlaywrightScraper
from src.scrapers.static_scraper import StaticScraper

__all__ = ["BaseScraper", "PlaywrightScraper", "StaticScraper"]
