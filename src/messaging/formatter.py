"""Format listings for WhatsApp messages."""

from src.models.listing import Listing


def format_listing(listing: Listing) -> str:
    """Format a single listing for WhatsApp.

    Args:
        listing: The listing to format

    Returns:
        Formatted string for the listing
    """
    lines = [f"*{listing.title}*"]

    if listing.price:
        lines.append(f"Price: ${listing.price:,.0f}/mo")

    details = []
    if listing.bedrooms is not None:
        details.append(f"{listing.bedrooms} bed")
    if listing.bathrooms is not None:
        details.append(f"{listing.bathrooms:.1f} bath")
    if listing.sqft:
        details.append(f"{listing.sqft:,} sqft")

    if details:
        lines.append(" | ".join(details))

    if not listing.available:
        lines.append("_Currently unavailable_")

    lines.append(listing.url)

    return "\n".join(lines)


def format_listings(listings: list[Listing], site_name: str | None = None) -> str:
    """Format multiple listings for WhatsApp.

    Args:
        listings: List of listings to format
        site_name: Optional site name for the header

    Returns:
        Formatted string with all listings
    """
    if not listings:
        if site_name:
            return f"No new listings found on {site_name}."
        return "No new listings found."

    header = f"*{len(listings)} New Listing(s)*"
    if site_name:
        header = f"*{len(listings)} New Listing(s) from {site_name}*"

    formatted = [header, ""]

    for i, listing in enumerate(listings, 1):
        formatted.append(f"*{i}.* {format_listing(listing)}")
        formatted.append("")  # Empty line between listings

    return "\n".join(formatted)


def format_status(
    total_sites: int,
    total_listings: int,
    last_scrape: str | None = None,
) -> str:
    """Format a status message.

    Args:
        total_sites: Number of configured sites
        total_listings: Total listings in database
        last_scrape: Timestamp of last scrape

    Returns:
        Formatted status message
    """
    lines = [
        "*Apartment Finder Status*",
        "",
        f"Sites configured: {total_sites}",
        f"Total listings tracked: {total_listings}",
    ]

    if last_scrape:
        lines.append(f"Last scrape: {last_scrape}")

    return "\n".join(lines)


def format_site_list(site_names: list[str]) -> str:
    """Format the list of configured sites.

    Args:
        site_names: List of site names

    Returns:
        Formatted site list message
    """
    if not site_names:
        return "No sites configured."

    lines = ["*Configured Sites:*", ""]
    for name in site_names:
        lines.append(f"- {name}")

    lines.append("")
    lines.append("_Use 'scrape <site>' to scrape a specific site_")

    return "\n".join(lines)
