"""Listing data model."""

from dataclasses import dataclass, field
from datetime import datetime, date
import hashlib


@dataclass
class Listing:
    """Represents a rental listing scraped from a website."""

    site_name: str
    title: str
    url: str
    price: float | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    sqft: int | None = None
    available: bool = True
    move_in_date: date | None = None
    scraped_at: datetime = field(default_factory=datetime.now)
    id: str = field(default="")

    def __post_init__(self):
        """Generate ID if not provided."""
        if not self.id:
            self.id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate a unique ID based on key fields."""
        # Use site + title + url to create a stable hash
        content = f"{self.site_name}|{self.title}|{self.url}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "site_name": self.site_name,
            "title": self.title,
            "url": self.url,
            "price": self.price,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "sqft": self.sqft,
            "available": self.available,
            "move_in_date": self.move_in_date.isoformat() if self.move_in_date else None,
            "scraped_at": self.scraped_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Listing":
        """Create a Listing from a dictionary."""
        scraped_at = data.get("scraped_at")
        if isinstance(scraped_at, str):
            scraped_at = datetime.fromisoformat(scraped_at)
        elif scraped_at is None:
            scraped_at = datetime.now()

        move_in_date = data.get("move_in_date")
        if isinstance(move_in_date, str):
            move_in_date = date.fromisoformat(move_in_date)

        return cls(
            id=data.get("id", ""),
            site_name=data["site_name"],
            title=data["title"],
            url=data["url"],
            price=data.get("price"),
            bedrooms=data.get("bedrooms"),
            bathrooms=data.get("bathrooms"),
            sqft=data.get("sqft"),
            available=data.get("available", True),
            move_in_date=move_in_date,
            scraped_at=scraped_at,
        )
