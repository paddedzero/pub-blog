# FeedMeUp News Aggregator - Project Specification

**Version**: 3.0  
**Last Updated**: January 5, 2026  
**Status**: Investigative Journalism Enhancement (Phase 3 - In Progress)

---

## 1. Project Vision & Goals

**feedmeup** is an automated, cloud-hosted news aggregation and curation platform that transforms raw RSS feeds into professionally formatted, AI-synthesized weekly blog posts published on GitHub Pages.

### Primary Goals
- **Automate weekly news curation** from 40+ trusted RSS sources across 6 categories
- **Apply intelligent filtering** using keyword matching and fuzzy deduplication
- **Synthesize insights** using AI (Gemini) to identify trends and cross-source patterns
- **Publish professionally** with Jekyll/Chirpy theme for GitHub Pages audience
- **Enable customization** through simple YAML configuration (no code changes needed)
- **Maintain high reliability** with retry logic, error handling, and validation

### Secondary Goals (Phase 2-3 - v2.0-3.0)
- **Enhanced Analyst Opinion**: Article-of-the-week format with multi-layered Gemini analysis
- **Smart article selection**: Surface pieces at the convergence of Cybersecurity + AI + Cloud
- **Expanded executive brief**: 5-sentence, 150-200 word contextualized summary
- **Historical context lookup**: Compare to past incidents, identify novel vs. recurring patterns
- **Risk/opportunity assessment**: 3-timeframe matrix (immediate, medium-term, strategic)
- **Investigative journalism depth** (Phase 3): Krebs-style technical deep-dives with paragraph-long analysis
- **Technical breakdowns**: Attack chains, CVE details, defense failure analysis
- **Threat intelligence**: Attribution, monetization, criminal ecosystem analysis
- **Actionable intelligence**: Concrete detection rules, mitigations, strategic recommendations

---

## 2. Architecture Overview

### 2.1 System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    FEEDMEUP NEWS AGGREGATOR                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐     ┌──────────────────┐                 │
│  │   40+ RSS Feeds  │────▶│  fetch_news.py   │                 │
│  │  (6 categories)  │     │  (Core Pipeline) │                 │
│  └──────────────────┘     └──────────────────┘                 │
│                                  │                              │
│                    ┌─────────────┼─────────────┐               │
│                    ▼             ▼             ▼               │
│              ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│              │ Keyword  │ │Deduplica-│ │  Format  │            │
│              │ Filtering│ │   tion   │ │  Posts   │            │
│              └──────────┘ └──────────┘ └──────────┘            │
│                    │             │             │               │
│                    └─────────────┼─────────────┘               │
│                                  ▼                              │
│                    ┌──────────────────────────┐                │
│                    │  Gemini AI Synthesis     │                │
│                    │  (Dual-Post Output)      │                │
│                    └──────────────────────────┘                │
│                                  │                              │
│                    ┌─────────────┴─────────────┐               │
│                    ▼                           ▼               │
│              ┌──────────┐               ┌──────────┐           │
│              │  Weekly  │               │ Analyst  │           │
│              │  Scan    │               │ Opinion  │           │
│              │  Post    │               │  Post    │           │
│              └──────────┘               └──────────┘           │
│                    │                           │               │
│                    └─────────────┬─────────────┘               │
│                                  ▼                              │
│                   ┌────────────────────────────┐               │
│                   │  GitHub Actions Workflow   │               │
│                   │  (Blue-Green Deployment)   │               │
│                   └────────────────────────────┘               │
│                                  │                              │
│                    ┌─────────────┴─────────────┐               │
│                    ▼                           ▼               │
│              ┌──────────┐               ┌──────────┐           │
│              │  main    │               │ gh-pages │           │
│              │ branch   │               │ branch   │           │
│              │(staging) │               │(live)    │           │
│              └──────────┘               └──────────┘           │
│                                          │                     │
│                                          ▼                     │
│                                  ┌──────────────┐              │
│                                  │ GitHub Pages │              │
│                                  │ + Jekyll     │              │
│                                  │ + Chirpy     │              │
│                                  └──────────────┘              │
│                                          │                     │
│                                          ▼                     │
│                         ┌────────────────────────────┐         │
│                         │ Live Blog with Navigation  │         │
│                         │ Dark Mode, Search, etc.    │         │
│                         └────────────────────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Source** | 40+ RSS feeds | News input from AI, Cloud, Cybersecurity, CVE, Threat Intel, APAC Regulatory |
| **Processing** | Python 3.10+ | Core pipeline: fetch, filter, deduplicate, format |
| **HTTP Client** | requests + retry adapter | Parallel feed retrieval with exponential backoff |
| **Feed Parsing** | feedparser 6.0.8+ | RFC 3339, RSS 2.0, Atom 1.0 support |
| **Fuzzy Matching** | RapidFuzz 2.15.1+ | Deduplication: 80% threshold (configurable) |
| **HTML Processing** | BeautifulSoup4 4.12.2+ | Summary extraction + plaintext conversion |
| **Config** | PyYAML 6.0+ | sources, keywords, performance settings |
| **AI Synthesis** | Google Gemini API | Trend analysis + opinion generation |
| **Blog Platform** | Jekyll 4.4.1 | Static site generator |
| **Theme** | Chirpy 7.4.1 | Professional Jekyll theme (remote_theme) |
| **Hosting** | GitHub Pages | Free, integrated with repository |
| **Automation** | GitHub Actions | Scheduled workflow (Monday 08:00 UTC) |
| **CI/CD** | pytest | Smoke tests on PR/push to main |
| **Git** | GitHub | Version control + deployment orchestration |

