import re
import unicodedata
from typing import Optional


# =====================================================================
# Λίστα clickbait φράσεων / μοτίβων — εύκολα επεκτάσιμη
# =====================================================================
CLICKBAIT_PHRASES: list[str] = [
    "you won't believe",
    "you won\u2019t believe",
    "what happens next",
    "shocking",
    "mind-blowing",
    "mind blowing",
    "jaw-dropping",
    "jaw dropping",
    "game-changer",
    "game changer",
    "this one trick",
    "doctors hate",
    "scientists are baffled",
    "will blow your mind",
    "is breaking the internet",
    "gone wrong",
    "gone viral",
    "you need to see",
    "you have to see",
    "can't stop watching",
    "the truth about",
    "what they don't want you to know",
    "exposed",
    "is dead",
    "just changed everything",
    "won't last long",
    "before it's too late",
    "act now",
    "limited time",
    "secret revealed",
    "insane",
    "unbelievable",
    "breaking:",
    "just in:",
    "urgent:",
    "alert:",
    "wait until you see",
    "number \\d+ will shock",
    "top \\d+ reasons",
]

# =====================================================================
# Λίστα AI slop φράσεων — τυπικές εξόδοι ChatGPT / LLM
# =====================================================================
AI_SLOP_PHRASES: list[str] = [
    "in today's rapidly evolving",
    "in today's digital landscape",
    "in today's fast-paced world",
    "in the ever-changing landscape",
    "in the ever-evolving",
    "it's important to note",
    "it is important to note",
    "it's worth noting",
    "it is worth noting",
    "let's dive in",
    "let's delve into",
    "let's explore",
    "dive deep into",
    "in this comprehensive guide",
    "this comprehensive guide",
    "this article explores",
    "this article delves",
    "unlock the power",
    "unlock the potential",
    "unlock the secrets",
    "harness the power",
    "navigate the complexities",
    "navigate the landscape",
    "at the end of the day",
    "it goes without saying",
    "without further ado",
    "in conclusion",
    "to sum it up",
    "the bottom line is",
    "paradigm shift",
    "leverage cutting-edge",
    "cutting-edge technology",
    "groundbreaking approach",
    "revolutionize the way",
    "revolutionizing the",
    "game-changing solution",
    "holistic approach",
    "seamlessly integrate",
    "robust solution",
    "robust and scalable",
    "tapestry of",
    "delve into the",
    "embark on a journey",
    "realm of possibilities",
    "foster innovation",
    "foster collaboration",
    "spearheading",
    "underscores the importance",
    "a testament to",
    "poised to revolutionize",
    "reshaping the future",
    "stands as a beacon",
]

# =====================================================================
# Κατώφλι ποιότητας — Άρθρα κάτω από αυτό μαρκάρονται ως filtered
# =====================================================================
QUALITY_THRESHOLD: float = 0.3


# =====================================================================
# Βοηθητικές συναρτήσεις
# =====================================================================

def _count_uppercase_ratio(text: str) -> float:
    """Υπολογίζει το ποσοστό κεφαλαίων γραμμάτων στο κείμενο.

    Αγνοεί μη-αλφαβητικούς χαρακτήρες. Επιστρέφει 0.0 αν δεν
    υπάρχουν γράμματα.

    Πολυπλοκότητα: O(n) όπου n = μήκος κειμένου.
    """
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    upper_count = sum(1 for c in letters if c.isupper())
    return upper_count / len(letters)


def _count_emoji(text: str) -> int:
    """Μετράει τον αριθμό emoji / σύμβολων στο κείμενο.

    Χρησιμοποιεί Unicode κατηγορία 'So' (Symbol, other)
    που καλύπτει τα περισσότερα emoji.
    """
    count = 0
    for char in text:
        # So = Symbol, other — covers most emoji
        if unicodedata.category(char) == "So":
            count += 1
    return count


# =====================================================================
# Layer 1: Clickbait Detection
# =====================================================================

def _check_clickbait(title: str) -> tuple[float, list[str]]:
    """Ελέγχει αν ο τίτλος έχει χαρακτηριστικά clickbait.

    Ψάχνει για γνωστές clickbait φράσεις, υπερβολικά CAPS,
    και υπερβολικά σημεία στίξης.

    Επιστρέφει (penalty, flags) — penalty στο εύρος [0.0, 0.5].
    """
    title_lower = title.lower().strip()
    penalty = 0.0
    flags: list[str] = []

    # Έλεγχος γνωστών clickbait φράσεων (μερικές είναι regex patterns)
    matches = 0
    for phrase in CLICKBAIT_PHRASES:
        if "\\" in phrase:
            # Regex pattern — π.χ. "number \\d+ will shock"
            if re.search(phrase, title_lower):
                matches += 1
        elif phrase in title_lower:
            matches += 1

    if matches >= 2:
        # Πολλαπλά clickbait σημάδια — σοβαρή ποινή
        penalty += 0.45
        flags.append("clickbait_phrases")
    elif matches == 1:
        # Ένα clickbait σημάδι — μέτρια ποινή
        penalty += 0.15
        flags.append("clickbait_phrase")

    # Έλεγχος υπερβολικών κεφαλαίων (>60% CAPS σε τίτλο > 10 χαρακτήρων)
    if len(title) > 10 and _count_uppercase_ratio(title) > 0.6:
        penalty += 0.2
        flags.append("excessive_caps")

    # Έλεγχος υπερβολικών σημείων στίξης (3+ ! ή ?)
    excl_count = title.count("!") + title.count("?")
    if excl_count >= 3:
        penalty += 0.15
        flags.append("excessive_punctuation")

    return min(penalty, 0.6), flags


