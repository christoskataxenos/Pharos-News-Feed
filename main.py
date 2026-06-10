from fastapi import FastAPI, Depends, BackgroundTasks, Request, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, func
from pydantic import BaseModel
from typing import List, Optional

from bs4 import BeautifulSoup
from readability import Document
from deep_translator import GoogleTranslator
import aiohttp

from database import get_db, engine, Base
from models import Article, Category, Feed, UserInteraction
from fetcher import update_all_feeds

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="FeedFlow V2 Premium")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

security = HTTPBasic()
ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "secret")

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USER)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASS)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # We could seed here automatically or wait for seeder.py

@app.get("/")
async def serve_spa():
    return FileResponse("static/index.html")

@app.get("/api/init_data")
@limiter.limit("30/minute")
async def get_init_data(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category))
    categories = result.scalars().all()
    
    data = []
    for cat in categories:
        # fetch feeds for category
        feeds_res = await db.execute(select(Feed).where(Feed.category_id == cat.id))
        feeds = feeds_res.scalars().all()
        
        data.append({
            "id": cat.id,
            "name": cat.name,
            "feeds": [{
                "id": f.id, 
                "title": f.title, 
                "is_favorite": f.is_favorite,
                "type": f.type
            } for f in feeds]
        })
    return data

@app.post("/api/refresh")
@limiter.limit("10/minute")
async def refresh_feeds(request: Request, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    # Run fetch asynchronously in background
    background_tasks.add_task(update_all_feeds)
    return {"status": "started", "message": "High-speed refresh started in background!"}

class ArticleResponse(BaseModel):
    id: int
    title: str
    summary: Optional[str]
    link: str
    image_url: Optional[str]
    published: str
    raw_published: str
    feed_title: str
    feed_type: str
    is_read: bool

class PaginatedArticlesResponse(BaseModel):
    articles: List[ArticleResponse]
    has_next: bool
    total: int

@app.get("/api/articles", response_model=PaginatedArticlesResponse)
@limiter.limit("100/minute")
async def get_articles(request: Request, last_date: str = None, category_id: int = None, feed_id: int = None, db: AsyncSession = Depends(get_db)):
    per_page = 20
    
    query = select(Article, Feed).join(Feed, Article.feed_id == Feed.id).order_by(desc(Article.published), desc(Article.id))
    count_query = select(func.count(Article.id)).join(Feed, Article.feed_id == Feed.id)
    
    if category_id:
        query = query.where(Feed.category_id == category_id)
        count_query = count_query.where(Feed.category_id == category_id)
    if feed_id:
        query = query.where(Article.feed_id == feed_id)
        count_query = count_query.where(Article.feed_id == feed_id)
        
    if last_date:
        from datetime import datetime
        try:
            ld = datetime.fromisoformat(last_date)
            query = query.where(Article.published < ld)
        except Exception:
            pass
            
    query = query.limit(per_page)
    
    result = await db.execute(query)
    rows = result.all()
    
    total_result = await db.execute(count_query)
    total_count = total_result.scalar_one()
    
    articles = []
    for art, feed in rows:
        articles.append({
            "id": art.id,
            "title": art.title,
            "summary": art.summary,
            "link": art.link,
            "image_url": art.image_url,
            "published": art.published.strftime("%d %b, %Y %H:%M"),
            "raw_published": art.published.isoformat(),
            "feed_title": feed.title,
            "feed_type": feed.type,
            "is_read": art.is_read
        })
        
    return {
        "articles": articles,
        "has_next": len(articles) == per_page,
        "total": total_count
    }

@app.post("/api/mark_read/{article_id}")
@limiter.limit("200/minute")
async def mark_read(request: Request, article_id: int, db: AsyncSession = Depends(get_db)):
    art_res = await db.execute(select(Article).where(Article.id == article_id))
    article = art_res.scalar_one_or_none()
    if article:
        article.is_read = True
        interaction = UserInteraction(article_id=article_id, interaction_type="read")
        db.add(interaction)
        await db.commit()
    return {"status": "success"}

@app.get("/api/article/{article_id}/read")
@limiter.limit("50/minute")
async def read_article(request: Request, article_id: int, lang: str = None, db: AsyncSession = Depends(get_db)):
    art_res = await db.execute(select(Article).where(Article.id == article_id))
    article = art_res.scalar_one_or_none()
    if not article:
        return {"error": "Article not found"}
        
    import asyncio
    try:
        html = article.summary or ""
        try:
            async with aiohttp.ClientSession(connector = aiohttp.TCPConnector(ssl = False)) as session:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                async with session.get(article.link, headers=headers, timeout=5) as resp:
                    if resp.status == 200:
                        html = await resp.text()
        except Exception:
            pass # Fallback to summary if live fetch fails or times out
                
        # Use Readability to extract main content and remove clutter
        if "<html" in html.lower():
            doc = Document(html)
            title = doc.title()
            content = doc.summary()
        else:
            title = article.title
            content = html
        
        # Mark as read since user opened the reader
        if not article.is_read:
            article.is_read = True
            db.add(UserInteraction(article_id=article_id, interaction_type="read"))
            await db.commit()
            
        if lang:
            def sync_translate():
                soup = BeautifulSoup(content, 'html.parser')
                translator = GoogleTranslator(source='auto', target=lang)
                for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'li']):
                    text = element.get_text(strip=True)
                    if text and len(text) > 2:
                        try:
                            element.string = translator.translate(text)
                        except Exception:
                            pass
                translated_title = title
                try:
                    translated_title = translator.translate(title)
                except Exception:
                    pass
                return translated_title, str(soup)
                
            title, content = await asyncio.to_thread(sync_translate)

        return {"title": title, "content": content, "url": article.link}
    except Exception as e:
        return {"error": str(e)}