---

## 3. Data Flow & Pipeline

### 3.1 Weekly Execution Flow (Every Monday 08:00 UTC)

```
TRIGGER: Schedule or Manual Dispatch
    │
    ▼
┌─────────────────────────────────────┐
│ 1. Setup Environment                │
│   • Checkout main branch            │
│   • Install Python dependencies     │
│   • Install Ruby + Bundler          │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 2. Run fetch_news.py                │
│   • Load config.yaml                │
│   • Fetch from 40+ feeds (parallel) │
│   • Apply keyword filters           │
│   • Deduplicate by fuzzy matching   │
│   • Generate 2 posts (weekly scan + │
│     analyst opinion)                │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 3. Posts Generated in _posts/       │
│   • YYYY-MM-DD-HH-MM-weekly-scan.md │
│   • YYYY-MM-DD-HH-MM-analyst.md    │
│   • Jekyll front matter included    │
│   • 30-day lookback applied         │
│   • HTML anchor links (safe)        │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 4. Save Posts to Temp Storage       │
│   • mkdir -p /tmp/generated_posts   │
│   • Copy new posts before branch    │
│     switching                       │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 5. Deploy to gh-pages               │
│   • git checkout gh-pages           │
│   • Copy source files (preserve     │
│     _config.yml, Chirpy config)     │
│   • Add new posts from /tmp/        │
│   • Remove .nojekyll (enable Jekyll)│
│   • Commit + push to origin         │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 6. GitHub Pages Rebuild             │
│   • Detects removed .nojekyll       │
│   • Runs Jekyll build locally       │
│   • Applies Chirpy theme            │
│   • Generates site/_index.html etc. │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 7. Live Site Updated                │
│   • New posts visible               │
│   • Sidebar navigation active       │
│   • Theme styling applied           │
│   • Dark mode available             │
└─────────────────────────────────────┘
```

### 3.2 fetch_news.py Pipeline (Core Processing)

**Step 1: Load Configuration**
- Read `config.yaml`
- Load 40+ RSS source URLs organized by category
- Load keyword filter list (literal strings, word-boundary matched)
- Load performance settings: fuzz_threshold, max_per_domain, max_results, retries

**Step 2: Parallel Feed Fetching**
- Open global `requests.Session` with HTTPAdapter
- Retry policy: 3 retries, exponential backoff (0.3 factor), timeout 15s
- Retries on: [429, 500, 502, 503, 504] HTTP status codes
- User-Agent header set (avoids 403 from strict servers)
- Fetches each feed in parallel

**Step 3: Parse & Filter**
- For each entry in each feed:
  - Extract: title, summary/description, content, published date, link
  - Check: published within last 30 days (cutoff_date logic)
  - Match: keyword regex against title + summary + content (case-insensitive, word boundaries)
  - Save: matching entries to category buckets
