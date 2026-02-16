# Copilot Instructions for feedmeup News Aggregator

## Project Overview
**feedmeup** is an automated RSS feed aggregator that fetches news from 40+ sources (AI/LLM, Cloud, Cybersecurity, CVE/Vulnerability, Threat Intelligence, APAC regulatory), applies keyword filters, groups similar articles by fuzzy-matching, and publishes as Jekyll markdown posts to GitHub Pages on a weekly schedule.

## Architecture & Data Flow

### Core Pipeline: `fetch_news.py`
1. **Load config** → reads `config.yaml` for sources, keywords, and deduplication settings
2. **Fetch feeds** → parallel retrieval with automatic retry logic (3 retries, backoff_factor=0.3, timeout=15s)
3. **Filter by keywords** → regex pattern matching against title + summary + content (case-insensitive word boundaries)
4. **Deduplicate** → fuzzy title matching (default threshold 0.8) groups similar stories across feeds
5. **Generate posts** → creates single Jekyll `.md` file with highlights, summary table, and categorized articles
6. **Write to `_posts/`** → filenames include date and HH-MM timestamp to prevent collisions

### Configuration: `config.yaml`
- **sources**: list of {name, url, category} — feeds are pre-configured for AI/LLM, Cloud, Cybersecurity, CVE, ThreatIntel, and APAC Regulation
- **filters.keywords**: list of strings for keyword matching (no regex; words are literal, matched at word boundaries)
- **Performance settings**: fuzz_threshold (0.8), max_per_domain (2), max_results (10 for highlights), request_retries (3)
- When adding sources, assign existing category or create new one — these become section headers in generated posts

### Output Structure: Jekyll Posts in `_posts/`
Generated files: `YYYY-MM-DD-HH-MM-news-brief.md` containing:
- **Front matter**: layout: post, title, date with timezone offset, categories: [newsbrief]
- **Highlights section**: top 10 deduplicated stories by frequency × recency, limited to 2 per domain
- **Summary table**: article count per category
- **Categories section**: full article lists formatted with HTML anchors (avoids Markdown link mangling of feed HTML)

## Key Technical Patterns

### Keyword Matching
- No keywords configured → matches everything (default behavior)
- Keywords are literal strings, matched at word boundaries using `\b(keyword1|keyword2|...)\b` regex
- Case-insensitive search across title + summary + content blocks
- **Pattern**: `compile_keywords_pattern(keywords)` returns compiled regex or None

### Error Handling & Edge Cases
- **HTTP 403/404 errors**: saved to `_errors/YYYY-MM-DD-*.md` instead of failing
- **Parse failures**: saves error post with bozo exception details
- **Missing/invalid links**: `sanitize_url()` validates and percent-encodes URLs; missing links skip href
- **HTML cleaning**: `clean_summary()` uses BeautifulSoup to extract plaintext, collapses whitespace
- **Timezone handling**: all times use `America/New_York` (ZoneInfo), includes offset in post front matter
- **30-day lookback**: only fetches entries published in last 30 days (prevents historical data flooding)

### Session & Retry Configuration
- Global `SESSION` object (requests.Session) initialized in `main()` with HTTPAdapter + Retry policy
- Retry logic: exponential backoff, retries on [429, 500, 502, 503, 504]
- User-Agent header set to avoid 403 errors from strict feed servers
- All config values fall back to DEFAULTS dict if missing from config.yaml

### Deduplication: `group_similar_entries()`
- Uses RapidFuzz fuzzy string matching (threshold 0.8 by default)
- Groups entries with similar titles, selects most recent as representative
- Sorts by group size descending, then recency
- **Domain diversity**: enforces max 2 articles per normalized domain (strips www., removes port)
- Returns top N results (default 10) across all categories

## Testing & CI/CD

### Test File: `tests/test_smoke.py`
- Minimal smoke tests: module import, constants existence
- Run locally: `pytest -q` or `python -m pytest`
- CI runs on Python 3.10 and 3.11 on push/PR to main branch

### GitHub Actions Workflows

**`.github/workflows/news.yml`** (Weekly Schedule)
- Triggers: Monday 08:00 UTC or manual dispatch (`workflow_dispatch`)
- Steps: checkout → setup Ruby/Python → install deps → run fetch_news.py → commit to gh-pages branch
- **Branch switching logic**: script temporarily stashes generated posts, switches to gh-pages (or creates if missing), restores posts, commits only if changes
- Permissions: `contents: write` (required for push)

**`.github/workflows/ci.yml`** (Pull Request / Push CI)
- Matrix: Python 3.10, 3.11
- Runs: pytest, optional flake8 (non-blocking)
- No deploy; validates code quality before merge to main

## Developer Workflows

### Adding a New Feed Source
1. Edit `config.yaml` under `sources:` — add {name, url, category}
2. Assign category: use existing (e.g., "Cybersecurity") or create new
3. Test locally: `python fetch_news.py` → check `_posts/` for output
4. Commit and merge to main; news.yml will pick it up on next schedule

### Adjusting Keyword Filters
- Edit `config.yaml` → `filters.keywords` list
- Keywords are literal strings; `fetch_news.py` converts to word-boundary regex
- Empty list (or missing key) matches all articles
- Restart: next scheduled run or manual dispatch workflow

### Debugging a Specific Feed
- Set `LOG_LEVEL: DEBUG` in env before running fetch_news.py locally
- Error posts in `_errors/` contain feed URL and exception details
- Use `requests` retry logic logs to diagnose network issues

### Local Development Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python fetch_news.py
# Check _posts/ for generated output
pytest tests/
```

## Dependencies & Libraries
- **feedparser** (6.0.8+): RFC 3339, RSS 2.0, Atom 1.0 parsing
- **PyYAML** (6.0+): config.yaml loading
- **requests** (2.31.0+): HTTP with retry adapter
- **rapidfuzz** (2.15.1+): fuzzy string matching for deduplication
- **BeautifulSoup4** (4.12.2+): HTML-to-plaintext conversion
- **tzdata** (2024.1+): timezone database for zoneinfo

## Common AI Assistant Tasks

### Adding Deduplication Features
- Threshold is configurable in config.yaml → `fuzz_threshold` (default 0.8)
- Domain diversity logic in `group_similar_entries()` prevents over-weighting single sources
- Modify `normalize_domain()` if domain normalization strategy changes

### Extending Filtering Logic
- Current: keyword word-boundary regex matching
- To add time-based filters: modify `entry_matches()` or adjust `cutoff_date` logic in main()
- To add source-specific rules: extend the loop over sources in `main()`

### Improving Post Format
- HTML anchors used instead of Markdown links to prevent feed HTML mangling
- Summary truncation: 200 chars for category articles, 250 for highlights
- Modify `format_entries_for_category()` or `create_news_brief()` for layout changes

### Debugging Missing Articles
1. Check `_errors/` folder for feed fetch failures
2. Verify keywords in config.yaml match article titles/summaries
3. Check 30-day window: only articles from last 30 days are included
4. Increase `LOG_LEVEL: DEBUG` and re-run to see which entries matched/failed filters
