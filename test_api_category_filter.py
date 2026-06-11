import unittest
from unittest.mock import MagicMock, AsyncMock
from starlette.requests import Request
from main import get_articles

class TestApiCategoryFilter(unittest.IsolatedAsyncioTestCase):
    """Κλάση δοκιμών για το φιλτράρισμα άρθρων με πολλαπλές κατηγορίες (Archipelagos)."""

    def _create_mock_request(self) -> Request:
        # Δημιουργία έγκυρου Request αντικειμένου της Starlette με βασικό scope
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/articles",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 12345)
        }
        return Request(scope)

    # Δοκιμή: Επιτυχής φιλτράρισμα άρθρων με category_ids (π.χ. "1,2,3")
    async def test_get_articles_with_multiple_category_ids_success(self) -> None:
        # Προετοιμασία mock για τη βάση δεδομένων και τα αποτελέσματα
        mock_session = AsyncMock()
        
        # Mocking του return value της εκτέλεσης των queries (select άρθρων)
        mock_result = MagicMock()
        mock_result.all.return_value = []  # Επιστρέφει κενή λίστα άρθρων
        
        # Mocking της εκτέλεσης του count query
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0
        
        # Σύνδεση των mock εκτελέσεων με τη σειρά
        mock_session.execute.side_effect = [mock_result, mock_count_result]
        
        # Εκτέλεση της συνάρτησης get_articles άμεσα ως async
        response = await get_articles(
            request=self._create_mock_request(),
            category_ids="1,2,3",
            db=mock_session
        )
        
        # Έλεγχος ότι η απάντηση περιέχει τα σωστά κλειδιά και τιμές
        self.assertIn("articles", response)
        self.assertEqual(len(response["articles"]), 0)
        self.assertEqual(response["total"], 0)

    # Δοκιμή Edge Case: Malformed/Invalid category_ids (π.χ. "abc,def")
    async def test_get_articles_with_invalid_category_ids_fallback(self) -> None:
        # Προετοιμασία mock
        mock_session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0
        
        mock_session.execute.side_effect = [mock_result, mock_count_result]
        
        # Εκτέλεση με μη έγκυρα IDs
        response = await get_articles(
            request=self._create_mock_request(),
            category_ids="abc,def",
            db=mock_session
        )
        
        # Έλεγχος ότι η συνάρτηση διαχειρίστηκε τα μη έγκυρα IDs και επέστρεψε κενά άρθρα
        self.assertIn("articles", response)
        self.assertEqual(len(response["articles"]), 0)

# Παράδειγμα χρήσης 10-20 γραμμών
def run_example() -> None:
    # Παράδειγμα άμεσης async κλήσης της get_articles
    import asyncio
    from unittest.mock import AsyncMock, MagicMock
    from starlette.requests import Request
    from main import get_articles

    async def main_example():
        mock_session = AsyncMock()
        mock_res = MagicMock()
        mock_res.all.return_value = []
        mock_count = MagicMock()
        mock_count.scalar_one.return_value = 0
        mock_session.execute.side_effect = [mock_res, mock_count]
        
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/articles",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 12345)
        }
        req = Request(scope)
        
        # Κλήση με category_ids
        res = await get_articles(
            request=req,
            category_ids="1,2",
            db=mock_session
        )
        print(f"Direct Async Call Success. Total: {res['total']}")
        
    asyncio.run(main_example())

if __name__ == "__main__":
    unittest.main()
