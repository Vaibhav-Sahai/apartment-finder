"""SQLite database operations for tracking listings."""

import aiosqlite
from datetime import datetime, timedelta
from pathlib import Path

from src.models.listing import Listing


class Database:
    """Async SQLite database for storing and querying listings."""

    def __init__(self, db_path: str = "listings.db"):
        self.db_path = Path(db_path)
        self._connection: aiosqlite.Connection | None = None

    async def connect(self):
        """Open database connection and create tables if needed."""
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self):
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def _create_tables(self):
        """Create database tables if they don't exist."""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id TEXT PRIMARY KEY,
                site_name TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                price REAL,
                bedrooms INTEGER,
                bathrooms REAL,
                sqft INTEGER,
                available INTEGER DEFAULT 1,
                scraped_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_listings_site ON listings(site_name)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_listings_scraped ON listings(scraped_at)
        """)
        await self._connection.commit()

    async def is_new_listing(self, listing_id: str) -> bool:
        """Check if a listing ID has been seen before."""
        cursor = await self._connection.execute(
            "SELECT 1 FROM listings WHERE id = ?", (listing_id,)
        )
        row = await cursor.fetchone()
        return row is None

    async def save_listing(self, listing: Listing):
        """Save a listing to the database."""
        data = listing.to_dict()
        await self._connection.execute(
            """
            INSERT OR REPLACE INTO listings
            (id, site_name, title, url, price, bedrooms, bathrooms, sqft, available, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["id"],
                data["site_name"],
                data["title"],
                data["url"],
                data["price"],
                data["bedrooms"],
                data["bathrooms"],
                data["sqft"],
                1 if data["available"] else 0,
                data["scraped_at"],
            ),
        )
        await self._connection.commit()

    async def save_listings(self, listings: list[Listing]):
        """Save multiple listings to the database."""
        for listing in listings:
            await self.save_listing(listing)

    async def get_recent_listings(self, hours: int = 24) -> list[Listing]:
        """Get listings from the last N hours."""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        cursor = await self._connection.execute(
            "SELECT * FROM listings WHERE scraped_at >= ? ORDER BY scraped_at DESC",
            (cutoff,),
        )
        rows = await cursor.fetchall()
        return [Listing.from_dict(dict(row)) for row in rows]

    async def get_listings_by_site(self, site_name: str) -> list[Listing]:
        """Get all listings for a specific site."""
        cursor = await self._connection.execute(
            "SELECT * FROM listings WHERE site_name = ? ORDER BY scraped_at DESC",
            (site_name,),
        )
        rows = await cursor.fetchall()
        return [Listing.from_dict(dict(row)) for row in rows]

    async def get_listing_count(self) -> int:
        """Get total number of listings in database."""
        cursor = await self._connection.execute("SELECT COUNT(*) FROM listings")
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