- If feed fails: save error post to `_errors/YYYY-MM-DD-*.md` (don't crash)

**Step 4: Deduplication**
- Group entries with similar titles using RapidFuzz
- Threshold: 0.8 (configurable in config.yaml)
- Select most recent entry per group
- Enforce domain diversity: max 2 articles per normalized domain
- Sort: by group frequency descending, then recency
- Return: top 10 entries (configurable)

**Step 5: Format for Jekyll**
- Create two separate posts:
  1. **Weekly Scan**: categorized article lists with summaries
  2. **Analyst Opinion (v2.0)**: **Single article-of-the-week** with deep Gemini analysis:
     - Expanded Executive Brief (5 sentences, 150-200 words)
     - Historical Context (comparison to past incidents, novelty assessment)
     - Risk/Opportunity Matrix (3 timeframes: immediate, medium-term, strategic)
- Use HTML anchors instead of Markdown links (prevents feed HTML mangling)
- Truncate summaries: 250 chars for highlights, 200 for category articles
- Include front matter:
  ```yaml
  layout: post
  title: "Article of the Week: {category} — {date}"
  date: {ISO 8601 with timezone offset, America/New_York}
  categories: [analysis, opinion, {category}]
  ```

**Step 6: Write Posts**
- Filenames: `_posts/YYYY-MM-DD-HH-MM-{type}.md`
- Timestamp prevents collisions (if run multiple times same day)
- File path: repository `_posts/` directory

---

## 4.1 Enhanced Analyst Opinion Post (Phase 2 - v2.0)

### Design Goals
- **Target audience**: Cybersecurity professionals
- **Focus**: Single, high-impact article per week (article-of-the-week format)
- **Depth**: Multi-layered Gemini analysis instead of template commentary
- **Intelligence**: Historical context + forward-looking risk assessment

### Article Selection
- **Smart scoring**: Prioritize articles mentioning Cybersecurity + AI + Cloud convergence
- **Convergence keywords**: cybersecurity, AI, machine learning, cloud, threat, vulnerability, ransomware, defense, etc.
- **Selection**: Article with highest convergence_score (keyword_hits × recency × uniqueness)

### Post Structure (Article of the Week)
```
├─ Headline (Featured article title + summary)
├─ Executive Brief (5 sentences, 150-200 words)
│  - What happened + immediate impact
│  - Why it matters to organizations
│  - Key risk or opportunity
│  - Connection to broader trends
│  - What organizations should monitor
├─ Historical Context (Gemini-generated comparison)
│  - Similar past incidents (search 12-week lookback)
│  - What has changed or improved since then
│  - Is this novel or recurring with new tactics?
│  - What should we learn from history?
├─ Risk/Opportunity Matrix (3 timeframes)
│  - Immediate (0-30 days): What needs attention NOW
│  - Medium-term (30-90 days): What to prepare for
│  - Strategic (90+ days): How does this reshape landscape?
│  - For each: Threat/Opportunity type, Impact severity, Recommended action
└─ Analyst Note (Disclaimer + guidance)
```

### Implementation Details
- **New function**: `find_historical_context(keywords, lookback_weeks=12)`
  - Searches `_posts/` for similar topics from past 12 weeks
  - Returns list of {title, date, summary, keywords} for matching posts
  
- **New function**: `generate_gemini_opinion_analysis(article, category, historical_posts, config)`
  - Gemini Prompt 1: Expanded Executive Brief (150-200 words)
  - Gemini Prompt 2: Historical Context & Novelty Assessment
  - Gemini Prompt 3: Risk/Opportunity Matrix (3 timeframes)
  - Returns: {executive_brief, historical_context, risk_assessment}

- **Modified function**: `create_analyst_opinion_post()`
  - Now selects **1 article** (most trending) instead of 3
  - Calls `find_historical_context()` for past post lookup
  - Calls `generate_gemini_opinion_analysis()` for 3x deep Gemini analysis
  - Generates structured post with all 4 sections above

### Hybrid Model Strategy (v2.0)
**Philosophy**: Different tasks require different model capabilities. Optimize for speed vs. reasoning depth.

#### Model Assignment
| Task | Model | Why | Config |
|------|-------|-----|--------|
| **Weekly Scan Summaries** | `gemini-2.5-flash` | Fast, cost-effective for high-volume (40+ articles). Simple 2-3 sentence extraction. | `max_tokens=150`, `temp=0.7` |
| **Analyst Opinion Analysis** | `gemini-2.0-pro` | Superior reasoning for technical analysis, threat actor context, defense gaps. Stronger factual grounding. | `max_tokens=300-400`, `temp=0.3-0.4` |

**Rationale**:
- **Flash** optimizes for speed/cost → ideal for repetitive summarization
- **Pro** optimizes for reasoning depth → critical for investigative journalism quality
- **Cost impact**: 3 Pro calls/week vs. 40+ Flash calls = <$0.10/week incremental cost
- **Quality gain**: Krebs-style technical nuance, attribution patterns, defense failure analysis

**Technical Details**:
- Weekly Scan: Simple extraction, high volume → Flash's 2M token context sufficient
- Analyst Opinion: Complex reasoning (article + 12 weeks history + threat context) → Pro's 32k context ideal
- Lower temperature (0.3-0.4) for analyst opinion ensures factual consistency, avoids AI clichés

---

## 4.2 Investigative Journalism Enhancement (Phase 3 - v3.0)

### Design Philosophy
**Goal**: Transform analyst opinion from executive summaries into Krebs-style investigative articles with technical depth, threat intelligence, and actionable defense strategies.

**Inspiration**: [KrebsOnSecurity.com](https://krebsonsecurity.com/) - investigative cybersecurity journalism that:
- Explains technical vulnerabilities with specifics (CVE IDs, product versions, exploitation mechanics)
- Traces threat actor attribution and criminal infrastructure
- Connects incidents to broader patterns (historical evolution, monetization models)
- Provides actionable intelligence for security professionals AND non-technical readers

### Enhanced Post Structure (Investigative Format)
```
├─ Headline (Featured article title + trend context)
├─ Introduction (Category overview + article-of-the-week selection)
├─ Featured Article Summary (Original source excerpt)
├─ Technical Deep-Dive: What's Really Happening (400-600 words)
│  ├─ Paragraph 1: Incident/Vulnerability Technical Breakdown
│  │  - Attack chain or exploitation mechanics
│  │  - Specific technical details: CVEs, product versions, protocols
│  ├─ Paragraph 2: Defense Failure Analysis
│  │  - Why this succeeds (detection blind spots, config errors, vendor gaps)
│  │  - Concrete examples of what security controls fail
│  ├─ Paragraph 3: Historical Context & Evolution
│  │  - Past similar incidents and what's changed
│  │  - Success rates and attacker tactics evolution
│  └─ Paragraph 4: Real-World Impact
│     - Affected sectors, cascade effects, regulatory implications
│     - Why this matters for technical AND non-technical audiences
├─ Threat Intelligence: Follow the Money (300-400 words)
│  ├─ Paragraph 1: Attribution & Actor Profile
│  │  - Specific threat actors, APT groups, criminal forums
│  │  - Attribution clues from infrastructure and TTPs
│  ├─ Paragraph 2: Monetization & Infrastructure
│  │  - How attackers profit (ransomware, data sales, fraud)
│  │  - Criminal marketplace dynamics and supply chains
│  └─ Paragraph 3: Historical Evolution & Predictions
│     - Timeline of threat development
│     - Trend predictions with specific reasoning
├─ Defense Strategy: What Security Teams Should Do (600+ words)
│  ├─ Immediate Actions (0-30 days) - Tactical Response
│  │  - 3-5 specific, technical actions with concrete details
│  │  - Detection rules, patch priorities, configuration hardening
│  │  - Actual CVE IDs, product names, SIEM queries
│  ├─ Medium-Term Planning (30-90 days) - Process & Architecture
│  │  - 3-4 strategic improvements
│  │  - Architecture changes, process improvements, capability gaps
│  ├─ Long-Term Vision (90+ days) - Strategic Transformation
│  │  - 2-3 strategic shifts
│  │  - Philosophy changes, investment priorities, resilience building
│  └─ Each action tied to the technical analysis (no generic advice)
└─ Analyst Note (Disclaimer + validation guidance)
```

### Gemini Prompt Strategy (3 Investigative Prompts)

#### Prompt 1: Technical Deep-Dive & Opinion Analysis
- **Purpose**: Multi-paragraph technical breakdown with investigative depth
- **Length**: 400-600 words (3-4 paragraphs)
- **Content**:
  - Attack chains or vulnerability exploitation mechanics
  - Why security controls fail (specific detection gaps)
  - Historical comparison and technique evolution
  - Real-world impact for technical and non-technical readers
- **Tone**: Investigative journalism (like Brian Krebs)
- **Model**: `gemini-2.0-pro`, `max_tokens=800`, `temp=0.4`

#### Prompt 2: Threat Intelligence & Ecosystem Context
- **Purpose**: Attribution, monetization, criminal infrastructure analysis
- **Length**: 300-400 words (2-3 paragraphs)
- **Content**:
  - Specific threat actors, APT groups, criminal forums
  - Follow the money: ransomware payments, data sales, infrastructure
  - Historical evolution timeline and trend predictions
- **Specificity**: Name actors, tools, hosting providers, ransom amounts
- **Model**: `gemini-2.0-pro`, `max_tokens=600`, `temp=0.4`

#### Prompt 3: Defense Strategy & Actionable Intelligence
- **Purpose**: Concrete detection rules, mitigations, strategic actions
- **Length**: 600+ words (3 timeframes with multiple actions each)
- **Content**:
  - Immediate (0-30 days): 3-5 technical actions (CVEs, queries, configs)
  - Medium-term (30-90 days): 3-4 strategic improvements (architecture, process)
  - Long-term (90+ days): 2-3 strategic transformations (philosophy shifts)
- **Specificity**: Actual CVE IDs, product names, SIEM query syntax, vendor names
- **Model**: `gemini-2.0-pro`, `max_tokens=800`, `temp=0.3` (lowest for factual accuracy)

### Implementation Functions

**`generate_gemini_opinion_analysis()`** - Completely redesigned:
- Input: article + category + historical_posts
- Output: `{technical_analysis, threat_intelligence, defense_strategy}`
- 3 sequential Gemini Pro calls (not parallel to preserve context flow)
- Each prompt builds on investigative journalism principles
- Graceful fallback if Gemini unavailable

**`create_analyst_opinion_post()`** - Updated structure:
- New section headings: "Technical Deep-Dive", "Threat Intelligence", "Defense Strategy"
- Support for 1000+ word articles (vs. previous 500 word summaries)
- Maintains single article-of-the-week focus

### Key Differences: Phase 2 vs. Phase 3

| Aspect | Phase 2 (Executive Summary) | Phase 3 (Investigative Journalism) |
|--------|----------------------------|-----------------------------------|
| **Length** | 500-600 words total | 1300-1600 words total |
| **Executive Brief** | 5 sentences (150-200 words) | Technical Deep-Dive (400-600 words, 4 paragraphs) |
| **Historical Context** | 3-4 sentences comparison | Integrated into Technical Deep-Dive + Threat Intel |
| **Risk Assessment** | 3-timeframe matrix (generic) | Defense Strategy (specific, technical, actionable) |
| **Technical Depth** | Surface-level explanation | Attack chains, CVE details, defense failure analysis |
| **Attribution** | Not included | Threat actors, infrastructure, monetization |
| **Actionability** | Generic recommendations | Concrete detection rules, patch priorities, SIEM queries |
| **Tone** | Executive summary | Investigative journalism (Krebs-style) |
| **Audience** | CISOs, security leaders | Security professionals + non-technical readers |
| **Token Budget** | 300-400 per prompt | 600-800 per prompt |

### Expected Output Quality

**Before (Phase 2)**:
> "The Acme Health ransomware breach exposes patient data. Organizations should improve security posture and conduct regular training. This represents an escalation of healthcare targeting. Immediate action: patch systems. Medium-term: conduct tabletop exercises. Long-term: adopt zero-trust."

**After (Phase 3)**:
> "The Acme Health ransomware breach isn't just another data leak—it's a case study in how attackers exploit VMware ESXi's authentication bypass (CVE-2024-XXXX) to encrypt entire virtual machine estates in under 90 minutes. While VMware issued patches in Q2 2024, Shodan reveals 12,000+ internet-exposed ESXi hosts still running vulnerable versions, with 40% in healthcare. 
> 
> This mirrors the 2022 Royal ransomware campaign, but today's attackers chain this with Mimikatz credential theft to pivot to backup systems—a tactic we first documented in our October 2023 analysis of the [related incident]. The strategic failure: healthcare CISOs continue treating virtualization platforms as infrastructure rather than crown jewels, leaving them unmonitored by EDR.
>
> [3 more paragraphs of technical analysis...]
> 
> **Threat Intelligence**: The Scattered Spider group has been attributed to this campaign based on infrastructure overlaps with their previous healthcare targeting. They monetize via double-extortion: encrypting systems while threatening to leak 2.3TB of patient records on their leak site (hosted on Tor via bulletproof hosting provider [redacted]). Ransom demands average $4.5M in Monero, with payments laundered through [specific mixer]..."

**Configuration Extension (config.yaml)**
```yaml
synthesis:
  enable_opinion_post: true
  enable_historical_context: true         # NEW (v2.0)
  opinion_lookback_weeks: 12              # NEW (v2.0)
  convergence_keywords:                   # NEW (v2.0)
    - cybersecurity
    - ai
    - cloud
    - machine learning
    - threat
    - vulnerability
    - ransomware
    - data breach
    - attack
    - defense
```

---

## 4 (original). Configuration Management

### 4.1 config.yaml Structure

```yaml
# RSS Sources (40+ configured)
sources:
  - name: "Product Hunt"
    url: "https://www.producthunt.com/feed"
    category: "AI/LLM"
  - name: "OpenAI Blog"
    url: "https://openai.com/blog/feed.xml"
    category: "AI/LLM"
  # ... 40+ more sources across:
  # - AI/LLM (15 sources)
  # - Cloud (10 sources)
  # - Cybersecurity (10 sources)
  # - CVE/Vulnerability (5 sources)
  # - Threat Intelligence (5 sources)
  # - APAC Regulatory (5 sources)

# Keyword Filters (literal strings, word-boundary matched)
filters:
  keywords:
    - "artificial intelligence"
    - "machine learning"
    - "LLM"
    - "cloud computing"
    - # ... more keywords ...
    # Empty list or omit key: matches ALL articles (default behavior)

# Performance & Deduplication
performance:
  fuzz_threshold: 0.8              # Fuzzy match threshold (0.0-1.0)
  max_per_domain: 2                # Max articles per normalized domain
  max_results: 10                  # Top N stories for highlights
  request_retries: 3               # HTTP retry attempts
  timeout_seconds: 15              # Request timeout
  lookback_days: 30                # Only fetch entries from last N days
```

### 4.2 Default Fallback Values

If config.yaml values missing, code falls back to:
```python
DEFAULTS = {
    'fuzz_threshold': 0.8,
    'max_per_domain': 2,
    'max_results': 10,
    'request_retries': 3,
    'timeout_seconds': 15,
    'lookback_days': 30
}
```

### 4.3 Configuration Modification Workflow

| Change | File | Steps | When Effective |
|--------|------|-------|-----------------|
| **Add RSS source** | config.yaml | 1. Edit sources list 2. Assign category 3. Test locally | Next scheduled run or manual dispatch |
| **Update keywords** | config.yaml | 1. Edit filters.keywords 2. Test locally | Next scheduled run |
| **Change deduplication** | config.yaml | 1. Adjust fuzz_threshold 2. Test locally | Next scheduled run |
| **Adjust timeouts/retries** | config.yaml | 1. Edit performance settings 2. Test locally | Next scheduled run |

---

## 5. GitHub Pages & Jekyll Integration

### 5.1 Deployment Branch Strategy

**Main Branch** (`main`)
- Source code: `fetch_news.py`, `config.yaml`, `requirements.txt`
- Tests: `tests/test_smoke.py`, CI configuration
- Workflow definition: `.github/workflows/news.yml`
- Theme config: `_config.yml` (references Chirpy remote_theme)
- Role: Staging/development, receives updates from PRs

**gh-pages Branch** (`gh-pages`)
- **Deployed files**:
  - `_config.yml` (includes `remote_theme: cotes2020/jekyll-theme-chirpy`)
  - `_posts/` (generated weekly news posts)
  - `_data/` (theme data files)
  - `_tabs/` (sidebar navigation: categories, tags, archives, about, subscribe)
  - `assets/` (CSS, JS, images)
  - `Gemfile` + `Gemfile.lock` (Jekyll dependencies)
  - `index.md` (home page)
- **NOT deployed**:
  - `.nojekyll` file (must be removed to enable Jekyll rebuild)
  - `fetch_news.py`, `config.yaml`, test files (not needed on live site)
- Role: Production/live site, served by GitHub Pages

### 5.2 Jekyll Theme: Chirpy 7.4.1

**Theme Configuration** (in `_config.yml`)
```yaml
remote_theme: cotes2020/jekyll-theme-chirpy
plugins:
  - jekyll-feed
  - jekyll-remote-theme
  - jekyll-seo-tag
  - jekyll-archives

collections:
  tabs:
    output: true
    sort_by: order
```

**Sidebar Navigation** (auto-generated from `_tabs/` directory)
- **Automatic**: HOME link (generated by Chirpy)
- **From `_tabs/` files**:
  - `categories.md` → CATEGORIES (layout: categories)
  - `tags.md` → TAGS (layout: tags)
  - `archives.md` → ARCHIVES (layout: archives)
  - `about.md` → ABOUT (custom user info)
  - `subscribe.md` → SUBSCRIBE (mailing list signup form)

**Post Display**
- Layout: `post` (from Chirpy theme)
- Auto-generates archive pages, category pages, tag clouds
- Dark mode toggle (user preference)
- Search functionality (via search.json)
- TOC generation (table of contents)
- Social sharing buttons

### 5.3 Deployment Process (Workflow Steps)

**Workflow File**: `.github/workflows/news.yml`

1. **Checkout main** → Get source code
2. **Setup Python** → Install Python 3.10+
3. **Setup Ruby** → For Jekyll (required for local build)
4. **Install dependencies** → `pip install -r requirements.txt`, `bundle install`
5. **Run fetch_news.py** → Generate posts in `_posts/`
6. **Capture posts** → `mkdir -p /tmp/generated_posts && cp _posts/* /tmp/generated_posts/`
7. **Switch to gh-pages** → `git checkout gh-pages` (or create if missing)
8. **Deploy source files** → `cp -r /tmp/main_source/* .` (preserves _config.yml, theme files)
9. **Restore generated posts** → `cp /tmp/generated_posts/* _posts/`
10. **Remove .nojekyll** → `rm -f .nojekyll` (enables GitHub Pages Jekyll rebuild)
11. **Commit & push** → Only commits if _posts/ changed (prevents empty commits)

**Critical Detail**: `.nojekyll` removal signals GitHub Pages to run Jekyll build on the source files (not serve pre-built HTML)

---

## 6. Error Handling & Resilience

### 6.1 Feed Fetch Failures

| Error | Handling |
|-------|----------|
| HTTP 403/404 | Save error post to `_errors/YYYY-MM-DD-*.md` (don't crash) |
| Parse failure (bozo exception) | Log details, save error post with exception info |
| Timeout (15s) | Retry 3x with exponential backoff |
| 429/503/504 | Retry 3x with exponential backoff |
| No entries in feed | Log warning, continue to next feed |
| Malformed XML | feedparser handles gracefully, log bozo exception |

### 6.2 URL & Content Sanitization

| Operation | Function | Behavior |
|-----------|----------|----------|
| **Validate URLs** | `sanitize_url()` | Percent-encodes special chars, returns None if invalid |
| **Extract text** | `clean_summary()` | BeautifulSoup extracts plaintext, collapses whitespace |
| **HTML links** | Use anchors not Markdown | Prevents feed HTML mangling (e.g., `<a href="...">text</a>` instead of `[text]()`) |
| **Missing links** | Skip href attribute | Safely handles articles without URLs |

### 6.3 Timezone Handling

- **Default timezone**: `America/New_York` (US Eastern)
- **All times**: Stored as ISO 8601 with offset (e.g., `2026-01-04T14:30:00-05:00`)
- **Cutoff date**: Relative to deployment time (last 30 days)
- **Library**: `zoneinfo` (Python 3.9+), requires `tzdata 2024.1+`

### 6.4 Data Integrity

- **30-day lookback**: Prevents historical data flooding
- **Duplicate domain enforcement**: Max 2 per domain prevents over-weighting single sources
- **Keyword matching word boundaries**: Prevents false positives (matches "ai", not "paid")
- **Timestamp in filenames**: Prevents post collision if run multiple times same day
- **Conditional commits**: Only commits if new posts differ from previous (avoids empty commits)

---

## 7. Testing & Quality Assurance

### 7.1 Test Coverage

**File**: `tests/test_smoke.py`
```python
# Minimal smoke tests:
- test_module_imports()      # Verify fetch_news.py imports cleanly
- test_constants_exist()     # Verify DEFAULTS dict, category names
```

**Execution**
```bash
# Local testing
pytest -q              # Quiet mode
python -m pytest       # Alternative invocation

# CI/CD testing
# Runs on Python 3.10 and 3.11
# Matrix: os=ubuntu-latest, python-version=[3.10, 3.11]
```

### 7.2 CI/CD Workflows

**`.github/workflows/ci.yml`** (PR/Push to main)
- Triggers: On push or pull request to main
- Matrix: Python 3.10, 3.11 on ubuntu-latest
- Steps:
  - Checkout code
  - Setup Python
  - Install dependencies
  - Run pytest
  - Optional: flake8 (linting, non-blocking)
- Gate: Must pass before merge to main

**`.github/workflows/news.yml`** (Weekly Schedule)
- Triggers: Monday 08:00 UTC or manual dispatch
- Steps: [As detailed in Section 5.3]
- Deployment: Blue-green with rollback on validation failure

---

## 8. Developer Workflows

### 8.1 Local Development Setup

```bash
# 1. Clone repository
git clone https://github.com/paddedzero/feedmeup.git
cd feedmeup

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run pipeline locally
python fetch_news.py

# 5. Check output
ls -la _posts/           # New posts generated
cat _posts/2026-*.md    # View post content

# 6. Run tests
pytest tests/
```

### 8.2 Adding a New RSS Source

**Step 1**: Edit `config.yaml`
```yaml
sources:
  # ... existing sources ...
  - name: "My News Site"
    url: "https://example.com/feed.xml"
    category: "AI/LLM"  # Use existing or create new
```

**Step 2**: Test locally
```bash
python fetch_news.py
```

**Step 3**: Verify output
```bash
grep -r "My News Site" _posts/
```

**Step 4**: Commit and push
```bash
git add config.yaml
git commit -m "Add: My News Site RSS feed to AI/LLM category"
git push origin main
```

**When effective**: Next scheduled workflow run (Monday 08:00 UTC) or manual dispatch

### 8.3 Updating Keyword Filters

**Step 1**: Edit `config.yaml`
```yaml
filters:
  keywords:
    - "quantum computing"      # Add new keyword
    - "blockchain"             # Add new keyword
    # - "old keyword"          # Remove by commenting out
```

**Step 2**: Test locally
```bash
python fetch_news.py
```

**Step 3**: Verify filtering
```bash
wc -l _posts/*.md              # Count articles (should differ if keywords changed)
```

**Step 4**: Commit and push
```bash
git add config.yaml
git commit -m "Update: Add 'quantum computing' and 'blockchain' to keyword filters"
git push origin main
```

**When effective**: Next scheduled run

### 8.4 Debugging a Failing Feed

**Enable debug logging**:
```bash
LOG_LEVEL=DEBUG python fetch_news.py
```

**Check error posts**:
```bash
ls _errors/
cat _errors/2026-01-04-*.md
```

**Analyze specific feed**:
```bash
# Temporarily modify config.yaml to test single source
# Comment out all sources except the problematic one
# Run fetch_news.py
# Check logs for detailed error messages
```

### 8.5 Extending Filtering Logic

**Current filtering**: Keyword word-boundary regex matching

**To add time-based filters**:
1. Modify `entry_matches()` function
2. Add time range check (e.g., published after specific date)
3. Test locally with sample feeds

**To add source-specific rules**:
1. Extend loop over sources in `main()`
2. Add conditional logic for specific source names
3. Apply different filter thresholds per source

---

## 9. Deployment Checklist

### 9.1 Pre-Deployment Validation

- [ ] All tests pass: `pytest -q`
- [ ] No lint errors: `flake8 fetch_news.py` (if enforced)
- [ ] config.yaml valid YAML syntax: `python -c "import yaml; yaml.safe_load(open('config.yaml'))"`
- [ ] At least one feed URL accessible: manual test with curl/requests
- [ ] fetch_news.py runs without errors locally
- [ ] Posts generated in `_posts/` directory
- [ ] Post frontmatter valid YAML
- [ ] No API secrets hardcoded in config

### 9.2 Post-Deployment Validation

- [ ] Workflow completes successfully (check GitHub Actions tab)
- [ ] No errors in workflow logs
- [ ] gh-pages branch updated with new posts
- [ ] `_config.yml` still exists on gh-pages (preserved)
- [ ] `.nojekyll` file deleted from gh-pages
- [ ] GitHub Pages build succeeds (check Pages settings)
- [ ] Live site loads: https://paddedzero.github.io/feedmeup
- [ ] Sidebar navigation visible (Categories, Tags, Archives, About, Subscribe)
- [ ] New posts visible on live site
- [ ] Post content formatted correctly (no broken links, proper styling)
- [ ] Dark mode toggle works
- [ ] Mobile responsive (test on phone)

---

## 10. Monitoring & Maintenance

### 10.1 Regular Checks

| Check | Frequency | Action |
|-------|-----------|--------|
| **Feed health** | Weekly (after workflow) | Review `_errors/` directory for failed feeds |
| **Post quality** | Weekly | Verify posts have adequate content, no duplicates |
| **Site functionality** | Weekly | Test navigation, search, dark mode |
| **Dependencies** | Monthly | Check for security updates in `requirements.txt` |
| **Configuration** | As needed | Add/remove sources, update keywords |
| **Disk usage** | Quarterly | Archive old posts if `_posts/` grows >1GB |

### 10.2 Common Issues & Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| **No posts generated** | `_posts/` empty after workflow | Check `_errors/` for feed failures; verify keywords match articles |
| **Posts don't appear on site** | New posts in `_posts/` but not visible | Wait 5 min for GitHub Pages build; check Actions tab for build errors |
| **Sidebar tabs missing** | Only HOME link visible | Verify `_config.yml` on gh-pages has `remote_theme` and `collections.tabs`; check `.nojekyll` deleted |
| **Posts cut off/truncated** | Summaries incomplete | Adjust `max_summary_length` in fetch_news.py (currently 250 chars) |
| **Too many duplicates** | Articles repeated in output | Lower `fuzz_threshold` in config.yaml (currently 0.8) |
| **Feed fetch timeout** | Specific feed fails 403/404 | Feed may be down; remove from config.yaml; try alternative source |
| **Gemini API quota exceeded** | Workflow fails on synthesis | Wait for quota reset or upgrade API plan |

---

## 11. API & External Service Dependencies

### 11.1 APIs Used

| Service | Purpose | Status | Cost |
|---------|---------|--------|------|
| **Google Gemini API** | AI synthesis for posts | Active | Usage-based pricing |
| **GitHub API** (implicit) | Repository access via Actions | Free (included) | Free for public repos |
| **GitHub Pages** | Static site hosting | Free | Free |
| **RSS Feeds** (40+ sources) | News content | Active | Free (varies by source) |

### 11.2 API Configuration

**Gemini API Key**
- Location: GitHub Actions secrets (not in code)
- Required for: Analyst Opinion post generation
- If missing: Workflow fails with clear error message
- Quota: Check Google Cloud Console dashboard

---

## 12. Scalability & Performance

### 12.1 Current Limits

| Metric | Current | Limit | Mitigation |
|--------|---------|-------|-----------|
| **RSS sources** | 40 | 100+ feasible | Parallel fetching + retry logic |
| **Posts per week** | 2 (scan + opinion) | 10+ feasible | Modify workflow to generate more |
| **Articles per post** | ~50-100 | 1000+ feasible | Adjust deduplication threshold |
| **Build time** | ~3-5 min | <10 min | Optimize if exceeds GitHub timeout |
| **Repository size** | ~50MB | 1GB hard limit | Archive old posts if needed |

### 12.2 Optimization Opportunities

- **Parallel feed fetching**: Already implemented via `requests.Session`
- **Caching**: Could cache fetches to avoid re-downloading unchanged feeds
- **Incremental updates**: Could track last fetch time per source
- **Async processing**: Could use `aiohttp` instead of `requests` for faster fetching

---

## 13. Security Considerations

### 13.1 Secrets Management

| Secret | Location | Usage | Rotation |
|--------|----------|-------|----------|
| **Gemini API Key** | GitHub Actions secrets | AI synthesis | As needed (via GCP) |
| **GitHub Token** | Actions auto-generated | Git push to gh-pages | Auto-rotated by Actions |

### 13.2 Input Validation

- **config.yaml**: Parsed with `yaml.safe_load()` (not eval)
- **RSS feeds**: Parsed with `feedparser` (tolerates malformed XML)
- **URLs**: Validated and percent-encoded by `sanitize_url()`
- **Content**: HTML cleaned by `BeautifulSoup` (strips scripts, dangerous tags)

### 13.3 Repository Permissions

- **Main branch**: Protected (requires PR review before merge)
- **gh-pages branch**: Only written by Actions workflow (restricted via fine-grained tokens)
- **Secrets**: Only readable by workflows, masked in logs

---

## 14. Project Maintenance & Evolution

### 14.1 Known Limitations

1. **Fixed schedule**: Only runs Monday 08:00 UTC (configurable but not dynamic)
2. **No filtering by date range**: Only lookback window (no forward date filtering)
3. **Single timezone**: America/New_York only (could be parameterized)
4. **No personalization**: Same posts for all users (could add user preferences)
5. **No real-time alerts**: Weekly only (could add daily digest option)
6. **Manual source management**: Sources edited in YAML, not UI

### 14.2 Future Roadmap

**Phase 1** (Current): Stable weekly news aggregation + Jekyll deployment
**Phase 2**: Admin UI for managing sources/keywords without code
**Phase 3**: Real-time feed monitoring + daily email alerts
**Phase 4**: Personalized feeds per user + preference storage
**Phase 5**: Multi-language support + regional customization

---

## 15. Contacts & Support

### 15.1 Repository Information

- **GitHub**: https://github.com/paddedzero/feedmeup
- **Pages**: https://paddedzero.github.io/feedmeup
- **Owner**: @paddedzero

### 15.2 Troubleshooting Resources

1. Check `.github/copilot-instructions.md` for detailed API docs
2. Review `_errors/` directory for feed-specific failures
3. Check GitHub Actions logs for workflow issues
4. Search GitHub Issues for similar problems
5. Enable `LOG_LEVEL=DEBUG` for verbose output

---

## 16. Document History

| Version | Date | Changes |
|---------|------|---------|
| 3.0 | 2026-01-05 | Phase 3: Investigative journalism transformation — Technical deep-dives (400-600 words), threat intelligence & attribution, actionable defense strategy with detection rules, Krebs-style investigative tone |
| 2.0 | 2026-01-05 | Phase 2: Enhanced analyst opinion — article-of-the-week format, historical context lookup, risk/opportunity matrix, multi-prompt Gemini analysis, hybrid model strategy (Flash for summaries, Pro for opinions) |
| 1.0 | 2026-01-04 | Initial project spec: full architecture, workflows, deployment, maintenance |

---

**Document Status**: Phase 3 Implementation Complete  
**Last Reviewed**: January 5, 2026  
**Next Review**: Q1 2026 (post-production validation)
