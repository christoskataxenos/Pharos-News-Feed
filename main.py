from fastapi import FastAPI, Depends, BackgroundTasks, Request, HTTPException, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import os
import asyncio
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, func, text
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import List, Optional

from bs4 import BeautifulSoup
from readability import Document
from deep_translator import GoogleTranslator
import aiohttp

import database
from database import get_db, engine, Base, AsyncSessionLocal
from models import Article, Category, Feed, UserInteraction, AdminUser
from fetcher import update_all_feeds

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Pharos News Feed")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

security = HTTPBasic()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _env_credentials() -> Optional[tuple[str, str]]:
    """Return (username, password) if both admin env vars are set, else None.

    Env vars always take priority over the DB-backed admin (advanced/IaC mode).
    """
    user = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    if user and password:
        return user, password
    return None


async def is_setup_mode(db: AsyncSession) -> bool:
    """Setup mode is active only when there are no env credentials AND no AdminUser record."""
    if _env_credentials() is not None:
        return False
    result = await db.execute(select(func.count(AdminUser.id)))
    return result.scalar_one() == 0


async def _setup_mode_via_factory() -> bool:
    """Setup-mode check for the middleware, which cannot use Depends()."""
    if _env_credentials() is not None:
        return False
    async with database.AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(AdminUser.id)))
        return result.scalar_one() == 0


async def verify_admin(
    credentials: HTTPBasicCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    env = _env_credentials()
    if env is not None:
        env_user, env_pass = env
        correct_username = secrets.compare_digest(credentials.username, env_user)
        correct_password = secrets.compare_digest(credentials.password, env_pass)
        if correct_username and correct_password:
            return credentials.username
    else:
        result = await db.execute(
            select(AdminUser).where(AdminUser.username == credentials.username)
        )
        admin = result.scalar_one_or_none()
        if admin and pwd_context.verify(credentials.password, admin.password_hash):
            return credentials.username

    raise HTTPException(
        status_code=401,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Basic"},
    )


@app.middleware("http")
async def setup_redirect_middleware(request: Request, call_next):
    """Redirect every request to /setup until the first admin exists."""
    path = request.url.path
    if path.startswith("/setup") or path.startswith("/static"):
        return await call_next(request)
    if await _setup_mode_via_factory():
        return RedirectResponse(url="/setup", status_code=307)
    return await call_next(request)


# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


SETUP_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pharos | First-Run Setup</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:wght@600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-dark: #05101a;
            --panel-bg: rgba(10, 25, 40, 0.7);
            --panel-border: rgba(0, 180, 216, 0.12);
            --text-main: #E2E8F0;
            --text-muted: #8FA5BA;
            --accent: #00B4D8;
            --accent-hover: #48CAE4;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center;
            background: var(--bg-dark); color: var(--text-main); font-family: 'Inter', sans-serif;
            background-image: radial-gradient(circle at 20% 20%, rgba(0,180,216,0.15), transparent 40%),
                              radial-gradient(circle at 80% 80%, rgba(244,162,97,0.08), transparent 40%);
        }}
        .card {{
            width: 100%; max-width: 420px; padding: 40px;
            background: var(--panel-bg); border: 1px solid var(--panel-border);
            border-radius: 18px; backdrop-filter: blur(18px); box-shadow: 0 8px 40px rgba(0,0,0,0.4);
        }}
        h1 {{ font-family: 'Playfair Display', serif; margin: 0 0 6px; font-size: 28px; }}
        p.sub {{ color: var(--text-muted); margin: 0 0 26px; font-size: 14px; }}
        label {{ display: block; font-size: 13px; color: var(--text-muted); margin: 16px 0 6px; text-transform: uppercase; letter-spacing: 1px; }}
        input {{
            width: 100%; padding: 12px 14px; border-radius: 10px; border: 1px solid var(--panel-border);
            background: rgba(5,16,26,0.6); color: var(--text-main); font-size: 15px; outline: none;
        }}
        input:focus {{ border-color: var(--accent); }}
        button {{
            margin-top: 26px; width: 100%; padding: 13px; border: none; border-radius: 10px;
            background: var(--accent); color: var(--bg-dark); font-weight: 600; font-size: 15px; cursor: pointer;
            transition: background 0.2s ease;
        }}
        button:hover {{ background: var(--accent-hover); }}
        .error {{ background: rgba(220,50,50,0.15); border: 1px solid rgba(220,50,50,0.4); color: #ffb3b3;
                  padding: 10px 14px; border-radius: 10px; font-size: 14px; margin-bottom: 18px; }}
        .brand {{ color: var(--accent); font-size: 13px; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 18px; }}
    </style>
