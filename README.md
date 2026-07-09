# Pharos (FeedFlow V2) — Modern News Feed Aggregator

![License](https://img.shields.io/badge/license-MIT-blue.svg) ![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg) ![Docker](https://img.shields.io/docker/v/christosk89/feedflow?sort=semver&logo=docker&label=Docker%20Hub)

Το **Pharos** είναι ένας σύγχρονος, υψηλών επιδόσεων ασύγχρονος news feed aggregator χτισμένος με **FastAPI**, **SQLAlchemy** (Async) και ένα εντυπωσιακό **Glassmorphic** frontend. Υποστηρίζει RSS/Atom feeds, έξυπνο web scraping, αυτόματη εξαγωγή εικόνων Open Graph και ενσωματωμένη μετάφραση άρθρων.

> 🧠 **Standout feature:** Pharos ships with a built-in **5-layer anti-slop quality engine** that automatically scores every incoming article and filters out clickbait, AI-generated "slop" writing, spam/promotional content, and near-duplicates — before they ever reach your feed. See [Quality Engine](#-anti-slop--quality-scoring-engine) below.

---

## ✨ Χαρακτηριστικά

- **🚀 Υψηλές Επιδόσεις (Async)**: Χρήση `aiohttp` και `asyncio.gather` με semaphores για ταυτόχρονη επεξεργασία δεκάδων feeds χωρίς καθυστερήσεις.
- **🛡️ Cloudflare Bypass**: Έξυπνο σύστημα που εντοπίζει αν ένα site μπλοκάρει το scraping (403 Error) και χρησιμοποιεί αυτόματα Google Translate proxy για να ανακτήσει το περιεχόμενο.
- **📂 Αυτόματη Κατηγοριοποίηση**: Δυνατότητα δημιουργίας κατηγοριών on-the-fly. Τα νέα feeds ταξινομούνται αυτόματα και εμφανίζονται στο sidebar navigation.
- **⚡ SQLite με WAL Mode**: Βελτιστοποιημένη βάση δεδομένων για αποφυγή του "database is locked" και υποστήριξη υψηλού concurrency.
- **🔄 Cursor-Based Pagination**: Infinite scrolling χωρίς διπλότυπα άρθρα και με ελάχιστο φόρτο στη βάση, ακόμα και με χιλιάδες εγγραφές.
- **🎨 Glassmorphic UI**:
  - Animated WebGL particle background (Three.js).
  - Lighthouse loading animation.
  - Reader Mode για καθαρή ανάγνωση άρθρων (Readability.js).
- **🌍 Μετάφραση & Scrapers**: Ενσωματωμένη μετάφραση στα Ελληνικά και ειδικοί scrapers για sites που δεν έχουν RSS (π.χ. AEK365).
- **📦 Docker Ready**: Έτοιμο Dockerfile για εύκολο deployment οπουδήποτε.
- **🧠 Anti-Slop Quality Engine**: 5-layer scoring σύστημα που εντοπίζει clickbait, AI-generated "slop" κείμενο, spam/promotional content και near-duplicate άρθρα, φιλτράροντας αυτόματα ό,τι δεν περνάει το κατώφλι ποιότητας.

---

## 🧠 Anti-Slop & Quality Scoring Engine

Το Pharos δεν είναι απλά ένας aggregator — κάθε άρθρο περνάει από ένα **πολυεπίπεδο σύστημα βαθμολόγησης ποιότητας** (`filters.py`) πριν εμφανιστεί στο feed. Κάθε layer προσθέτει penalty στο quality score ενός άρθρου (0.0–1.0). Άρθρα κάτω από το κατώφλι (`QUALITY_THRESHOLD = 0.3`) μαρκάρονται αυτόματα ως `is_filtered` και κρύβονται από το κύριο feed.

| Layer | Τι εντοπίζει | Παράδειγμα σημάτων |
|---|---|---|
| **1. Clickbait Detection** | Τίτλους-δόλωμα | "you won't believe", "shocking", υπερβολικά CAPS/! ? |
| **2. AI Slop Detection** | Τυπικές LLM-generated φράσεις | "in today's rapidly evolving", "let's dive in", "unlock the power" |
| **3. Content Quality** | Ασθενική δομή περιεχομένου | πολύ κοντός τίτλος, απόν ή ελλιπές summary |
| **4. Spam / Promo Detection** | Διαφημιστικό ή sponsored περιεχόμενο | "sponsored", "promo code", emoji spam |
| **5. Fuzzy Duplicate Detection** | Near-duplicate / repost άρθρα | `rapidfuzz` token-sort similarity ≥ 85–95% έναντι πρόσφατων τίτλων |

Το σύστημα τρέχει live σε κάθε νέο άρθρο κατά το fetch, και μπορεί να τρέξει αναδρομικά σε ολόκληρη τη βάση με:
```bash
python backfill_quality.py
```
Το script τυπώνει live στατιστικά (pass rate, filtered count) και ενημερώνει τα πεδία `quality_score` / `filter_flags` / `is_filtered` σε κάθε άρθρο.

Υπάρχει και ζωντανό `GET /api/stats/quality` endpoint που επιστρέφει το πλήθος φιλτραρισμένων άρθρων και το μέσο quality score όλων των άρθρων — για πλήρη διαφάνεια στο πόσο φιλτράρει το σύστημα.

---

## 🛠️ Τεχνολογίες (Tech Stack)

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy (Async), Pydantic.
- **Database**: SQLite (Asyncio).
- **Frontend**: Vanilla JS (ES6+), Three.js (Background), CSS Grid/Flexbox (Glassmorphism).
- **Libraries**: `feedparser`, `beautifulsoup4`, `readability-lxml`, `deep-translator`.

---

## 🚀 Γρήγορη Εκκίνηση (Quick Start)

### 🐳 Με Docker (Προτεινόμενο)

Η εφαρμογή είναι ρυθμισμένη να **κάνει αυτόματα seed** τα default feeds και να ξεκινάει το **πρώτο συγχρονισμό** άρθρων με το που τρέξει.

1. **Κατεβάστε και τρέξτε το image**:
   ```bash
   docker run -d -p 8000:8000 --name pharos christosk89/feedflow:latest
   ```
2. **Πρόσβαση**: Ανοίξτε το πρόγραμμα περιήγησης στο `http://localhost:8000`.

*Σημείωση: Για να μην χάνονται τα δεδομένα σας όταν σβήνετε το container, χρησιμοποιήστε volumes:*
```bash
docker run -d -p 8000:8000 -v pharos_data:/app christosk89/feedflow:latest
```

### 💻 Τοπική Εγκατάσταση (Local Setup)

1. **Clone & Virtual Env**:
   ```bash
   git clone <your-repo-url>
   cd feedflow-v2
   python -m venv venv
   source venv/bin/activate  # Σε Windows: .\venv\Scripts\Activate.ps1
   ```

2. **Εγκατάσταση Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Ρύθμιση `.env`**:
   Δημιουργήστε ένα αρχείο `.env`:
   ```env
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=your_password
   ```

4. **Εκτέλεση**:
   ```bash
   uvicorn main:app --reload
   ```
   *Η βάση θα δημιουργηθεί και θα γεμίσει αυτόματα με τα default feeds στην πρώτη εκτέλεση.*

---

## 📂 Δομή Φακέλων

- `main.py`: Τα API endpoints και η λογική εκκίνησης.
- `fetcher.py`: Η "καρδιά" του συστήματος. Διαχειρίζεται το parsing, scraping και Cloudflare bypass.
- `seeder.py`: Περιέχει τα hardcoded default feeds (Tech News, Greek Tech, κλπ).
- `models.py`: Τα database schemas.
- `static/`: Όλος ο κώδικας του frontend (HTML/CSS/JS).
- `backfill_images.py`: Utility για να τραβήξετε εικόνες Open Graph για παλιά άρθρα.
- `filters.py`: Ο anti-slop quality engine — clickbait, AI-slop, spam/promo και fuzzy-duplicate detection.
- `backfill_quality.py`: Utility για αναδρομική βαθμολόγηση ποιότητας σε ήδη αποθηκευμένα άρθρα.

---

## 🧪 Testing

Τρέξτε τα unit tests για να επιβεβαιώσετε τη σωστή λειτουργία του scraper και του URL cleaning:
```bash
python -m unittest test_fetcher.py -v
```

---

## 📝 License

MIT License — see [LICENSE](LICENSE).
