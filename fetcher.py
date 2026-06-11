import asyncio
import aiohttp
import feedparser
from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Feed, Article
from filters import score_article, QUALITY_THRESHOLD

# Κεφαλίδες HTTP που μιμούνται πραγματικό browser για αποφυγή μπλοκαρίσματος
_BROWSER_HEADERS: dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def clean_translated_url(url: str, original_domain: str) -> str:
    """Μετατρέπει URL από τo Google Translate proxy πίσω στο αρχικό domain.

    Αν το URL περιέχει 'translate.goog', αντικαθιστά το host με
    το αρχικό domain και αφαιρεί τις παραμέτρους _x_tr_*.
    """
    if not url:
        return url
    if "translate.goog" not in url:
        return url

    parsed = urlparse(url)
    # Αφαίρεση παραμέτρων Google Translate (_x_tr_sl, _x_tr_tl, _x_tr_hl κτλ.)
    clean_params = [(k, v) for k, v in parse_qsl(parsed.query) if not k.startswith("_x_tr_")]
    new_query = urlencode(clean_params)

    # Ανακατασκευή του URL με τo αρχικό domain
    original_parsed = urlparse(original_domain if "://" in original_domain else f"https://{original_domain}")
    return urlunparse((
        original_parsed.scheme,
        original_parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment,
    ))


async def _fetch_html_with_fallback(
    session: aiohttp.ClientSession,
    url: str,
    timeout: int = 10,
) -> tuple[str | None, str]:
    """Προσπαθεί να φέρει HTML απευθείας· αν αποτύχει (403 / exception),
    χρησιμοποιεί Google Translate ως proxy fallback.

    Επιστρέφει (html, response_base_url) — το response_base_url χρησιμεύει
    για σωστό urljoin σχετικών συνδέσμων.
    """
    html: str | None = None
    response_base_url: str = url

    # Πρώτη προσπάθεια: απευθείας σύνδεση
    try:
        async with session.get(url, headers=_BROWSER_HEADERS, timeout=timeout) as resp:
            if resp.status == 200:
                html = await resp.text()
                response_base_url = str(resp.url)
            elif resp.status == 403:
                print(f"Direct fetch returned 403 for {url}, trying translate proxy.")
    except Exception as e:
        print(f"Direct fetch failed for {url}: {e}")

    # Fallback: Google Translate proxy
    if html is None:
        translate_url = f"https://translate.google.com/translate?sl=auto&tl=el&u={url}"
        try:
            async with session.get(translate_url, headers=_BROWSER_HEADERS, timeout=timeout) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    response_base_url = str(resp.url)
                    print(f"Fetched via translate proxy: {url}")
        except Exception as e:
            print(f"Translate proxy also failed for {url}: {e}")

    return html, response_base_url

def parse_date(date_str: str | None) -> datetime:
    """Αναλύει ημερομηνία από RSS feed string σε datetime αντικείμενο."""
    if not date_str:
        return datetime.utcnow()
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo:
            dt = dt.replace(tzinfo=None)
        return dt
    except Exception:
        return datetime.utcnow()


def is_valid_image(url: str | None) -> bool:
    """Ελέγχει αν ένα URL εικόνας είναι έγκυρο (αποκλείει favicons, trackers κτλ.)."""
    if not url: return False
    lower_url = url.lower()
    bad_keywords = ['favicon', 'avatar', 'gravatar', 'pixel', 'tracker', 'logo', 'button', 'badge']
    if any(kw in lower_url for kw in bad_keywords):
        return False
    # Avoid 1x1 gifs often used for tracking
    if url.endswith('.gif') and '1x1' in lower_url:
        return False
    return True

