# Pharos (FeedFlow V2) — Modern News Feed Aggregator

Το **Pharos** είναι ένας σύγχρονος, υψηλών επιδόσεων ασύγχρονος news feed aggregator χτισμένος με **FastAPI**, **SQLAlchemy** (Async) και ένα εντυπωσιακό **Glassmorphic** frontend. Υποστηρίζει RSS/Atom feeds, έξυπνο web scraping, αυτόματη εξαγωγή εικόνων Open Graph και ενσωματωμένη μετάφραση άρθρων.

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

---

## 🧪 Testing

Τρέξτε τα unit tests για να επιβεβαιώσετε τη σωστή λειτουργία του scraper και του URL cleaning:
```bash
python -m unittest test_fetcher.py -v
```

---

## 📝 License

This project is private and intended for personal use.