# =====================================================================
# Layer 1: AI Slop Detection
# =====================================================================

def _check_ai_slop(text: str) -> tuple[float, list[str]]:
    """Ελέγχει αν το κείμενο περιέχει τυπικές AI-generated φράσεις.

    Μετράει πόσες AI slop φράσεις βρίσκονται στο κείμενο και
    βαθμολογεί ανάλογα.

    Επιστρέφει (penalty, flags) — penalty στο εύρος [0.0, 0.4].
    """
    text_lower = text.lower()
    penalty = 0.0
    flags: list[str] = []

    # Μέτρηση AI slop φράσεων στο κείμενο
    matches = sum(1 for phrase in AI_SLOP_PHRASES if phrase in text_lower)

    if matches >= 4:
        # Γεμάτο AI slop — σχεδόν σίγουρα auto-generated
        penalty = 0.55
        flags.append("heavy_ai_slop")
    elif matches >= 2:
        # Αρκετά AI σημάδια — ύποπτο
        penalty = 0.25
        flags.append("ai_slop")
    elif matches == 1:
        # Ένα match — μπορεί να είναι τυχαίο, ελαφριά ποινή
        penalty = 0.1
        flags.append("mild_ai_slop")

    return penalty, flags


# =====================================================================
# Layer 2: Content Quality
# =====================================================================

def _check_content_quality(title: str, summary: str | None) -> tuple[float, list[str]]:
    """Αξιολογεί τη βασική ποιότητα περιεχομένου (μήκος, δομή).

    Ελέγχει μήκος τίτλου, ύπαρξη/μήκος summary, και overlap
    μεταξύ τίτλου και summary.

    Επιστρέφει (penalty, flags) — penalty στο εύρος [0.0, 0.4].
    """
    penalty = 0.0
    flags: list[str] = []

    # Έλεγχος μήκους τίτλου
    if not title or len(title.strip()) == 0:
        penalty += 0.4
        flags.append("empty_title")
    elif len(title) < 15:
        penalty += 0.2
        flags.append("short_title")
    elif len(title) > 130:
        penalty += 0.1
        flags.append("long_title")
        
    # Έλεγχος ύπαρξης summary
    if not summary or len(summary.strip()) == 0:
        penalty += 0.2
        flags.append("empty_summary")
    elif len(summary.strip()) < 20:
        penalty += 0.1
        flags.append("short_summary")

    # Έλεγχος αν τίτλος και summary είναι ίδια
    if title and summary and title.strip().lower() == summary.strip().lower():
        penalty += 0.3
        flags.append("title_summary_identical")
        
    return min(penalty, 0.4), flags


# =====================================================================
# Λέξεις/φράσεις που δείχνουν promotional / sponsored content
# =====================================================================
_PROMO_PATTERNS: list[str] = [
    "sponsored",
    "promoted",
    "advertisement",
    "advertising",
    "partner content",
    "paid post",
    "paid promotion",
    "paid partnership",
    "brand partner",
    "affiliate",
    "buy now",
    "shop now",
    "order now",
    "discount code",
    "promo code",
    "use code",
    "coupon",
    "limited offer",
    "free trial",
    "subscribe now",
    "διαφήμιση",
    "διαφημιστικό",
    "χορηγούμενο",
    "χορηγούμενη",
    "χορηγουμενο",
    "χορηγουμενη",
    "προώθηση",
]


def _check_spam_signals(title: str, summary: str | None) -> tuple[float, list[str]]:
    """Ελέγχει για spam signals (emoji, promotional content).

    Ψάχνει για διαφημιστικό / χορηγούμενο περιεχόμενο (promotional/sponsored)
    καθώς και υπερβολικά emoji στον τίτλο.

    Επιστρέφει (penalty, flags) — penalty στο εύρος [0.0, 0.9].
    """
    penalty = 0.0
    flags: list[str] = []
    text = title + " " + (summary or "")
    text_lower = text.lower()

    # Υπερβολικά emoji στον τίτλο (συνήθως spam / clickbait)
    emoji_count = _count_emoji(title)
    if emoji_count >= 3:
        penalty += 0.2
        flags.append("emoji_spam")
    elif emoji_count >= 1:
        penalty += 0.05
        flags.append("has_emoji")

    # Έλεγχος για διαφημιστικά μοτίβα
    # Αν βρεθεί έστω και ένα διαφημιστικό σημάδι, επιβάλλεται βαριά ποινή
    # ώστε το άρθρο να φιλτραριστεί αυτόματα (το quality score πέφτει κάτω από 0.3)
    promo_matched = False
    for pattern in _PROMO_PATTERNS:
        if pattern in text_lower:
            promo_matched = True
            break

    # Έλεγχος για τη λέξη "ad" ως αυτόνομη λέξη (π.χ. "ad:", "[ad]")
    if not promo_matched:
        # Regex με όρια λέξεων για αποφυγή ψευδών θετικών (π.χ. address)
        if re.search(r"\b(ad|ads|διαφ|promo)\b", text_lower):
            promo_matched = True

    if promo_matched:
        penalty += 0.8
        flags.append("promotional")

    return min(penalty, 0.9), flags


