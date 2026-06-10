# FeedFlow V2 (Pharos)

FeedFlow V2 (also known as Pelagos) is a modern, high-performance asynchronous RSS feed reader and aggregator built with FastAPI, SQLAlchemy, and a dynamic frontend styled with Vanilla CSS and Three.js. It features automated Open Graph cover image extraction and parallel feed updating.

## Features

- **High-Performance Async Fetching**: Uses `aiohttp` and `asyncio.gather` with semaphores to parse multiple RSS feeds concurrently without blocking the event loop.
- **SQLite Optimizations**: Configured in WAL (Write-Ahead Logging) mode with explicit busy timeouts to handle high concurrency and prevent 'database is locked' errors.
- **Cursor-Based Pagination**: Employs timestamp-based cursors (`last_date`) instead of traditional offsets for infinite scrolling, ensuring zero duplicate articles and sub-millisecond query performance on large datasets.
- **Production-Ready Security**: 
  - **Authentication**: HTTP Basic Auth guards state-modifying endpoints (adding/deleting feeds, refreshing).
  - **XSS Protection**: Frontend sanitization using `DOMPurify` guarantees safe HTML rendering of external RSS content.
  - **SSRF Prevention**: `urllib` parsing combined with local-IP blocks prevents Server-Side Request Forgery during feed discovery.
  - **Rate Limiting**: Integrated `slowapi` to prevent DDoS and brute-force attacks across all API routes.
- **Translation Engine**: Built-in article translation via `deep-translator` offloaded to background threads to prevent event-loop freezing.
- **Interactive UI**: Animated WebGL background, dark glassmorphic styling, and integrated reader view with `readability-lxml`.

## Project Structure

```
feedflow-v2/
├── static/                 # Frontend assets
│   ├── index.html          # SPA markup
│   ├── styles.css          # Glassmorphic styling and layouts
│   ├── app.js              # State handling, rendering, and API calls
│   └── three_bg.js         # Three.js particle background setup
├── database.py             # SQLite + SQLAlchemy async connection configuration
├── models.py               # Database schemas (Category, Feed, Article, UserInteraction)
├── fetcher.py              # Feed fetching and Open Graph image extraction logic
├── seeder.py               # Initial category and RSS feed database seeding
├── backfill_images.py      # Backfilling utility for fetching missing images on existing articles
├── test_fetcher.py         # Unit tests for image extraction
├── requirements.txt        # Python dependency list
└── main.py                 # FastAPI application and REST API endpoints
```

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
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

### Database Seeding

To initialize the SQLite database and seed the default categories and feeds, run the following command:
```bash
python seeder.py
```

To backfill cover images for any existing articles in the database using the Open Graph scraper, run:
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

Unit tests for image extraction are written using python's built-in `unittest.IsolatedAsyncioTestCase` framework. Run the tests using the following command:
```bash
python -m unittest test_fetcher.py
```
