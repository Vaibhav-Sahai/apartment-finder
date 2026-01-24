# Apartment Finder

A Python bot that scrapes rental websites and sends notifications via WhatsApp. Supports scheduled daily updates and on-demand scraping via WhatsApp commands.

## Features

- **Multi-site scraping** - Configure multiple rental websites with custom CSS selectors
- **Two scraper types** - Static HTML (fast) and Playwright browser automation (for JS-heavy sites)
- **WhatsApp integration** - Daily notifications + respond to commands via WhatsApp
- **Duplicate detection** - SQLite database tracks seen listings to avoid repeat notifications
- **Flexible scheduling** - Configure daily scrape time via environment variable

## How It Works

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  APScheduler    │────▶│   Scrapers   │────▶│  Database   │
│  (daily cron)   │     │              │     │  (SQLite)   │
└─────────────────┘     └──────────────┘     └─────────────┘
                                                    │
                                                    ▼
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  WhatsApp       │◀────│  Formatter   │◀────│ New Listings│
│  (send msg)     │     │              │     │ (filtered)  │
└─────────────────┘     └──────────────┘     └─────────────┘
        │
        ▼
┌─────────────────┐     ┌──────────────┐
│  User Phone     │────▶│  FastAPI     │
│  (commands)     │     │  Webhook     │
└─────────────────┘     └──────────────┘
```

1. **Scheduled scrape** - APScheduler triggers scraping at your configured time
2. **Scrape sites** - Each configured site is scraped using the appropriate scraper
3. **Filter duplicates** - Database checks which listings are new
4. **Format & notify** - New listings are formatted and sent via WhatsApp
5. **Commands** - You can also send WhatsApp messages to trigger scrapes on-demand

## Project Structure

```
apartment-finder/
├── src/                    # Source code
│   ├── server.py           # Main entry point - FastAPI server + scheduler
│   ├── config/             # Configuration management
│   │   └── settings.py     # Load .env and sites.yaml into dataclasses
│   ├── scrapers/           # Web scraping implementations
│   │   ├── base.py         # Abstract BaseScraper interface
│   │   ├── static_scraper.py    # For simple HTML sites (httpx + BeautifulSoup)
│   │   └── playwright_scraper.py # For JS-rendered sites (browser automation)
│   ├── models/             # Data models and persistence
│   │   ├── listing.py      # Listing dataclass
│   │   └── database.py     # SQLite operations for tracking listings
│   ├── messaging/          # WhatsApp integration
│   │   ├── whatsapp.py     # Meta Business API client
│   │   └── formatter.py    # Format listings for WhatsApp messages
│   └── handlers/           # Request handlers
│       └── webhook.py      # Parse and route incoming WhatsApp commands
├── config/                 # Configuration files (gitignored except examples)
│   └── sites.example.yaml  # Example site configuration
├── .env.example            # Example environment variables
├── pyproject.toml          # Project dependencies and metadata
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.14+ (free-threaded build recommended)
- [uv](https://docs.astral.sh/uv/) package manager
- Meta Business Account with WhatsApp API access
- Tailscale (optional, for webhook endpoint)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Vaibhav-Sahai/apartment-finder.git
   cd apartment-finder
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Install Playwright browser**
   ```bash
   uv run playwright install chromium
   ```

### Configuration

1. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your credentials:
   ```env
   WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
   WHATSAPP_ACCESS_TOKEN=your_access_token
   WHATSAPP_VERIFY_TOKEN=your_custom_verify_token
   RECIPIENT_PHONE=14155238886
   DAILY_SCRAPE_TIME=09:00
   ```

2. **Configure sites to scrape**
   ```bash
   cp config/sites.example.yaml config/sites.yaml
   ```

   Edit `config/sites.yaml` with your target sites:
   ```yaml
   sites:
     - name: "My Apartments"
       url: "https://example.com/listings"
       scraper_type: "playwright"  # or "static"
       selectors:
         listing_container: ".listing-card"
         title: "h2"
         price: ".price"
         bedrooms: ".beds"
         sqft: ".sqft"
         url: "a"
       wait_for: ".listings-loaded"  # optional, playwright only
   ```

### WhatsApp API Setup

1. Create a [Meta Business Account](https://business.facebook.com/)
2. Go to [Meta for Developers](https://developers.facebook.com/) and create an app
3. Add the WhatsApp product to your app
4. Get your Phone Number ID and Access Token from the WhatsApp > API Setup page
5. Configure the webhook URL (see below)

### Webhook Setup (for receiving WhatsApp commands)

The bot needs a public URL to receive incoming WhatsApp messages.

**Using Tailscale Funnel:**
```bash
tailscale funnel 8000
# This gives you a URL like: https://your-machine.tail1234.ts.net
```

Then configure this URL in Meta Developer Portal:
- Webhook URL: `https://your-machine.tail1234.ts.net/webhook`
- Verify Token: Same as `WHATSAPP_VERIFY_TOKEN` in your `.env`
- Subscribe to: `messages`

### Running the Server

```bash
uv run python -m src.server
```

The server will:
- Start a FastAPI server on port 8000
- Schedule daily scrapes at your configured time
- Listen for incoming WhatsApp commands

## WhatsApp Commands

Send these messages to your bot's WhatsApp number:

| Command | Description |
|---------|-------------|
| `scrape` | Scrape all configured sites |
| `scrape <site>` | Scrape a specific site by name |
| `status` | Get bot status (sites configured, listings tracked) |
| `list` | List all configured sites |
| `help` | Show available commands |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhook` | GET | WhatsApp webhook verification |
| `/webhook` | POST | Receive incoming WhatsApp messages |
| `/health` | GET | Health check |
| `/scrape` | POST | Manually trigger a scrape (returns JSON) |

## Adding a New Site

1. Open the target site in Chrome DevTools
2. Identify CSS selectors for:
   - Container element for each listing
   - Title, price, bedrooms, sqft, etc.
3. Test selectors in console: `document.querySelectorAll('.your-selector')`
4. Add to `config/sites.yaml`:
   ```yaml
   - name: "New Site"
     url: "https://newsite.com/rentals"
     scraper_type: "playwright"  # Use if site loads content via JavaScript
     selectors:
       listing_container: ".apartment-card"
       title: ".apt-name"
       price: ".rent-price"
     wait_for: ".apartments-loaded"
   ```

## Development

```bash
# Run with auto-reload (development)
uv run uvicorn src.server:app --reload --port 8000

# Run a one-off scrape (without starting server)
uv run python -c "
import asyncio
from src.server import ApartmentFinderServer

async def main():
    server = ApartmentFinderServer()
    await server.db.connect()
    listings = await server.scrape_all()
    for l in listings:
        print(f'{l.title}: \${l.price}')
    await server.db.close()

asyncio.run(main())
"
```

## License

Apache License 2.0