@app.delete("/api/feeds/{feed_id}")
async def delete_feed(feed_id: int, db: AsyncSession = Depends(get_db)):
    feed_res = await db.execute(select(Feed).where(Feed.id == feed_id))
    feed = feed_res.scalar_one_or_none()
    if feed:
        await db.delete(feed)
        await db.commit()
    return {"status": "success"}

from pydantic import BaseModel
import feedparser

class FeedCreate(BaseModel):
    url: str
    category_name: str
    title: str

async def discover_feed(url: str) -> tuple[str, str]:
    """
    Δοκιμάζει να βρει το RSS URL από μια σελίδα.
    Αν βρει RSS, επιστρέφει (rss_url, 'article').
    Αν δεν βρει, επιστρέφει (url, 'scrape').
    """
    # Κανονικοποίηση της διεύθυνσης URL αν λείπει το σχήμα http/https
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0', '::1'] or (parsed.hostname and parsed.hostname.endswith('.local')):
            return url, 'scrape'
    except Exception:
        pass

    try:
        async with aiohttp.ClientSession(connector = aiohttp.TCPConnector(ssl = False)) as session:
            headers = {"User-Agent": "Mozilla/5.0"}
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    return url, 'scrape'
                
                content_type = resp.headers.get('Content-Type', '')
                if 'xml' in content_type or 'rss' in content_type:
                    return url, 'article'
                    
                html = await resp.text()
                
                # Check feedparser quickly if it's actually an RSS despite headers
                parsed = feedparser.parse(html)
                if parsed.entries:
                    return url, 'article'
                
                from bs4 import BeautifulSoup
                from urllib.parse import urljoin
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for alternate links
                for link in soup.find_all('link', rel='alternate'):
                    link_type = link.get('type', '').lower()
                    if 'rss+xml' in link_type or 'atom+xml' in link_type:
                        href = link.get('href')
                        if href:
                            return urljoin(url, href), 'article'
                            
                return url, 'scrape'
    except Exception as e:
        print(f"Discovery error for {url}: {e}")
        return url, 'scrape'

@app.post("/api/feeds")
@limiter.limit("20/minute")
async def add_feed(request: Request, feed: FeedCreate, db: AsyncSession = Depends(get_db)):
    # Αναζήτηση αν η κατηγορία υπάρχει ήδη στη βάση με βάση το όνομα
    category_name_stripped = feed.category_name.strip()
    stmt = select(Category).where(Category.name == category_name_stripped)
    result = await db.execute(stmt)
    category = result.scalar_one_or_none()
    
    # Αν δεν υπάρχει η κατηγορία, τη δημιουργούμε δυναμικά
    if not category:
        category = Category(name = category_name_stripped)
        db.add(category)
        await db.flush()  # Λήψη του παραχθέντος ID της νέας κατηγορίας
        
    resolved_url, feed_type = await discover_feed(feed.url)
    
    # Δημιουργία και προσθήκη της νέας ροής (feed)
    new_feed = Feed(
        url = resolved_url,
        category_id = category.id,
        title = feed.title,
        type = feed_type
    )
    db.add(new_feed)
    await db.commit()
    
    return {
        "status": "success",
        "id": new_feed.id,
        "resolved_url": resolved_url,
        "type": feed_type
    }
