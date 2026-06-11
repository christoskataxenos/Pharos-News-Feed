import unittest
from filters import (
    score_article,
    _check_clickbait,
    _check_ai_slop,
    _check_content_quality,
    _check_spam_signals,
    _check_fuzzy_duplicate,
    QUALITY_THRESHOLD,
)


class TestClickbaitDetection(unittest.TestCase):
    """Δοκιμές για την ανίχνευση clickbait τίτλων."""

    # Δοκιμή: τίτλος με πολλά clickbait σημάδια → σοβαρή ποινή
    def test_heavy_clickbait_title(self) -> None:
        penalty, flags = _check_clickbait(
            "SHOCKING: You Won't Believe What Happens Next!!!"
        )
        self.assertGreater(penalty, 0.3)
        self.assertTrue(len(flags) >= 2)

    # Δοκιμή: τίτλος με ένα clickbait σημάδι → μέτρια ποινή
    def test_mild_clickbait_title(self) -> None:
        penalty, flags = _check_clickbait(
            "The Truth About Python's Performance in 2024"
        )
        self.assertGreater(penalty, 0.0)
        self.assertIn("clickbait_phrase", flags)

    # Δοκιμή: κανονικός τεχνολογικός τίτλος → καμία ποινή
    def test_normal_tech_title(self) -> None:
        penalty, flags = _check_clickbait(
            "Linux Kernel 6.8 Released With Better AMD GPU Support"
        )
        self.assertEqual(penalty, 0.0)
        self.assertEqual(flags, [])

    # Δοκιμή: ALL CAPS τίτλος → ποινή excessive_caps
    def test_all_caps_title(self) -> None:
        penalty, flags = _check_clickbait(
            "NVIDIA ANNOUNCES NEW GPU ARCHITECTURE FOR AI WORKLOADS"
        )
        self.assertGreater(penalty, 0.0)
        self.assertIn("excessive_caps", flags)

    # Δοκιμή: υπερβολικά σημεία στίξης
    def test_excessive_punctuation(self) -> None:
        penalty, flags = _check_clickbait(
            "Wait what?!? This is incredible!!!"
        )
        self.assertGreater(penalty, 0.0)
        self.assertIn("excessive_punctuation", flags)


class TestAiSlopDetection(unittest.TestCase):
    """Δοκιμές για την ανίχνευση AI-generated slop content."""

    # Δοκιμή: κείμενο γεμάτο AI φράσεις → heavy penalty
    def test_heavy_ai_slop(self) -> None:
        text = (
            "In today's rapidly evolving digital landscape, "
            "it's important to note that this comprehensive guide "
            "will help you navigate the complexities of modern tech. "
            "Let's dive in and unlock the potential of AI."
        )
        penalty, flags = _check_ai_slop(text)
        self.assertGreater(penalty, 0.3)
        self.assertIn("heavy_ai_slop", flags)

    # Δοκιμή: κανονικό τεχνολογικό κείμενο → καμία ποινή
    def test_normal_tech_content(self) -> None:
        text = (
            "The new compiler optimization reduces build times by 30%. "
            "Engineers tested the feature across 500 production workloads "
            "and found consistent improvements in memory usage."
        )
        penalty, flags = _check_ai_slop(text)
        self.assertEqual(penalty, 0.0)
        self.assertEqual(flags, [])

    # Δοκιμή: μία AI φράση μόνο → ελαφριά ποινή
    def test_single_ai_phrase(self) -> None:
        text = "In today's rapidly evolving market, companies need to adapt."
        penalty, flags = _check_ai_slop(text)
        self.assertGreater(penalty, 0.0)
        self.assertIn("mild_ai_slop", flags)


class TestContentQuality(unittest.TestCase):
    """Δοκιμές για τον έλεγχο ποιότητας περιεχομένου."""

    # Δοκιμή: κοντός τίτλος → ποινή
    def test_short_title(self) -> None:
        penalty, flags = _check_content_quality("Short", "A decent summary here.")
        self.assertGreater(penalty, 0.0)
        self.assertIn("short_title", flags)

    # Δοκιμή: κενό summary → ποινή
    def test_empty_summary(self) -> None:
        penalty, flags = _check_content_quality(
            "A Normal Title For An Article", None
        )
        self.assertGreater(penalty, 0.0)
        self.assertIn("empty_summary", flags)

    # Δοκιμή: τίτλος = summary → ποινή
    def test_title_equals_summary(self) -> None:
        title = "Breaking News About Technology"
        penalty, flags = _check_content_quality(title, title)
        self.assertIn("title_summary_identical", flags)

    # Δοκιμή: καλό περιεχόμενο → καμία ποινή
    def test_good_content(self) -> None:
        penalty, flags = _check_content_quality(
            "Linux Kernel 6.8 Brings Exciting New Features for Developers",
            "The latest kernel release includes improved eBPF support, "
            "better scheduling algorithms, and enhanced security modules "
            "that benefit both desktop and server workloads."
        )
        self.assertEqual(penalty, 0.0)
        self.assertEqual(flags, [])


class TestSpamSignals(unittest.TestCase):
    """Δοκιμές για ανίχνευση spam signals."""

    # Δοκιμή: promotional content → ποινή
    def test_promotional_content(self) -> None:
        penalty, flags = _check_spam_signals(
            "Buy Now: Amazing Discount Code Inside!",
            "Use code SAVE50 for a limited offer on our products."
        )
        self.assertGreater(penalty, 0.0)
        self.assertTrue(
            "promotional" in flags or "mild_promo" in flags
        )

    # Δοκιμή: κανονικό άρθρο → καμία ποινή
    def test_normal_article(self) -> None:
        penalty, flags = _check_spam_signals(
            "Cloudflare Introduces New DDoS Protection Features",
            "The update includes automatic threat detection and mitigation."
        )
        self.assertEqual(penalty, 0.0)


