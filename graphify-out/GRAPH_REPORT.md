# Graph Report - C:\Users\chris\Documents\GitHub\feedflow-v2  (2026-06-10)

## Corpus Check
- 10 files · ~13,668 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 83 nodes · 160 edges · 12 communities detected
- Extraction: 62% EXTRACTED · 38% INFERRED · 0% AMBIGUOUS · INFERRED: 61 edges (avg confidence: 0.6)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]

## God Nodes (most connected - your core abstractions)
1. `Feed` - 18 edges
2. `Article` - 18 edges
3. `fetch_og_image()` - 11 edges
4. `clean_translated_url()` - 10 edges
5. `Category` - 10 edges
6. `UserInteraction` - 10 edges
7. `process_feed()` - 8 edges
8. `TestCleanTranslatedUrl` - 8 edges
9. `process_scrape_feed()` - 7 edges
10. `ArticleResponse` - 6 edges

## Surprising Connections (you probably didn't know these)
- `mark_read()` --calls--> `UserInteraction`  [INFERRED]
  C:\Users\chris\Documents\GitHub\feedflow-v2\main.py → C:\Users\chris\Documents\GitHub\feedflow-v2\models.py
- `read_article()` --calls--> `UserInteraction`  [INFERRED]
  C:\Users\chris\Documents\GitHub\feedflow-v2\main.py → C:\Users\chris\Documents\GitHub\feedflow-v2\models.py
- `backfill_article()` --calls--> `fetch_og_image()`  [INFERRED]
  C:\Users\chris\Documents\GitHub\feedflow-v2\backfill_images.py → C:\Users\chris\Documents\GitHub\feedflow-v2\fetcher.py
- `fetch_og_image()` --calls--> `run_example()`  [INFERRED]
  C:\Users\chris\Documents\GitHub\feedflow-v2\fetcher.py → C:\Users\chris\Documents\GitHub\feedflow-v2\test_fetcher.py
- `process_scrape_feed()` --calls--> `Article`  [INFERRED]
  C:\Users\chris\Documents\GitHub\feedflow-v2\fetcher.py → C:\Users\chris\Documents\GitHub\feedflow-v2\models.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.25
Nodes (10): extract_image(), fetch_feed_xml(), _fetch_html_with_fallback(), fetch_og_image(), is_valid_image(), parse_date(), process_feed(), process_scrape_feed() (+2 more)

### Community 1 - "Community 1"
Cohesion: 0.2
Nodes (2): mark_read(), read_article()

### Community 2 - "Community 2"
Cohesion: 0.36
Nodes (10): Base, Ελέγχει αν ένα URL εικόνας είναι έγκυρο (αποκλείει favicons, trackers κτλ.)., Ανακτά OG/Twitter εικόνα από σελίδα άρθρου.      Αν η άμεση σύνδεση αποτύχει (40, Κατεβάζει XML δεδομένα από RSS/Atom feed URL., Κάνει scrape μια ιστοσελίδα για άρθρα.      Αν η άμεση σύνδεση αποτύχει (π.χ. Cl, Επεξεργάζεται ένα feed (RSS ή scrape) και προσθέτει νέα άρθρα., Προσπαθεί να φέρει HTML απευθείας· αν αποτύχει (403 / exception),     χρησιμοποι, Αναλύει ημερομηνία από RSS feed string σε datetime αντικείμενο. (+2 more)

### Community 3 - "Community 3"
Cohesion: 0.31
Nodes (4): clean_translated_url(), Μετατρέπει URL από τo Google Translate proxy πίσω στο αρχικό domain.      Αν το, Δοκιμές για τη συνάρτηση clean_translated_url., TestCleanTranslatedUrl

### Community 4 - "Community 4"
Cohesion: 0.42
Nodes (8): BaseModel, ArticleResponse, FeedCreate, PaginatedArticlesResponse, Δοκιμάζει να βρει το RSS URL από μια σελίδα.     Αν βρει RSS, επιστρέφει (rss_ur, Δοκιμάζει να βρει το RSS URL από μια σελίδα.     Αν βρει RSS, επιστρέφει (rss_ur, Category, UserInteraction

### Community 5 - "Community 5"
Cohesion: 0.43
Nodes (7): fetchArticles(), initApp(), openSettings(), renderArticles(), renderCategories(), renderManageFeeds(), renderSkeletons()

### Community 6 - "Community 6"
Cohesion: 0.46
Nodes (7): openReader(), animateLighthouse(), hideLighthouse(), initLighthouse(), showLighthouse(), startLighthouseAnimation(), stopLighthouseAnimation()

### Community 7 - "Community 7"
Cohesion: 1.0
Nodes (2): backfill_article(), main()

### Community 8 - "Community 8"
Cohesion: 0.67
Nodes (0): 

### Community 9 - "Community 9"
Cohesion: 0.67
Nodes (3): add_feed(), discover_feed(), Δοκιμάζει να βρει το RSS URL από μια σελίδα.     Αν βρει RSS, επιστρέφει (rss_ur

### Community 10 - "Community 10"
Cohesion: 1.0
Nodes (1): seed_database()

### Community 11 - "Community 11"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **1 isolated node(s):** `Δοκιμές για τη συνάρτηση clean_translated_url.`
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 10`** (2 nodes): `seeder.py`, `seed_database()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 11`** (2 nodes): `three_bg.js`, `animate()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Article` connect `Community 2` to `Community 0`, `Community 9`, `Community 3`, `Community 4`?**
  _High betweenness centrality (0.177) - this node is a cross-community bridge._
- **Why does `fetch_og_image()` connect `Community 0` to `Community 2`, `Community 3`, `Community 7`?**
  _High betweenness centrality (0.136) - this node is a cross-community bridge._
- **Why does `Feed` connect `Community 2` to `Community 9`, `Community 10`, `Community 3`, `Community 4`?**
  _High betweenness centrality (0.133) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `Feed` (e.g. with `Μετατρέπει URL από τo Google Translate proxy πίσω στο αρχικό domain.      Αν το` and `Προσπαθεί να φέρει HTML απευθείας· αν αποτύχει (403 / exception),     χρησιμοποι`) actually correct?**
  _`Feed` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `Article` (e.g. with `Μετατρέπει URL από τo Google Translate proxy πίσω στο αρχικό domain.      Αν το` and `Προσπαθεί να φέρει HTML απευθείας· αν αποτύχει (403 / exception),     χρησιμοποι`) actually correct?**
  _`Article` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `fetch_og_image()` (e.g. with `backfill_article()` and `.test_fetch_og_image_success()`) actually correct?**
  _`fetch_og_image()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `clean_translated_url()` (e.g. with `.test_translate_goog_url_cleaned()` and `.test_non_translate_url_unchanged()`) actually correct?**
  _`clean_translated_url()` has 6 INFERRED edges - model-reasoned connections that need verification._