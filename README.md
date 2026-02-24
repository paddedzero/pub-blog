# feedmeup — Automated Tech News Aggregator

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Astro](https://img.shields.io/badge/Astro-Latest-purple)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated-success)

An intelligent news aggregator that automatically curates, deduplicates, summarizes, and publishes technology news from 40+ sources covering AI/LLM, Cloud, Cybersecurity, Vulnerabilities, Threat Intelligence, and Asia-Pacific regulatory updates.

---

## 🎯 What This Project Does

**feedmeup** is a fully automated news pipeline that:

1. **Fetches** news from 40+ RSS/Atom feeds across multiple categories
2. **Filters** content using configurable keyword matching
3. **Deduplicates** similar articles using fuzzy string matching (RapidFuzz)
4. **Summarizes** content using Google Gemini AI (1.5 Flash model)
5. **Generates** two types of posts:
   - **Weekly Scan**: Comprehensive news roundup with categorized articles and highlights
   - **Analyst Opinion**: AI-powered analysis with trends and strategic insights
6. **Publishes** automatically to your site with a modern Astro + Svelte frontend
7. **Runs weekly** via GitHub Actions (Mondays 8 AM UTC) or on-demand

---

## 🏗️ Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│ GitHub Actions Workflow (Scheduled: Mon 8AM UTC)           │
├─────────────────────────────────────────────────────────────┤
│  1. fetch_news.py → Aggregates 40+ RSS feeds               │
│  2. Filters by keywords (config.yaml)                      │
│  3. Deduplicates using RapidFuzz                           │
│  4. Gemini AI → Generates summaries & analysis             │
│  5. Creates markdown posts to site/content/newsfeed/       │
│  6. Astro site rebuilds and publishes                      │
│  7. Live on GitHub Pages with modern UI                    │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Astro 5.x + Svelte 5 + Tailwind CSS |
| **Aggregation** | Python 3.10+ with requests + feedparser |
| **Data Processing** | RapidFuzz (dedup), BeautifulSoup (HTML), Sentence-Transformers (semantic analysis) |
| **AI Summarization** | Google Gemini API (1.5 Flash) |
| **Deployment** | GitHub Pages + GitHub Actions |
| **Content** | Markdown with frontmatter, Astro content collections |

---

## 📰 News Sources (40+ Feeds)

### AI & LLM (25+ sources)
- OpenAI, Google AI, Microsoft AI, Hugging Face, DeepMind, Anthropic, Meta AI, Amazon Science, IBM Research, Apple ML
- Stanford HAI, MIT CSAIL, Berkeley AI, CMU ML
- VentureBeat AI, The Verge, MIT Technology Review, Ars Technica
- Netflix, Uber, Airbnb, Spotify Engineering blogs

### Cloud (3+ sources)
- AWS News, Azure Updates, Google Cloud Blog

### Cybersecurity & Vulnerabilities (15+ sources)
- Dark Reading, Krebs on Security, BleepingComputer, SecurityWeek
- CVE Details, Rapid7, Tenable, VulnDB
- Recorded Future, CrowdStrike, Cisco Talos, Palo Alto Unit 42, SANS ISC

### Threat Intelligence (5+ sources)
- Major security vendor blogs and threat reports

### Asia-Pacific Regulation (5+ sources)
- Singapore MAS/CSA, Japan NISC, India CERT-In, Korea KISA, Malaysia MyCERT

---

## 🚀 How It Works

### 1. News Aggregation (`scripts/fetch_news.py`)

```python
# Parallel feed fetching with retry logic
- HTTP requests with 3 retries, exponential backoff
- 15-second timeout per feed
- 30-day lookback window
- HTML-to-plaintext conversion with BeautifulSoup
- Session-based requests to handle feed rate limits
```

**Process**:
1. Load feed sources and filters from `config.yaml`
2. Fetch all feeds in parallel with retry/timeout handling
3. Parse RSS/Atom with feedparser
4. Extract title, summary, content, and metadata
5. Check entry age (30-day window)

### 2. Keyword Filtering

```yaml
# config.yaml
filters:
  keywords:
    - vulnerability
    - zero-day
    - ransomware
    - data breach
    # ... configurable list
```

- Word-boundary regex matching (case-insensitive)
- Searches across title + summary + content
- Empty list = matches everything (useful for broad categories)
- Patterns compiled once for performance

### 3. Deduplication (`group_similar_entries()`)

- **Fuzzy title matching** using RapidFuzz (threshold 0.8, configurable)
- Groups similar stories across feeds
- Selects most recent entry as representative
- **Domain diversity**: Enforces max 2 articles per normalized domain (strips www., removes port)
- **Sorting**: By group size (frequency), then recency
- Returns top N results (default 10 for highlights)

### 4. AI Summarization (Gemini 1.5 Flash)

**Weekly Scan Post**:
- Categorized article lists with AI-generated summaries (200 chars each)
- Highlights section with top 10 stories
- Article count table per category

**Analyst Opinion Post**:
- Executive summary of the week
- Key trends and patterns identified by AI
- Strategic implications for tech sector
- Regional analysis for APAC regulation content
- Actionable recommendations

**Configuration**: Set `GEMINI_API_KEY` environment variable in GitHub Actions secrets

### 5. Post Generation

```markdown
---
layout: post
title: "Weekly Tech News Scan - January 4, 2026"
date: 2026-01-04 08:00:00 -0500
categories: [newsbrief]
tags: [weekly-scan]
---
```

- **Timestamped filenames** prevent collision: `YYYY-MM-DD-HH-MM-{type}.md`
- **HTML anchors** for feed links (preserves feed HTML, prevents Markdown link mangling)
- **Front matter** with ISO 8601 timestamps and timezone support
- Posts written to `site/content/newsfeed/` as Astro content collection

### 6. Astro Site & Deployment

- **Content Collection**: All posts in `site/content/newsfeed/` indexed by Astro
- **Dynamic Pages**: `src/pages/newsfeed.astro` renders feed archive with search/filter
- **Static Generation**: Astro pre-renders all pages at build time
- **GitHub Actions**: Triggers build, deploys to GitHub Pages

---

## ⚙️ Configuration

### Adding/Removing Feeds

Edit [`scripts/config.yaml`](scripts/config.yaml):

```yaml
sources:
  - name: Your News Source
    url: https://example.com/feed.xml
    category: AI & LLM  # Existing: AI & LLM, Cloud, Cybersecurity, etc.
```

**Categories**: Assign existing category or create new one (becomes section header in generated posts)

### Adjusting Keyword Filters

```yaml
filters:
  keywords:
    - your-keyword
    - another-term
    # Literal strings, matched at word boundaries
```

Leave empty or omit to match all articles.

### Performance Tuning

```yaml
fuzz_threshold: 0.8          # Deduplication sensitivity (0.0-1.0, higher = stricter)
max_per_domain: 2            # Max articles per domain in highlights
max_results: 10              # Top N highlighted stories
request_retries: 3           # HTTP retry attempts
```

### Gemini AI Configuration

Set environment variable in GitHub Actions secrets:

```bash
GEMINI_API_KEY=your-google-api-key
```

Or locally before running:

```powershell
$env:GEMINI_API_KEY="your-api-key"
```

---

## 🛠️ Local Development

### Setup

```powershell
# Clone repository
git clone https://github.com/yourusername/feedmeup.git
cd feedmeup

# Create Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies for Astro
npm install

# Set Gemini API key (optional, for AI features)
$env:GEMINI_API_KEY="your-api-key"
```

### Run Aggregation Script

```powershell
python scripts/fetch_news.py
```

Check `site/content/newsfeed/` folder for generated markdown files.

### Start Development Server

```powershell
# Development mode with hot reload
npm run dev

# Visit http://localhost:3000
```

### Build for Production

```powershell
npm run build

# Preview production build
npm run preview
```

### Run Tests

```powershell
pytest tests/
```

---

## 📁 Project Structure

```
feedmeup/
├── scripts/
│   ├── fetch_news.py              # Main aggregation script
│   ├── config.yaml                # Feed sources & keyword filters
│   ├── test_negative_keywords.py  # Test filtering logic
│   ├── test_regex.py              # Regex testing utilities
│   └── __pycache__/
│
├── site/
│   ├── config.ts                  # Astro content config
│   ├── content/
│   │   ├── newsfeed/              # Generated news posts
│   │   ├── posts/                 # Manual blog posts
│   │   ├── about/                 # About page
│   │   ├── projects/              # Project portfolio
│   │   └── errors/                # Feed fetch error logs
│   └── assets/
│
├── src/
│   ├── pages/
│   │   ├── index.astro            # Home page
│   │   ├── newsfeed.astro         # News archive & search
│   │   ├── posts/                 # Post listing
│   │   ├── projects/              # Projects page
│   │   └── api/                   # Optional API routes
│   ├── components/                # Reusable Svelte/Astro components
│   ├── layouts/                   # Page layouts
│   ├── styles/                    # Global CSS & Tailwind
│   └── lib/                       # Utilities & schemas
│
├── .github/
│   └── workflows/
│       └── news.yml               # GitHub Actions automation
│
├── public/                        # Static assets
├── requirements.txt               # Python dependencies
├── package.json                   # Node/Astro dependencies
├── astro.config.mjs               # Astro configuration
├── tsconfig.json                  # TypeScript configuration
└── README.md                      # This file
```

---

## 🔄 GitHub Actions Workflow

**File**: [`.github/workflows/news.yml`](.github/workflows/news.yml)

**Trigger**: Monday 08:00 UTC (cron: `0 8 * * 1`) or manual dispatch

**Steps**:
1. Checkout repository
2. Setup Python 3.10 + Node.js
3. Install dependencies (pip + npm)
4. Run `scripts/fetch_news.py` to generate posts
5. Commit generated posts to main branch (if changes detected)
6. Astro build + deploy to GitHub Pages via GitHub's built-in Pages integration

---

## 📊 Data & Error Handling

### Feed Errors
Failing feeds are logged to `site/content/errors/` instead of crashing the pipeline:
- Filename: `YYYY-MM-DD-feed-error-TIMESTAMP.md`
- Includes HTTP status, exception details, and feed URL for debugging

### Deduplication & Quality
- **Duplicate prevention**: Fuzzy matching with domain diversity ensures breadth
- **Stale content filtering**: 30-day lookback prevents historical articles
- **HTML sanitization**: BeautifulSoup converts HTML to plain text, collapses whitespace
- **URL validation**: Percent-encoding handles special characters in feed links

### Retry & Backoff
- Exponential backoff strategy: `backoff_factor=0.3`
- Retries on HTTP 429 (rate limit), 500-504 (server errors)
- 15-second timeout per feed prevents hanging
- Session pooling (requests.Session) for connection reuse

---

## 🤝 Contributing

This is a personal automation project, but suggestions welcome:

1. **Feed Suggestions**: Open an issue with feed URL + category
2. **Bug Reports**: Include workflow logs (`_errors/` folder) and error details
3. **Feature Ideas**: Describe use case (e.g., new AI analysis, filtering logic)
4. **Improvements**: Suggest optimizations for performance or accuracy

---

## 📄 License

This project is open source for educational purposes.

**Respect RSS feed terms of service and rate limits when adapting this code.**

---

## 🙏 Acknowledgments

- **Astro**: Modern static site framework
- **Google Gemini**: AI summarization powered by Gemini 1.5 Flash
- **RapidFuzz**: Fast fuzzy string matching for deduplication
- **GitHub Actions**: Free automation platform
- **Feed Sources**: 40+ news organizations providing RSS feeds

---

## 📬 Quick Links

- **Issue Tracking**: Use [GitHub Issues](../../issues) for bug reports
- **Local Setup**: See [Local Development](#-local-development) section above
- **Configuration**: Edit [`scripts/config.yaml`](scripts/config.yaml) to customize feeds & filters

---

**Last Updated**: February 23, 2026