# =====================================================================
# Layer 3: Fuzzy Duplicate Detection
# =====================================================================

def _check_fuzzy_duplicate(
    title: str,
    recent_titles: list[str],
    threshold: int = 85,
) -> tuple[float, list[str]]:
    """Ελέγχει αν ο τίτλος μοιάζει πολύ με πρόσφατους τίτλους.

    Χρησιμοποιεί rapidfuzz (token_sort_ratio) για γρήγορο
    fuzzy matching. Αν δεν είναι εγκατεστημένο, παραλείπει.

    Args:
        title: Ο τίτλος προς έλεγχο
        recent_titles: Λίστα πρόσφατων τίτλων (τελευταίες 48 ώρες)
        threshold: Ελάχιστο ποσοστό ομοιότητας (default 85%)

    Επιστρέφει (penalty, flags) — penalty στο εύρος [0.0, 0.35].
    Πολυπλοκότητα: O(n) όπου n = αριθμός recent_titles.
    """
    if not recent_titles:
        return 0.0, []

    try:
        from rapidfuzz import fuzz
    except ImportError:
        # Αν δεν είναι εγκατεστημένο, παράλειψη ελέγχου
        return 0.0, []

    title_clean = title.lower().strip()

    # Εύρεση του πιο παρόμοιου τίτλου
    best_ratio = 0.0
    for recent in recent_titles:
        ratio = fuzz.token_sort_ratio(title_clean, recent.lower().strip())
        if ratio > best_ratio:
            best_ratio = ratio

    flags: list[str] = []
    penalty = 0.0

    if best_ratio >= 95:
        # Σχεδόν ίδιος τίτλος — πολύ πιθανό duplicate
        penalty = 0.35
        flags.append("near_duplicate")
    elif best_ratio >= threshold:
        # Πολύ παρόμοιος — πιθανό repost / aggregation
        penalty = 0.2
        flags.append("similar_title")

    return penalty, flags


# =====================================================================
# Κύρια Συνάρτηση Βαθμολόγησης
# =====================================================================

def score_article(
    title: str,
    summary: str | None,
    feed_title: str | None = None,
    recent_titles: list[str] | None = None,
) -> tuple[float, list[str]]:
    """Κύρια συνάρτηση βαθμολόγησης ποιότητας άρθρου.

    Εφαρμόζει όλα τα layers (clickbait, AI slop, content quality,
    spam signals, fuzzy duplicates) και επιστρέφει ένα συνολικό
    quality score μαζί με λίστα flags.

    Args:
        title: Ο τίτλος του άρθρου
        summary: Η περίληψη / description (μπορεί να είναι None)
        feed_title: Το όνομα του feed (για logging / μελλοντική χρήση)
        recent_titles: Λίστα πρόσφατων τίτλων για dedup (τελευταίες 48h)

    Returns:
        (quality_score, flags) — score 0.0-1.0, flags λίστα αιτιών

    Πολυπλοκότητα: O(n*m) όπου n = μήκος κειμένου, m = αριθμός patterns.
    Μνήμη: O(1) σταθερή (δεν δημιουργεί μεγάλες δομές).
    """
    # Βασικό score ξεκινάει στο 1.0 (τέλειο άρθρο)
    score = 1.0
    all_flags: list[str] = []

    # Συνδυασμός τίτλου + summary για ελέγχους κειμένου
    combined_text = title + " " + (summary or "")

    # === Layer 1: Clickbait Detection ===
    clickbait_pen, clickbait_flags = _check_clickbait(title)
    score -= clickbait_pen
    all_flags.extend(clickbait_flags)

    # === Layer 1: AI Slop Detection ===
    slop_pen, slop_flags = _check_ai_slop(combined_text)
    score -= slop_pen
    all_flags.extend(slop_flags)

    # === Layer 2: Content Quality ===
    quality_pen, quality_flags = _check_content_quality(title, summary)
    score -= quality_pen
    all_flags.extend(quality_flags)

    # === Layer 2: Spam Signals ===
    spam_pen, spam_flags = _check_spam_signals(title, summary)
    score -= spam_pen
    all_flags.extend(spam_flags)

    # === Layer 3: Fuzzy Duplicate ===
    if recent_titles is not None:
        dup_pen, dup_flags = _check_fuzzy_duplicate(title, recent_titles)
        score -= dup_pen
        all_flags.extend(dup_flags)

    # Κλείδωμα score στο εύρος [0.0, 1.0]
    final_score = max(0.0, min(1.0, score))

    return round(final_score, 3), all_flags