</head>
<body>
    <form class="card" method="post" action="/setup">
        <div class="brand">Pharos</div>
        <h1>Welcome aboard</h1>
        <p class="sub">Create your administrator account to secure feed management. This screen appears only once.</p>
        {error_block}
        <label for="username">Username</label>
        <input id="username" name="username" type="text" autocomplete="username" required autofocus>
        <label for="password">Password</label>
        <input id="password" name="password" type="password" autocomplete="new-password" required>
        <label for="confirm_password">Confirm Password</label>
        <input id="confirm_password" name="confirm_password" type="password" autocomplete="new-password" required>
        <button type="submit">Create admin &amp; continue</button>
    </form>
</body>
</html>"""


def _render_setup(error: Optional[str] = None) -> HTMLResponse:
    error_block = f'<div class="error">{error}</div>' if error else ""
    return HTMLResponse(SETUP_PAGE.format(error_block=error_block))


@app.get("/setup", response_class=HTMLResponse)
async def setup_form(request: Request, db: AsyncSession = Depends(get_db)):
    if not await is_setup_mode(db):
        return RedirectResponse(url="/", status_code=307)
    return _render_setup()


@app.post("/setup")
async def setup_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    # Permanently locked once an admin exists.
    if not await is_setup_mode(db):
        raise HTTPException(status_code=403, detail="Setup has already been completed.")

    username = username.strip()
    if len(username) < 3:
        return _render_setup("Username must be at least 3 characters long.")
    if len(password) < 8:
        return _render_setup("Password must be at least 8 characters long.")
    if password != confirm_password:
        return _render_setup("Passwords do not match.")

    admin = AdminUser(username=username, password_hash=pwd_context.hash(password))
    db.add(admin)
    await db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.on_event("startup")
async def on_startup():
    print("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Έλεγχος αν υπάρχουν οι νέες στήλες στον πίνακα articles και προσθήκη τους αν λείπουν
        # Αυτό εξασφαλίζει ομαλή μετάβαση χωρίς την ανάγκη για manual migrations (Alembic κλπ)
        result = await conn.execute(text("PRAGMA table_info(articles)"))
        columns = [row[1] for row in result.fetchall()]
        
        # Προσθήκη στήλης quality_score αν δεν υπάρχει
        if "quality_score" not in columns:
            print("Adding quality_score column to articles table...")
            await conn.execute(text("ALTER TABLE articles ADD COLUMN quality_score FLOAT DEFAULT 1.0"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_articles_quality_score ON articles (quality_score)"))
            
        # Προσθήκη στήλης filter_flags αν δεν υπάρχει
        if "filter_flags" not in columns:
            print("Adding filter_flags column to articles table...")
            await conn.execute(text("ALTER TABLE articles ADD COLUMN filter_flags VARCHAR(500)"))
            
        # Προσθήκη στήλης is_filtered αν δεν υπάρχει
        if "is_filtered" not in columns:
            print("Adding is_filtered column to articles table...")
            await conn.execute(text("ALTER TABLE articles ADD COLUMN is_filtered BOOLEAN DEFAULT 0"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_articles_is_filtered ON articles (is_filtered)"))
    
    # Automatically seed default tech news feeds so the user has something to work with.
    # The seeder handles idempotency (won't duplicate if they already exist).
    print("Seeding default feeds...")
    from seeder import seed_database
    await seed_database()
    
    # Check if we have articles. If not, trigger an initial refresh in the background.
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(Article.id)))
        count = result.scalar_one()
        if count == 0:
            print("No articles found. Triggering initial background refresh...")
            from fetcher import update_all_feeds
            # Run in background to not block startup
            asyncio.create_task(update_all_feeds())
        else:
            print(f"Database ready with {count} articles.")

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
async def refresh_feeds(request: Request, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), admin: str = Depends(verify_admin)):
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
    quality_score: float
    filter_flags: Optional[str]

class PaginatedArticlesResponse(BaseModel):
    articles: List[ArticleResponse]
    has_next: bool
    total: int

@app.get("/api/articles", response_model=PaginatedArticlesResponse)
@limiter.limit("100/minute")
async def get_articles(request: Request, last_date: str = None, category_id: int = None, category_ids: str = None, feed_id: int = None, show_filtered: bool = False, db: AsyncSession = Depends(get_db)):
    per_page = 20
    
    query = select(Article, Feed).join(Feed, Article.feed_id == Feed.id).order_by(desc(Article.published), desc(Article.id))
    count_query = select(func.count(Article.id)).join(Feed, Article.feed_id == Feed.id)
    
    # Φιλτράρισμα χαμηλής ποιότητας άρθρων εκτός αν ζητηθεί διαφορετικά
    if not show_filtered:
        query = query.where(Article.is_filtered == False)
        count_query = count_query.where(Article.is_filtered == False)
    
    # Έλεγχος αν ζητήθηκε συγκεκριμένη κατηγορία ή πολλαπλές κατηγορίες (Archipelago stack)
    if category_id:
        query = query.where(Feed.category_id == category_id)
        count_query = count_query.where(Feed.category_id == category_id)
    elif category_ids:
        # Μετατροπή της συμβολοσειράς των IDs σε λίστα ακεραίων
        parsed_ids = []
        for item in category_ids.split(","):
            cleaned_val = item.strip()
            if cleaned_val.isdigit():
                parsed_ids.append(int(cleaned_val))
        
        # Εφαρμογή φιλτραρίσματος μόνο αν έχουμε έγκυρα IDs στη λίστα
        if parsed_ids:
            query = query.where(Feed.category_id.in_(parsed_ids))
            count_query = count_query.where(Feed.category_id.in_(parsed_ids))
            
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
            "is_read": art.is_read,
            "quality_score": art.quality_score if art.quality_score is not None else 1.0,
            "filter_flags": art.filter_flags,
        })
        
    return {
        "articles": articles,
        "has_next": len(articles) == per_page,
        "total": total_count
    }

@app.get("/api/stats/quality")
@limiter.limit("30/minute")
async def quality_stats(request: Request, db: AsyncSession = Depends(get_db)):
    """Στατιστικά ποιότητας / filtering — πόσα φιλτραρίστηκαν και γιατί."""
    # Σύνολο άρθρων
    total_res = await db.execute(select(func.count(Article.id)))
    total = total_res.scalar_one()

    # Φιλτραρισμένα άρθρα
    filtered_res = await db.execute(
        select(func.count(Article.id)).where(Article.is_filtered == True)
    )
    filtered = filtered_res.scalar_one()

    # Μέσος όρος quality score
    avg_res = await db.execute(select(func.avg(Article.quality_score)))
    avg_score = avg_res.scalar_one() or 0.0

    # Ανάλυση flags — ποια flags εμφανίζονται πιο συχνά
    flags_res = await db.execute(
        select(Article.filter_flags).where(Article.filter_flags != None)
    )
    flag_counts: dict[str, int] = {}
    for row in flags_res.all():
        if row[0]:
            for flag in row[0].split(","):
                flag = flag.strip()
                if flag:
                    flag_counts[flag] = flag_counts.get(flag, 0) + 1

    # Ταξινόμηση flags κατά συχνότητα (φθίνουσα)
    top_flags = sorted(flag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total_articles": total,
        "filtered_articles": filtered,
        "pass_rate": round((total - filtered) / total * 100, 1) if total > 0 else 100.0,
        "avg_quality_score": round(avg_score, 3),
        "top_flags": [{"flag": f, "count": c} for f, c in top_flags],
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
                # 1. Προσπάθεια άμεσης ανάκτησης με Googlebot User-Agent
                # Αυτό παρακάμπτει τα cookie walls στα περισσότερα ειδησεογραφικά site (Golem, Heise κλπ.)
                headers = {
                    "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
                }
                async with session.get(article.link, headers=headers, timeout=8) as resp:
                    resp_url_str = str(resp.url).lower()
                    
                    # Έλεγχος αν ανακατευθυνθήκαμε σε σελίδα συναίνεσης (cookie wall / zustimmung)
                    # Ή αν η απάντηση δεν είναι επιτυχής (π.χ. 403, 500)
                    is_consent_redirect = any(x in resp_url_str for x in ["/zustimmung", "consent", "cookie-consent", "cookie-wall", "agree"])
                    
                    if resp.status == 200 and not is_consent_redirect:
                        temp_html = await resp.text()
                        
                        # Επιπλέον έλεγχος περιεχομένου για Golem/Heise cookie walls αν ξεφύγουν από το url redirect
                        is_cookie_page = "willkommen auf golem.de" in temp_html.lower() or "pur-abo" in temp_html.lower()
                        
                        if not is_cookie_page:
                            html = temp_html
                        else:
                            print(f"Detected cookie wall in content for {article.link}, triggering translate fallback.")
                    else:
                        print(f"Direct fetch with Googlebot failed (status={resp.status}, redirect={resp_url_str}). Trying fallback...")

            # 2. Fallback: Ανάκτηση μέσω Google Translate proxy αν το Googlebot UA αποτύχει ή μπλοκαριστεί
            if html == (article.summary or ""):
                async with aiohttp.ClientSession(connector = aiohttp.TCPConnector(ssl = False)) as session:
                    # Χρήση browser headers για το Google Translate
                    browser_headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                    translate_url = f"https://translate.google.com/translate?sl=auto&tl=el&u={article.link}"
                    async with session.get(translate_url, headers=browser_headers, timeout=8) as resp:
                        if resp.status == 200:
                            html = await resp.text()
                            print(f"Successfully fetched article via Translate proxy: {article.link}")

            # 3. Fallback: Ανάκτηση μέσω curl αν οι προηγούμενες μέθοδοι απέτυχαν (π.χ. λόγω Cloudflare TLS fingerprinting)
            if html == ( article.summary or "" ):
                try:
                    # Επιλογή του κατάλληλου εκτελέσιμου ανάλογα με το λειτουργικό σύστημα
                    import platform
                    curl_bin = "curl.exe" if platform.system() == "Windows" else "curl"
                    
                    # Ορισμός των παραμέτρων της κλήσης
                    curl_cmd = [
                        curl_bin,
                        "-s",
                        "-L",
                        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        article.link
                    ]
                    
                    # Εκτέλεση του curl.exe ως ασύγχρονη διεργασία
                    proc = await asyncio.create_subprocess_exec(
                        *curl_cmd,
                        stdout = asyncio.subprocess.PIPE,
                        stderr = asyncio.subprocess.PIPE
                    )
                    
                    # Αναμονή για την ολοκλήρωση της διεργασίας με χρονικό όριο 8 δευτερολέπτων
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(),
                        timeout = 8.0
                    )
                    
                    # Έλεγχος αν η διεργασία ολοκληρώθηκε επιτυχώς
                    if proc.returncode == 0:
                        temp_html = stdout.decode( "utf-8", errors = "ignore" )
                        if temp_html.strip():
                            html = temp_html
                            print( f"Successfully fetched article via curl.exe: {article.link}" )
                except Exception as curl_error:
                    # Καταγραφή τυχόν σφάλματος κατά την εκτέλεση του curl
                    print( f"Error fetching via curl.exe: {curl_error}" )
        except Exception as e:
            print(f"Error fetching article content: {e}")
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
async def delete_feed(feed_id: int, db: AsyncSession = Depends(get_db), admin: str = Depends(verify_admin)):
    feed_res = await db.execute(select(Feed).where(Feed.id == feed_id))
    feed = feed_res.scalar_one_or_none()
    if feed:
        await db.delete(feed)
        await db.commit()
    return {"status": "success"}

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
async def add_feed(request: Request, feed: FeedCreate, db: AsyncSession = Depends(get_db), admin: str = Depends(verify_admin)):
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
