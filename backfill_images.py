import asyncio
import aiohttp
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import AsyncSessionLocal
from models import Article
from fetcher import fetch_og_image

# Ρύθμιση της κονσόλας σε UTF-8 για αποφυγή UnicodeEncodeError στα Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass

# Ορισμός ορίου ταυτόχρονων αιτημάτων για αποφυγή υπερφόρτωσης των διακομιστών
SEMAPHORE_LIMIT = 5

async def backfill_article(session: aiohttp.ClientSession, db_session: AsyncSession, article: Article, sem: asyncio.Semaphore) -> None:
    # Χρήση semaphore για τον περιορισμό των ταυτόχρονων συνδέσεων
    async with sem:
        # Ασφαλής εκτύπωση τίτλου άρθρου
        print(f"Processing: {article.title}")
        
        # Ανάκτηση της εικόνας Open Graph από το σύνδεσμο του άρθρου
        try:
            image_url = await fetch_og_image(session, article.link)
            
            if image_url:
                # Ενημέρωση της εγγραφής στη βάση δεδομένων εάν βρεθεί εικόνα
                article.image_url = image_url
                print(f"-> Found image: {image_url}")
            else:
                print(f"-> No image found for: {article.title}")
        except Exception as e:
            print(f"-> Error processing {article.title}: {e}")


async def main() -> None:
    # Δημιουργία ορίου ταυτόχρονων αιτημάτων
    sem = asyncio.Semaphore(SEMAPHORE_LIMIT)
    
    async with AsyncSessionLocal() as db_session:
        # Ανάκτηση όλων των άρθρων από τη βάση δεδομένων που δεν έχουν εικόνα εξωφύλλου
        stmt = select(Article).where((Article.image_url == None) | (Article.image_url == ""))
        result = await db_session.execute(stmt)
        articles = result.scalars().all()
        
        # Έλεγχος εάν υπάρχουν άρθρα προς ενημέρωση
        if not articles:
            print("No articles found without an image cover.")
            return
            
        print(f"Found {len(articles)} articles needing image backfill.")
        
        # Έναρξη συνεδρίας aiohttp για την ανάκτηση των σελίδων
        async with aiohttp.ClientSession() as session:
            tasks = [
                backfill_article(session, db_session, article, sem)
                for article in articles
            ]
            # Εκτέλεση όλων των εργασιών παράλληλα
            await asyncio.gather(*tasks)
            
        # Αποθήκευση των αλλαγών στη βάση δεδομένων
        await db_session.commit()
        print("Backfill complete and committed successfully!")


if __name__ == "__main__":
    # Εκτέλεση της κύριας ασύγχρονης συνάρτησης
    asyncio.run(main())
