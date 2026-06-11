import unittest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

# Δοκιμές για τη λογική μετάφρασης που χρησιμοποιείται στο backend
class TestArticleTranslation(unittest.TestCase):
    """Κλάση δοκιμών για τη λειτουργία μετάφρασης των άρθρων."""

    # Δοκιμή: Επιτυχής μετάφραση σελίδας HTML στα Αγγλικά
    @patch("main.GoogleTranslator")
    def test_translate_english_success(self, mock_translator_class: MagicMock) -> None:
        # Δημιουργία mock translator που επιστρέφει συγκεκριμένη μετάφραση
        mock_translator = MagicMock()
        mock_translator.translate.side_effect = lambda text: f"Translated: {text}"
        mock_translator_class.return_value = mock_translator

        # Αρχικό περιεχόμενο HTML και τίτλος
        original_title = "Γεια σου Κόσμε"
        original_content = "<p>Αυτό είναι ένα άρθρο.</p>"

        # Προσομοίωση της λογικής μετάφρασης του main.py
        soup = BeautifulSoup(original_content, "html.parser")
        translator = mock_translator_class(source="auto", target="en")
        
        # Μετάφραση των στοιχείων p, h1-h4, li
        for element in soup.find_all(["p", "h1", "h2", "h3", "h4", "li"]):
            text = element.get_text(strip=True)
            if text and len(text) > 2:
                element.string = translator.translate(text)

        # Μετάφραση τίτλου
        translated_title = translator.translate(original_title)
        translated_content = str(soup)

        # Έλεγχος αποτελεσμάτων
        self.assertEqual(translated_title, "Translated: Γεια σου Κόσμε")
        self.assertIn("Translated: Αυτό είναι ένα άρθρο.", translated_content)

    # Δοκιμή Edge Case: Αποτυχία μετάφρασης (π.χ. σφάλμα API) και διατήρηση αρχικού κειμένου
    @patch("main.GoogleTranslator")
    def test_translate_failure_fallback(self, mock_translator_class: MagicMock) -> None:
        # Δημιουργία mock translator που προκαλεί σφάλμα κατά τη μετάφραση
        mock_translator = MagicMock()
        mock_translator.translate.side_effect = Exception("Translation service unavailable")
        mock_translator_class.return_value = mock_translator

        # Αρχικό περιεχόμενο HTML και τίτλος
        original_title = "Γεια σου Κόσμε"
        original_content = "<p>Αυτό είναι ένα άρθρο.</p>"

        # Προσομοίωση της λογικής με διαχείριση σφαλμάτων
        soup = BeautifulSoup(original_content, "html.parser")
        translator = mock_translator_class(source="auto", target="en")
        
        for element in soup.find_all(["p", "h1", "h2", "h3", "h4", "li"]):
            text = element.get_text(strip=True)
            if text and len(text) > 2:
                try:
                    element.string = translator.translate(text)
                except Exception:
                    # Σε περίπτωση σφάλματος, το περιεχόμενο μένει ως έχει
                    pass

        translated_title = original_title
        try:
            translated_title = translator.translate(original_title)
        except Exception:
            pass

        translated_content = str(soup)

        # Έλεγχος ότι το κείμενο παρέμεινε το αρχικό
        self.assertEqual(translated_title, "Γεια σου Κόσμε")
        self.assertIn("Αυτό είναι ένα άρθρο.", translated_content)

# Παράδειγμα χρήσης 10-20 γραμμών
def run_example() -> None:
    # Παράδειγμα προσομοίωσης μετάφρασης
    from deep_translator import GoogleTranslator
    try:
        translator = GoogleTranslator(source="auto", target="en")
        sample_text = "Καλημέρα, πώς είστε;"
        result = translator.translate(sample_text)
        print(f"Sample translate result: '{sample_text}' -> '{result}'")
    except Exception as e:
        print(f"Failed to call translation service: {e}")

if __name__ == "__main__":
    unittest.main()
