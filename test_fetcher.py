import unittest
import aiohttp
from unittest.mock import AsyncMock, MagicMock
from fetcher import fetch_og_image, clean_translated_url


class TestCleanTranslatedUrl(unittest.TestCase):
    """Δοκιμές για τη συνάρτηση clean_translated_url."""

    # Δοκιμή: URL που περνάει μέσω translate.goog πρέπει να επιστρέψει στο αρχικό domain
    def test_translate_goog_url_cleaned(self) -> None:
        translated = (
            "https://www-aek365-org.translate.goog/a-123/article.htm"
            "?_x_tr_sl=auto&_x_tr_tl=el&_x_tr_hl=de"
        )
        original = "https://www.aek365.org"
        result = clean_translated_url(translated, original)
        self.assertEqual(result, "https://www.aek365.org/a-123/article.htm")

    # Δοκιμή: URL χωρίς translate.goog πρέπει να μείνει αμετάβλητο
    def test_non_translate_url_unchanged(self) -> None:
        url = "https://example.com/article/123"
        result = clean_translated_url(url, "https://example.com")
        self.assertEqual(result, url)

    # Δοκιμή: κενό URL πρέπει να επιστραφεί ως έχει
    def test_empty_url_returns_empty(self) -> None:
        self.assertEqual(clean_translated_url("", "https://example.com"), "")

    # Δοκιμή: αρχικό domain χωρίς scheme πρέπει να δουλεύει
    def test_original_domain_without_scheme(self) -> None:
        translated = (
            "https://www-example-com.translate.goog/path"
            "?_x_tr_sl=auto&_x_tr_tl=el"
        )
        result = clean_translated_url(translated, "www.example.com")
        self.assertEqual(result, "https://www.example.com/path")

    # Δοκιμή: query params που δεν είναι _x_tr_* πρέπει να διατηρηθούν
    def test_preserves_non_translate_query_params(self) -> None:
        translated = (
            "https://www-example-com.translate.goog/page"
            "?id=42&_x_tr_sl=auto&_x_tr_tl=el"
        )
        result = clean_translated_url(translated, "https://www.example.com")
        self.assertEqual(result, "https://www.example.com/page?id=42")

    # Δοκιμή edge case: None URL
    def test_none_url_returns_none(self) -> None:
        self.assertIsNone(clean_translated_url(None, "https://example.com"))


class TestFetcherImageExtraction(unittest.IsolatedAsyncioTestCase):

    # Δοκιμή επιτυχούς ανάκτησης εικόνας Open Graph από HTML
    async def test_fetch_og_image_success(self) -> None:
        # Δημιουργία ψευδούς (mock) απάντησης με ετικέτα og:image
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.url = "https://example.com/article"
        mock_response.text = AsyncMock(return_value = "<html><head><meta property=\"og:image\" content=\"https://example.com/cover.jpg\"></head></html>")
        
        # Δημιουργία ψευδούς (mock) συνεδρίας aiohttp ClientSession
        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        # Κλήση της συνάρτησης προς δοκιμή
        result = await fetch_og_image(mock_session, "https://example.com/article")
        
        # Επιβεβαίωση ότι η σωστή διεύθυνση εικόνας επιστράφηκε
        self.assertEqual(result, "https://example.com/cover.jpg")


    # Δοκιμή περίπτωσης αποτυχίας (π.χ. απουσία ετικέτας og:image)
    async def test_fetch_og_image_failure_or_missing(self) -> None:
        # Δημιουργία ψευδούς απάντησης χωρίς καμία εικόνα
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.url = "https://example.com/article"
        mock_response.text = AsyncMock(return_value = "<html><head></head><body>No images here</body></html>")
        
        # Δημιουργία ψευδούς (mock) συνεδρίας aiohttp ClientSession
        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        # Κλήση της συνάρτησης για σελίδα χωρίς εικόνα
        result = await fetch_og_image(mock_session, "https://example.com/article")
        
        # Επιβεβαίωση ότι η συνάρτηση επιστρέφει None
        self.assertIsNone(result)


# Παράδειγμα χρήσης 10-20 γραμμών
async def run_example() -> None:
    # Παράδειγμα εκτέλεσης της ανάκτησης εικόνας
    async with aiohttp.ClientSession(connector = aiohttp.TCPConnector(ssl = False)) as session:
        img = await fetch_og_image(session, "https://www.theverge.com")
        print(f"Example run image: {img}")


if __name__ == "__main__":
    unittest.main()