def extract_image(entry):
    if 'media_content' in entry:
        media = entry.media_content
        if media and isinstance(media, list) and len(media) > 0:
            if media[0].get('type', '').startswith('image/'):
                url = media[0].get('url')
                if is_valid_image(url): return url
                
    if 'media_thumbnail' in entry:
        thumbs = entry.media_thumbnail
        if thumbs and isinstance(thumbs, list) and len(thumbs) > 0:
            url = thumbs[0].get('url')
            if is_valid_image(url): return url
            
    if 'enclosures' in entry:
        for enc in entry.enclosures:
            if enc.get('type', '').startswith('image/'):
                url = enc.get('href')
                if is_valid_image(url): return url

    content = entry.get('summary', entry.get('description', ''))
    if content:
        soup = BeautifulSoup(content, 'html.parser')
        # Find all images and take the first valid one
        for img in soup.find_all('img'):
            url = img.get('src')
            if is_valid_image(url):
                # Extra check: if width/height attributes exist and are tiny, skip it
                w = img.get('width')
                h = img.get('height')
                try:
                    if w and int(w) < 50: continue
                    if h and int(h) < 50: continue
                except:
                    pass
                return url
            
    # Έλεγχος εναλλακτικού πεδίου content (συνήθως content:encoded) για εικόνες
    if "content" in entry:
        for c in entry.content:
            value = c.get("value", "")
            if value:
                soup = BeautifulSoup(value, "html.parser")
                for img in soup.find_all("img"):
                    url = img.get("src")
                    if is_valid_image(url):
                        return url
            
    return None


async def fetch_og_image(session: aiohttp.ClientSession, url: str) -> str | None:
    """Ανακτά OG/Twitter εικόνα από σελίδα άρθρου.

    Αν η άμεση σύνδεση αποτύχει (403 Cloudflare κτλ.), δοκιμάζει
    μέσω Google Translate proxy και καθαρίζει τα URL πίσω στο αρχικό domain.
    """
    # Επιστρέφει None εάν η διεύθυνση URL είναι κενή
    if not url:
        return None

    # Ανάκτηση HTML με fallback στον translate proxy
    html, response_base_url = await _fetch_html_with_fallback(session, url, timeout=5)
    if not html:
        return None

    # Καθορισμός αρχικού domain για καθαρισμό translate URLs
    original_domain = url

    try:
        soup = BeautifulSoup(html, "html.parser")

        # Αναζήτηση εικόνας Open Graph (og:image)
        og_img = soup.find("meta", attrs={"property": "og:image"}) or soup.find("meta", attrs={"name": "og:image"})
        if og_img and og_img.get("content"):
            img_url = og_img.get("content")
            # Μετατροπή σχετικού URL σε απόλυτο εάν χρειάζεται
            img_url = urljoin(response_base_url, img_url)
            img_url = clean_translated_url(img_url, original_domain)
            if is_valid_image(img_url):
                return img_url

        # Εναλλακτική αναζήτηση εικόνας Twitter (twitter:image)
        tw_img = soup.find("meta", attrs={"name": "twitter:image"}) or soup.find("meta", attrs={"property": "twitter:image"})
        if tw_img and tw_img.get("content"):
            img_url = tw_img.get("content")
            img_url = urljoin(response_base_url, img_url)
            img_url = clean_translated_url(img_url, original_domain)
            if is_valid_image(img_url):
                return img_url

        # Αναζήτηση τυπικού συνδέσμου image_src
        link_img = soup.find("link", rel="image_src")
        if link_img and link_img.get("href"):
            img_url = link_img.get("href")
            img_url = urljoin(response_base_url, img_url)
            img_url = clean_translated_url(img_url, original_domain)
            if is_valid_image(img_url):
                return img_url

        # Αναζήτηση της πρώτης μεγάλης εικόνας στο κείμενο του άρθρου ως έσχατη λύση
        for img in soup.find_all("img"):
            src = img.get("src")
            if src:
                # Έλεγχος διαστάσεων για αποφυγή μικρών εικονιδίων
                w = img.get("width")
                h = img.get("height")
                try:
                    if w and int(w) < 100:
                        continue
                    if h and int(h) < 100:
                        continue
                except Exception:
                    pass

                img_url = urljoin(response_base_url, src)
                img_url = clean_translated_url(img_url, original_domain)
                if is_valid_image(img_url):
                    return img_url
    except Exception as e:
        # Καταγραφή τυχόν σφαλμάτων κατά την ανάκτηση της εικόνας
        print(f"Error parsing OG image for {url}: {e}")

    return None

