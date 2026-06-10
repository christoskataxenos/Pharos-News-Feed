import asyncio
from sqlalchemy.future import select
from models import Category, Feed
from database import AsyncSessionLocal, Base, engine

SEEDS = {
    "Tech News": [
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("Wired", "https://www.wired.com/feed/rss"),
        ("Ars Technica", "http://feeds.arstechnica.com/arstechnica/index"),
        ("TechCrunch", "https://techcrunch.com/feed/"),
    ],
    "Greek Tech": [
        ("PCSteps", "https://www.pcsteps.gr/feed/"),
        ("Techblog", "https://feeds.feedburner.com/techblogGR"),
        ("Unboxholics News", "https://unboxholics.com/news?format=rss"),
    ],
    "Programming": [
        ("Hacker News", "https://news.ycombinator.com/rss"),
        ("CSS-Tricks", "https://css-tricks.com/feed/"),
        ("Dev.to", "https://dev.to/feed"),
    ],
    "Awesome Tech RSS": [
        ("GitHub Blog", "https://github.blog/feed/"),
        ("Netflix Tech", "https://netflixtechblog.com/feed"),
        ("Uber Engineering", "https://eng.uber.com/feed/"),
        ("Discord Blog", "https://discord.com/blog/rss.xml"),
    ]
}

async def seed_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as session:
        for cat_name, feeds in SEEDS.items():
            stmt = select(Category).where(Category.name == cat_name)
            result = await session.execute(stmt)
            category = result.scalar_one_or_none()
            
            if not category:
                category = Category(name=cat_name)
                session.add(category)
                await session.flush()
                print(f"Created Category: {cat_name}")
            
            for title, url in feeds:
                stmt_feed = select(Feed).where(Feed.url == url)
                res_feed = await session.execute(stmt_feed)
                feed = res_feed.scalar_one_or_none()
                
                if not feed:
                    feed_type = 'video' if 'youtube.com' in url else 'article'
                    feed = Feed(title=title, url=url, category_id=category.id, type=feed_type)
                    session.add(feed)
                    print(f"Added Feed: {title}")
        
        await session.commit()
        print("Database seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_database())
