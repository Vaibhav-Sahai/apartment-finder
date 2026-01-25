# Apartment Finder

![Apartment Finder](images/cover.png)

A Python bot that scrapes rental websites and sends notifications via Telegram. Supports scheduled daily updates and on-demand scraping via Telegram commands.

## Features

- **Multi-site scraping** - Configure multiple rental websites with custom CSS selectors
- **Two scraper types** - Static HTML (httpx + BeautifulSoup) and Playwright (for JS-heavy sites)
- **Interactive site support** - Click through elements (e.g., floor selectors) to reveal hidden content
- **Telegram integration** - Daily notifications + on-demand commands
- **Smart tracking** - SQLite database deduplicates listings and removes stale ones (taken units)

## How It Works

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  APScheduler    │────▶│   Scrapers   │────▶│   SQLite    │
│  (daily cron)   │     │              │     │  (tracking) │
└─────────────────┘     └──────────────┘     └─────────────┘
                                                    │
┌─────────────────┐     ┌──────────────┐            ▼
│  Telegram Bot   │◀───▶│   FastAPI    │◀────  New Listings
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
- Telegram account

### Installation

```bash
git clone https://github.com/Vaibhav-Sahai/apartment-finder.git
cd apartment-finder
uv sync
uv run playwright install chromium
```

### Telegram Bot Setup

1. **Create a bot**: Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` and follow the prompts
   - Save the bot token (looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

2. **Get your chat ID**:
   - Message your new bot (send any message)
   - Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Find `"chat":{"id":123456789}` in the response

3. **Set webhook** (after deploying your server):
   ```bash
   curl "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=https://your-server.com/webhook"
   ```

### Configuration

**Environment variables** (`.env`):
```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=123456789
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

### Webhook Setup

For local development with Tailscale:
```bash
tailscale funnel 8000
# Then set webhook:
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://your-machine.tail1234.ts.net/webhook"
```

### Running

```bash
uv run python -m src.server
```

## Telegram Commands

| Command | Description |
|---------|-------------|
| `scrape` | Scrape all configured sites |
| `scrape <site>` | Scrape a specific site |
| `ls` | List all scraped listings by site |
| `status` | Bot status and stats |
| `list` | List configured sites |
| `help` | Show commands |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhook` | POST | Telegram webhook |
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
│   ├── telegram.py        # Telegram Bot API client
│   └── formatter.py       # Message formatting
└── handlers/webhook.py    # Telegram command routing
```

## License

Apache License 2.0