async def fetch_feed_xml(session: aiohttp.ClientSession, url: str) -> str | None:
    """Κατεβάζει XML δεδομένα από RSS/Atom feed URL."""
    # Κανονικοποίηση της διεύθυνσης URL αν λείπει το σχήμα http/https
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    headers = {"User-Agent": "FeedFlow-V2 (async)"}
    try:
        async with session.get(url, headers=headers, timeout=15) as response:
            if response.status == 200:
                return await response.text()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

async def process_scrape_feed(
    session: aiohttp.ClientSession,
    db_session: AsyncSession,
    feed: Feed,
) -> int:
    """Κάνει scrape μια ιστοσελίδα για άρθρα.

    Αν η άμεση σύνδεση αποτύχει (π.χ. Cloudflare 403), δοκιμάζει
    μέσω Google Translate proxy και καθαρίζει τα URL.
    """
    # Κανονικοποίηση της διεύθυνσης URL για το scrape
    url = feed.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Ανάκτηση HTML με fallback στον translate proxy
    html, response_base_url = await _fetch_html_with_fallback(session, url, timeout=15)
    if not html:
        return 0

    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(url).netloc

    new_articles_count = 0
    seen_links: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Κατασκευή πλήρους URL χρησιμοποιώντας το response base URL
        full_url = urljoin(response_base_url, href)
        # Καθαρισμός translate proxy URL πίσω στο αρχικό domain
        full_url = clean_translated_url(full_url, url)
        parsed_url = urlparse(full_url)

        # Φίλτρο: μόνο links από το ίδιο domain
        if parsed_url.netloc != base_domain:
            continue

        # Φίλτρο: ελάχιστο μήκος path (αποφυγή αρχικών σελίδων / μενού)
        if len(parsed_url.path) < 20:
            continue

        # Φίλτρο: αποκλεισμός σελίδων κατηγοριών, tags, συγγραφέων κτλ.
        if any(x in parsed_url.path.lower() for x in ["/category/", "/tag/", "/author/", "/about", "/contact", "/login"]):
            continue

        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        title = a.get_text(strip=True)
        if not title:
            img = a.find("img")
            if img and img.get("alt"):
                title = img.get("alt").strip()

        # Φίλτρο: ελάχιστο μήκος τίτλου
        if len(title) < 15:
            continue

        # Έλεγχος αν το άρθρο υπάρχει ήδη στη βάση
        stmt = select(Article).where(Article.link == full_url)
        result = await db_session.execute(stmt)
        if result.scalar_one_or_none():
            continue

        # Ανάκτηση εικόνας (με αυτόματο fallback)
        image_url = await fetch_og_image(session, full_url)

        # Βαθμολόγηση ποιότητας scraped άρθρου
        quality_score, flags = score_article(
            title=title[:255],
            summary="Web scraped article",
            feed_title=feed.title,
        )
        is_filtered = quality_score < QUALITY_THRESHOLD

        article = Article(
            feed_id=feed.id,
            title=title[:255],
            link=full_url,
            published=datetime.utcnow(),
            summary="Web scraped article",
            image_url=image_url,
            quality_score=quality_score,
            filter_flags=",".join(flags) if flags else None,
            is_filtered=is_filtered,
        )
        db_session.add(article)
        new_articles_count += 1

        if new_articles_count >= 15:
            break

    await db_session.commit()
    return new_articles_count

