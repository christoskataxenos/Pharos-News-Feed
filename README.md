# Pharos — News Feed Aggregator

Pharos is a modern, high-performance asynchronous news feed aggregator built with FastAPI, SQLAlchemy, and a dynamic glassmorphic frontend. It supports RSS/Atom feeds, web scraping with automatic Cloudflare bypass, Open Graph cover image extraction, and inline article translation.

## Features

- **High-Performance Async Fetching**: Uses `aiohttp` and `asyncio.gather` with semaphores to parse multiple RSS feeds concurrently without blocking the event loop.
- **Cloudflare Bypass**: Automatically falls back to a Google Translate proxy when direct fetching is blocked by Cloudflare JS challenges (e.g. 403 responses), enabling scraping of protected sites like AEK365.
- **Dynamic Categories**: Users can create custom categories on the fly when adding feeds — each new category automatically appears in the sidebar navigation.
- **SQLite Optimizations**: Configured in WAL (Write-Ahead Logging) mode with explicit busy timeouts to handle high concurrency and prevent 'database is locked' errors.
- **Cursor-Based Pagination**: Employs timestamp-based cursors (`last_date`) instead of traditional offsets for infinite scrolling, ensuring zero duplicate articles and sub-millisecond query performance on large datasets.
- **Security**:
  - **XSS Protection**: Frontend sanitization using `DOMPurify` guarantees safe HTML rendering of external RSS content.
  - **SSRF Prevention**: `urllib` parsing combined with local-IP blocks prevents Server-Side Request Forgery during feed discovery.
  - **Rate Limiting**: Integrated `slowapi` to prevent DDoS and brute-force attacks across all API routes.
- **Translation Engine**: Built-in article translation to Greek via `deep-translator`, offloaded to background threads to prevent event-loop freezing.
- **Interactive UI**: Animated WebGL particle background, dark glassmorphic styling, lighthouse loading animation, and integrated reader view with `readability-lxml`.

## Project Structure

```
feedflow-v2/
├── static/                     # Frontend assets
│   ├── index.html              # SPA markup
│   ├── styles.css              # Glassmorphic styling and layouts
│   ├── app.js                  # State handling, rendering, and API calls
│   ├── three_bg.js             # Three.js particle background setup
│   └── lighthouse_spinner.js   # Lighthouse loading animation
├── database.py                 # SQLite + SQLAlchemy async connection configuration
├── models.py                   # Database schemas (Category, Feed, Article, UserInteraction)
├── fetcher.py                  # Feed fetching, scraping, Cloudflare bypass, and OG image extraction
├── seeder.py                   # Initial category and RSS feed database seeding
├── backfill_images.py          # Backfilling utility for fetching missing images on existing articles
├── test_fetcher.py             # Unit tests for image extraction and URL cleaning
├── requirements.txt            # Python dependency list
├── main.py                     # FastAPI application and REST API endpoints
├── Dockerfile                  # Container build configuration
└── .env                        # Environment variables (admin credentials, database URL)
```

## Setup Instructions

### Prerequisites

- Python 3.11 or higher
- `pip` package manager

### Installation

1. Create a Python virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate the virtual environment:
   - On Windows (PowerShell):
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - On Linux/macOS:
     ```bash
     source venv/bin/activate
     ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

Create a `.env` file (or edit the existing one) with your preferred settings:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secret
DATABASE_URL=sqlite+aiosqlite:///./feedhub.db
```

### Database Seeding

To initialize the SQLite database and seed the default categories and feeds:
```bash
python seeder.py
```

To backfill cover images for any existing articles using the Open Graph scraper:
```bash
python backfill_images.py
```

### Running the Application

Start the development server using Uvicorn:
```bash
uvicorn main:app --reload
```

Once started, open your web browser and navigate to `http://127.0.0.1:8000`.

## Testing

Unit tests cover image extraction, URL cleaning (Google Translate proxy cleanup), and edge cases. Run them with:
```bash
python -m unittest test_fetcher.py -v
```

## License

This project is private and intended for personal use.
