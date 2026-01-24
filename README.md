# Apartment Finder

A Python bot that scrapes rental websites and sends notifications via WhatsApp. Supports scheduled daily updates and on-demand scraping via WhatsApp commands.

## Features

- **Multi-site scraping** - Configure multiple rental websites with custom CSS selectors
- **Two scraper types** - Static HTML (httpx + BeautifulSoup) and Playwright (for JS-heavy sites)
- **Interactive site support** - Click through elements (e.g., floor selectors) to reveal hidden content
- **WhatsApp integration** - Daily notifications + on-demand commands
- **Smart tracking** - SQLite database deduplicates listings and removes stale ones (taken units)

## How It Works

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  APScheduler    │────▶│   Scrapers   │────▶│   SQLite    │
│  (daily cron)   │     │              │     │  (tracking) │
└─────────────────┘     └──────────────┘     └─────────────┘
                                                    │
┌─────────────────┐     ┌──────────────┐            ▼
│  User Phone     │◀───▶│   FastAPI    │◀────  New Listings
│  (commands)     │     │   Webhook    │
└─────────────────┘     └──────────────┘
```

## Database Schema

```sql
CREATE TABLE listings (
    id TEXT PRIMARY KEY,          -- SHA256 hash of site+title+url
    site_name TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    price REAL,
    bedrooms INTEGER,
    bathrooms REAL,
    sqft INTEGER,
    available INTEGER DEFAULT 1,
    move_in_date TEXT,            -- ISO format (YYYY-MM-DD)
    scraped_at TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

Listings not found on subsequent scrapes are automatically removed (unit taken).

## Getting Started

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- Meta Business Account with WhatsApp API access

### Installation

```bash
git clone https://github.com/Vaibhav-Sahai/apartment-finder.git
cd apartment-finder
uv sync
uv run playwright install chromium
```

### Configuration

**Environment variables** (`.env`):
```env
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_access_token
WHATSAPP_VERIFY_TOKEN=your_custom_verify_token
RECIPIENT_PHONE=14155238886
DAILY_SCRAPE_TIME=09:00
DB_PATH=listings.db
```

**Site configuration** (`config/sites.yaml`):
```yaml
sites:
  - name: "My Apartments"
    url: "https://example.com/listings"
    scraper_type: "playwright"  # or "static"
    selectors:
      listing_container: ".listing-card"
      title: "h2"
      price: ".price"
      details: ".info"           # parses "1 bed 1 bath 800 sq ft"
      availability: ".status"    # parses move-in date
      url: "a"
    wait_for: ".listings-loaded"

    # For interactive sites (e.g., floor plan maps)
    click_each:
      selector: ".floor-button"  # clicks each matching element
      wait_after: 2000           # ms to wait after each click
```

### WhatsApp Webhook Setup

```bash
tailscale funnel 8000
# Configure in Meta Developer Portal:
# - URL: https://your-machine.tail1234.ts.net/webhook
# - Verify Token: same as WHATSAPP_VERIFY_TOKEN
# - Subscribe to: messages
```

### Running

```bash
uv run python -m src.server
```

## WhatsApp Commands

| Command | Description |
|---------|-------------|
| `scrape` | Scrape all configured sites |
| `scrape <site>` | Scrape a specific site |
| `status` | Bot status and stats |
| `list` | List configured sites |
| `help` | Show commands |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhook` | GET/POST | WhatsApp webhook |
| `/health` | GET | Health check |
| `/scrape` | POST | Manual scrape trigger |

## Project Structure

```
src/
├── server.py              # FastAPI + scheduler entry point
├── config/settings.py     # Configuration dataclasses
├── scrapers/
│   ├── base.py            # Abstract scraper interface
│   ├── static_scraper.py  # httpx + BeautifulSoup
│   └── playwright_scraper.py  # Browser automation
├── models/
│   ├── listing.py         # Listing dataclass
│   └── database.py        # SQLite operations
├── messaging/
│   ├── whatsapp.py        # Meta Business API client
│   └── formatter.py       # Message formatting
└── handlers/webhook.py    # WhatsApp command routing
```

## License

Apache License 2.0