async def process_feed(
    session: aiohttp.ClientSession,
    db_session: AsyncSession,
    feed: Feed,
) -> int:
    """Επεξεργάζεται ένα feed (RSS ή scrape) και προσθέτει νέα άρθρα."""
    # Μην τραβάμε νέα δεδομένα αν περάσαν λιγότερο από 15 λεπτά (cooldown / buffer)
    if feed.last_fetched and datetime.utcnow() - feed.last_fetched < timedelta(minutes=15):
        return 0

    if feed.type == 'scrape':
        new_count = await process_scrape_feed(session, db_session, feed)
    else:
        xml_data = await fetch_feed_xml(session, feed.url)
        if not xml_data:
            new_count = 0
        else:
            parsed = feedparser.parse(xml_data)
            new_count = 0
            
            # 10 Days Buffer for all feeds
            min_date = datetime.utcnow() - timedelta(days=10)

            # Ανάκτηση πρόσφατων τίτλων (48 ώρες) για fuzzy duplicate detection
            dedup_cutoff = datetime.utcnow() - timedelta(hours=48)
            recent_stmt = select(Article.title).where(Article.published >= dedup_cutoff)
            recent_result = await db_session.execute(recent_stmt)
            recent_titles = [row[0] for row in recent_result.all()]

            # Process up to 100 entries per feed to fill the buffer
            for entry in parsed.entries[:100]:
                # Check if exists
                stmt = select(Article).where(Article.link == entry.link)
                result = await db_session.execute(stmt)
                if result.scalar_one_or_none():
                    continue
                    
                published = parse_date(entry.get('published', entry.get('updated')))
                
                if min_date and published < min_date:
                    continue

                if feed.type == 'video' and 'shorts' in entry.title.lower():
                    continue

                image_url = extract_image(entry)
                
                # Εάν δεν βρέθηκε εικόνα στο RSS feed, δοκιμάζουμε να την ανακτήσουμε από τη σελίδα του άρθρου
                if not image_url:
                    image_url = await fetch_og_image(session, entry.link)
                
                summary = entry.get('summary', entry.get('description', ''))
                # Strip html tags for cleaner DB if desired, but keep simple for now
                if summary:
                    soup = BeautifulSoup(summary, 'html.parser')
                    summary = soup.get_text()[:500] + "..." if len(soup.get_text()) > 500 else soup.get_text()
                
                # Βαθμολόγηση ποιότητας άρθρου πριν την αποθήκευση
                quality_score, flags = score_article(
                    title=entry.title,
                    summary=summary,
                    feed_title=feed.title,
                    recent_titles=recent_titles,
                )
                is_filtered = quality_score < QUALITY_THRESHOLD

                article = Article(
                    feed_id=feed.id,
                    title=entry.title,
                    link=entry.link,
                    published=published,
                    summary=summary,
                    image_url=image_url,
                    quality_score=quality_score,
                    filter_flags=",".join(flags) if flags else None,
                    is_filtered=is_filtered,
                )
                db_session.add(article)
                new_count += 1

                # Προσθήκη νέου τίτλου στη λίστα dedup για τα επόμενα entries
                recent_titles.append(entry.title)
                
    # Update last fetched timestamp
    feed.last_fetched = datetime.utcnow()
    await db_session.commit()
    return new_count



async def update_all_feeds(db_session: AsyncSession | None = None) -> int:
    from database import AsyncSessionLocal
    
    async def process_single_feed(feed_id: int):
        async with AsyncSessionLocal() as session_to_use:
            feed_res = await session_to_use.execute(select(Feed).where(Feed.id == feed_id))
            feed = feed_res.scalar_one_or_none()
            if not feed: return 0
            
            # Start HTTP session inside for isolated requests, or pass one if preferred.
            # aiohttp handles session creation relatively fast, or we could pass it.
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as http_session:
                try:
                    res = await process_feed(http_session, session_to_use, feed)
                    return res
                except Exception as e:
                    print(f"Error processing feed {feed.title}: {e}")
                    return 0

    async def _do_update(session_to_use):
        stmt = select(Feed)
        result = await session_to_use.execute(stmt)
        feeds = result.scalars().all()
        feed_ids = [f.id for f in feeds]
        
        # Semaphore limits parallel fetching to 5 to avoid overwhelming the network or DB
        sem = asyncio.Semaphore(5)
        
        async def bounded_process(f_id):
            async with sem:
                return await process_single_feed(f_id)
                
        tasks = [bounded_process(f_id) for f_id in feed_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_new = sum(r for r in results if isinstance(r, int))
        print(f"Update complete! Added {total_new} new articles.")
        return total_new

    if db_session is None:
        async with AsyncSessionLocal() as new_session:
            return await _do_update(new_session)
    else:
        return await _do_update(db_session)

