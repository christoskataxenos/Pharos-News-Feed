import asyncio
import sys
from sqlalchemy.future import select
from database import AsyncSessionLocal
from models import Article
from filters import score_article, QUALITY_THRESHOLD

# Ρύθμιση της κονσόλας σε UTF-8 για αποφυγή UnicodeEncodeError στα Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Μέγεθος batch για ενημέρωση βάσης (αποφυγή υπερβολικών commits)
BATCH_SIZE = 100


async def main() -> None:
    """Εφαρμόζει quality scoring σε όλα τα υπάρχοντα άρθρα στη βάση.

    Τρέχει σε batches των BATCH_SIZE για αποδοτικότητα.
    Πολυπλοκότητα: O(n * m) όπου n = αριθμός άρθρων, m = αριθμός patterns.
    """
    async with AsyncSessionLocal() as db_session:
        # Ανάκτηση όλων των άρθρων χωρίς quality score (ή με default 1.0)
        stmt = select(Article).where(
            (Article.quality_score == None) | (Article.quality_score == 1.0)
        )
        result = await db_session.execute(stmt)
        articles = result.scalars().all()

        if not articles:
            print("Δεν βρέθηκαν άρθρα προς βαθμολόγηση.")
            return

        total = len(articles)
        print(f"Βρέθηκαν {total} άρθρα προς βαθμολόγηση ποιότητας.")

        # Συλλογή πρόσφατων τίτλων για fuzzy duplicate detection
        all_titles: list[str] = [a.title for a in articles]

        filtered_count = 0
        processed = 0

        for article in articles:
            # Βαθμολόγηση ποιότητας
            quality_score, flags = score_article(
                title=article.title,
                summary=article.summary,
                recent_titles=all_titles,
            )

            # Ενημέρωση πεδίων
            article.quality_score = quality_score
            article.filter_flags = ",".join(flags) if flags else None
            article.is_filtered = quality_score < QUALITY_THRESHOLD

            if article.is_filtered:
                filtered_count += 1

            processed += 1

            # Εκτύπωση προόδου κάθε BATCH_SIZE εγγραφές
            if processed % BATCH_SIZE == 0:
                await db_session.commit()
                pct = round(processed / total * 100)
                print(f"  [{pct}%] {processed}/{total} — φιλτραρισμένα: {filtered_count}")

        # Τελικό commit για τα εναπομείναντα
        await db_session.commit()

        # Εκτύπωση αποτελεσμάτων
        print(f"\nΟλοκλήρωση! Βαθμολογήθηκαν {total} άρθρα:")
        print(f"  ✅ Πέρασαν: {total - filtered_count}")
        print(f"  ❌ Φιλτραρίστηκαν: {filtered_count}")
        print(f"  📊 Pass rate: {round((total - filtered_count) / total * 100, 1)}%")


if __name__ == "__main__":
    asyncio.run(main())