class TestFuzzyDuplicate(unittest.TestCase):
    """Δοκιμές για fuzzy duplicate detection."""

    # Δοκιμή: σχεδόν ίδιος τίτλος → penalty
    def test_near_duplicate(self) -> None:
        recent = ["Linux Kernel 6.8 Released with New Features"]
        penalty, flags = _check_fuzzy_duplicate(
            "Linux Kernel 6.8 Released With New Features",
            recent,
        )
        self.assertGreater(penalty, 0.0)
        self.assertTrue(
            "near_duplicate" in flags or "similar_title" in flags
        )

    # Δοκιμή: εντελώς διαφορετικός τίτλος → καμία ποινή
    def test_different_title(self) -> None:
        recent = ["Python 3.12 Adds Pattern Matching Improvements"]
        penalty, flags = _check_fuzzy_duplicate(
            "NVIDIA Unveils New RTX 5090 Graphics Card",
            recent,
        )
        self.assertEqual(penalty, 0.0)
        self.assertEqual(flags, [])

    # Δοκιμή: κενή λίστα πρόσφατων τίτλων → καμία ποινή
    def test_empty_recent(self) -> None:
        penalty, flags = _check_fuzzy_duplicate("Any title here", [])
        self.assertEqual(penalty, 0.0)
        self.assertEqual(flags, [])


class TestScoreArticle(unittest.TestCase):
    """Δοκιμές ολοκλήρωσης για τη συνάρτηση score_article."""

    # Δοκιμή: υψηλής ποιότητας άρθρο → score ≥ 0.7
    def test_high_quality_article(self) -> None:
        score, flags = score_article(
            title="Linux Kernel 6.8 Released With Better AMD GPU Support",
            summary=(
                "The Linux kernel team has released version 6.8, bringing "
                "significant improvements to AMD GPU drivers, enhanced "
                "eBPF support, and better power management for laptops."
            ),
        )
        self.assertGreaterEqual(score, 0.7)
        self.assertEqual(flags, [])

    # Δοκιμή: χαμηλής ποιότητας clickbait → score < threshold
    def test_clickbait_article_filtered(self) -> None:
        score, flags = score_article(
            title="SHOCKING!!! You Won't Believe What Happens Next!!!",
            summary="",
        )
        self.assertLess(score, QUALITY_THRESHOLD)
        self.assertTrue(len(flags) > 0)

    # Δοκιμή: AI slop content → χαμηλό score
    def test_ai_slop_article(self) -> None:
        score, flags = score_article(
            title="In Today's Rapidly Evolving Digital Landscape",
            summary=(
                "It's important to note that this comprehensive guide "
                "will help you navigate the complexities. Let's dive in "
                "and unlock the potential of holistic approaches."
            ),
        )
        self.assertLess(score, 0.5)
        self.assertTrue(any("slop" in f for f in flags))

    # Δοκιμή: μέτριας ποιότητας — πάνω από threshold αλλά όχι τέλειο
    def test_medium_quality(self) -> None:
        score, flags = score_article(
            title="Tech update",
            summary="Short desc.",
        )
        # Κοντός τίτλος + κοντό summary → penalties αλλά δεν είναι spam
        self.assertLess(score, 1.0)
        self.assertGreater(score, 0.0)

    # Δοκιμή: edge case — κενός τίτλος
    def test_empty_title(self) -> None:
        score, flags = score_article(title="", summary=None)
        self.assertLess(score, 0.7)

    # Δοκιμή: Ελληνικό κείμενο — δεν πρέπει να μπλοκάρεται
    def test_greek_content_passes(self) -> None:
        score, flags = score_article(
            title="Νέα αναβάθμιση ασφαλείας για τα Windows 11",
            summary=(
                "Η Microsoft κυκλοφόρησε σημαντική ενημέρωση ασφαλείας "
                "που διορθώνει κρίσιμα κενά ασφαλείας στο λειτουργικό "
                "σύστημα Windows 11 έκδοση 24H2."
            ),
        )
        self.assertGreaterEqual(score, 0.7)

    # Δοκιμή: fuzzy duplicate integration
    def test_duplicate_penalty(self) -> None:
        recent = [
            "Apple Releases iOS 18.2 With AI Features",
            "Google Chrome Gets New Security Update",
        ]
        score_original, _ = score_article(
            title="Apple Releases iOS 18.2 With AI Features",
            summary="Apple has released a new iOS version.",
            recent_titles=recent,
        )
        score_unique, _ = score_article(
            title="NVIDIA Announces Next-Gen GPU Architecture",
            summary="NVIDIA revealed their new GPU lineup today.",
            recent_titles=recent,
        )
        # Duplicate πρέπει να έχει χαμηλότερο score
        self.assertLess(score_original, score_unique)


# Παράδειγμα χρήσης (~15 γραμμές)
def run_example() -> None:
    """Παράδειγμα εκτέλεσης — δείχνει πώς λειτουργεί το scoring."""
    examples = [
        ("Linux 6.8 Released With Better AMD Support",
         "New kernel release with improvements to GPU drivers and power management."),
        ("SHOCKING!!! You Won't Believe This!!!",
         ""),
        ("In Today's Rapidly Evolving Digital Landscape",
         "It's important to note that this comprehensive guide will help "
         "you navigate the complexities. Let's dive in."),
    ]
    for title, summary in examples:
        score, flags = score_article(title, summary)
        status = "PASS" if score >= QUALITY_THRESHOLD else "FILTERED"
        print(f"[{status}] Score={score:.3f} Flags={flags}")
        print(f"  Title: {title}")
        print()


if __name__ == "__main__":
    unittest.main()
