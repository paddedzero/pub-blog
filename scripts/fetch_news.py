import feedparser
import yaml
import re
import requests
import logging
import os
import textwrap
import base64
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from requests.utils import requote_uri
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

# rapidfuzz for fuzzy matching
from rapidfuzz.fuzz import ratio as rf_ratio

# requests retry
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Web scraping module for non-RSS feeds
from scraper import scrape_site, is_scraping_candidate

# Semantic deduplication (Group 2 improvement)
try:
    from sentence_transformers import SentenceTransformer
    from scipy.spatial.distance import cosine
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    logging.warning("sentence-transformers or scipy not installed; semantic deduplication disabled")

# Gemini API for summarization (Phase 1) - using new google-genai SDK
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("google-genai not installed; Gemini summarization disabled")

# --- ANSI color codes (kept for console output) ---
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
GREY = "\033[90m"

CONFIG_FILE = "scripts/config.yaml"
POSTS_DIR = Path("site/content/newsfeed")
ERRORS_DIR = Path("site/content/errors")

# Distribution staging directories (for push to feedmeup)
DIST_POSTS_DIR = Path("temp_dist/site/content/newsfeed")
DIST_ERRORS_DIR = Path("temp_dist/site/content/errors")

# Use America/New_York as the local timezone
LOCAL_TZ = ZoneInfo("America/New_York")

# Defaults (can be overridden by config.yaml)
DEFAULTS = {
    "fuzz_threshold": 0.8,
    "max_per_domain": 2,
    "max_results": 10,
    "request_retries": 3,
    "request_backoff": 0.3,
    "request_timeout": 15,
    "request_status_forcelist": [429, 500, 502, 503, 504],
    "log_level": "INFO",
}

# Module-level sessions (initialized in main)
SESSION = None  # requests.Session for HTTP calls
GEMINI_CLIENT = None  # google.genai.Client for summarization (new SDK)

# Semantic model & embedding cache (initialized on demand)
SEMANTIC_MODEL = None  # SentenceTransformer model
EMBEDDING_CACHE = {}  # {text_hash: embedding_vector}
SEMANTIC_CACHE_DIR = Path(".semantic_cache")  # Cache directory for embeddings


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logging.warning("config.yaml not found, using defaults")
        return {}
    except Exception:
        logging.exception("Failed to load config.yaml; using defaults")
        return {}


def compile_keywords_pattern(keywords, config=None):
    """Compile keywords into regex pattern, with optional synonym expansion (Group 2.2).
    
    If config provided, expands keywords using synonym_map.
    Returns regex pattern or None (if no keywords, matches everything).
    """
    # If no keywords configured, return None -> match everything
    if not keywords:
        return None
    
    # Expand keywords with synonyms if config available
    if config:
        keywords = expand_keywords_with_synonyms(keywords, config)
    
    # Remove duplicates while preserving order
    keywords = list(dict.fromkeys(keywords))
    
    escaped = [re.escape(k) for k in keywords]
    pattern = r"(?i)\b(" + "|".join(escaped) + r")\b"
    return re.compile(pattern)


def write_dual_output(filename, content):
    """Write content to both preview (POSTS_DIR) and distribution (DIST_POSTS_DIR) paths.
    
    This ensures fetch_news.py outputs are available for:
    1. Local preview in pub-blog (site/content/newsfeed/)
    2. Distribution staging for feedmeup (temp_dist/site/content/newsfeed/)
    
    Args:
        filename: Path object for the preview file (under POSTS_DIR or ERRORS_DIR)
        content: Full file content (frontmatter + body)
    """
    # Write to preview path (original behavior)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    logging.info("[PREVIEW] Written: %s", filename)
    
    # Determine distribution path by replacing the base directory
    filename_path = Path(filename)
    if str(filename_path).startswith(str(ERRORS_DIR)):
        dist_filename = DIST_ERRORS_DIR / filename_path.relative_to(ERRORS_DIR)
    elif str(filename_path).startswith(str(POSTS_DIR)):
        dist_filename = DIST_POSTS_DIR / filename_path.relative_to(POSTS_DIR)
    else:
        logging.warning("[DIST] Unknown base path for %s; skipping distribution copy", filename)
        return
    
    # Write to distribution path
    dist_filename.parent.mkdir(parents=True, exist_ok=True)
    with open(dist_filename, "w", encoding="utf-8") as f:
        f.write(content)
    logging.info("[DIST] Written: %s", dist_filename)


def save_error_post(feed_url, error_message):
    """Save feed fetch error into _errors folder instead of _posts."""
    try:
        ERRORS_DIR.mkdir(parents=True, exist_ok=True)
        now_local = datetime.now(LOCAL_TZ)
        date_str = now_local.strftime("%Y-%m-%d")
        slug = re.sub(r'[^a-z0-9]+', '-', f"feed-error-{date_str}").strip('-')
        filename = ERRORS_DIR / f"{date_str}-{slug}.md"

        # Astro content collection frontmatter for error posts
        front_matter = f"""---
title: "Feed Fetch Error - {date_str}"
description: "Error encountered while fetching RSS feed"
pubDate: {now_local.strftime('%Y-%m-%d')}
categories: ["error"]
tags: ["error", "feed-fetch"]
author: "feedmeup"
aiGenerated: false
---

"""
        content = f"**Failed to fetch feed:** {feed_url}\n\n**Error:** {error_message}\n"
        write_dual_output(filename, front_matter + content)
        logging.error("[ERROR POST] Saved to %s", filename)
    except Exception:
        logging.exception("Failed to write error post")


def init_requests_session(retries=None, backoff=None, timeout=None, status_forcelist=None):
    """Initialize requests.Session with retry adapter and store globally."""
    global SESSION
    r = int(retries) if retries is not None else DEFAULTS["request_retries"]
    b = float(backoff) if backoff is not None else DEFAULTS["request_backoff"]
    status_list = status_forcelist if status_forcelist is not None else DEFAULTS["request_status_forcelist"]

    session = requests.Session()
    retry = Retry(
        total=r,
        backoff_factor=b,
        status_forcelist=list(status_list),
        allowed_methods=frozenset(["GET", "POST", "HEAD", "OPTIONS"])
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    SESSION = session
    return session


def init_gemini_client(api_key, model="gemini-2.5-flash"):
    """
    Initialize Gemini API client for article summarization (Phase 1).
    Uses the new google-genai SDK (unified Google Gen AI SDK).
    
    Args:
        api_key: Gemini API key (from config or environment)
        model: Model name (default: gemini-2.5-flash, latest lightweight & fast)
    
    Returns:
        genai.Client object, or None if Gemini unavailable
    
    Raises:
        ValueError: If api_key is missing or invalid
    """
    global GEMINI_CLIENT
    
    if not GEMINI_AVAILABLE:
        logging.warning("Gemini not available (google-genai not installed)")
        return None
    
    if not api_key or not api_key.strip():
        logging.warning("GEMINI_API_KEY not provided; Gemini summarization disabled")
        return None
    
    try:
        GEMINI_CLIENT = genai.Client(api_key=api_key)
        logging.info("[GEMINI] Initialized client with model: %s", model)
        return GEMINI_CLIENT
    except Exception as e:
        logging.error("[GEMINI] Failed to initialize: %s", str(e))
        return None


def summarize_with_gemini(entry, keywords, prompt_template, config):
    """
    Summarize an article using Gemini API (Phase 1).
    Uses the new google-genai SDK (unified Google Gen AI SDK).
    
    Calls Gemini to generate a 2-3 sentence summary emphasizing keywords.
    If API fails, falls back to clean_summary() for graceful degradation.
    
    Args:
        entry: Feed entry dict with 'title', 'summary', 'description', 'content'
        keywords: List of keywords to emphasize
        prompt_template: Prompt template string with {keywords} and {article_text} placeholders
        config: Config dict with synthesis/error_handling settings
    
    Returns:
        dict: {
            'title': str (original or enhanced),
            'excerpt': str (2-3 sentences from Gemini or fallback),
            'keywords_hit': [str] (keywords found in article)
        }
    """
    if not GEMINI_CLIENT or not GEMINI_AVAILABLE:
        # Fallback: use existing clean_summary
        excerpt = clean_summary(entry.get("summary", "") or entry.get("description", ""))
        return {
            'title': entry.get('title', 'No Title'),
            'excerpt': excerpt,
            'keywords_hit': []
        }
    
    try:
        # Extract raw article text
        raw_summary = entry.get("summary", "") or entry.get("description", "")
        article_text = clean_summary(raw_summary)
        
        if not article_text or len(article_text.strip()) < 10:
            # Too short; skip Gemini, use fallback
            logging.debug("[GEMINI] Article text too short, using fallback")
            return {
                'title': entry.get('title', 'No Title'),
                'excerpt': article_text,
                'keywords_hit': []
            }
        
        # Build Gemini prompt
        keywords_str = ", ".join(keywords) if keywords else "none"
        prompt = prompt_template.format(
            keywords=keywords_str,
            article_text=article_text[:2000]  # Limit to 2000 chars for API cost
        )
        
        # Call Gemini API using new google-genai SDK
        response = GEMINI_CLIENT.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "max_output_tokens": 150,
                "temperature": 0.7,
            }
        )
        
        excerpt = response.text.strip() if response.text else ""
        
        # Validate response
        if not excerpt or len(excerpt) < 10:
            logging.debug("[GEMINI] Invalid response for '%s'; using fallback", entry.get('title'))
            excerpt = clean_summary(raw_summary)
        
        # Check which keywords were hit
        article_lower = article_text.lower()
        keywords_hit = [kw for kw in keywords if kw.lower() in article_lower]
        
        logging.debug("[GEMINI] Summarized '%s' (keywords hit: %s)", entry.get('title'), keywords_hit)
        
        return {
            'title': entry.get('title', 'No Title'),
            'excerpt': excerpt,
            'keywords_hit': keywords_hit
        }
    
    except Exception as e:
        logging.warning("[GEMINI] API error for '%s': %s; using fallback", entry.get('title'), str(e))
        # Graceful degradation: use raw summary
        excerpt = clean_summary(entry.get("summary", "") or entry.get("description", ""))
        return {
            'title': entry.get('title', 'No Title'),
            'excerpt': excerpt,
            'keywords_hit': []
        }


def translate_entry(entry, config):
    """Translate non-English entry content to English using Gemini.
    Returns modified entry with translated title and summary.
    Adds _translated flag and preserves original in _original_title.
    """
    if not GEMINI_CLIENT or not GEMINI_AVAILABLE:
        return entry
    
    try:
        title = entry.get("title", "")
        summary = clean_summary(entry.get("summary", "") or entry.get("description", ""))[:500]
        
        # Quick heuristic: check if content contains Japanese characters
        has_japanese = any('\u3040' <= char <= '\u30ff' or '\u4e00' <= char <= '\u9faf' for char in (title + summary))
        has_chinese = any('\u4e00' <= char <= '\u9faf' for char in (title + summary))
        has_korean = any('\uac00' <= char <= '\ud7af' for char in (title + summary))
        
        # Skip if appears to be primarily English (no CJK characters)
        if not (has_japanese or has_chinese or has_korean):
            return entry
        
        logging.debug("[TRANSLATE] Detected non-English content in: %s", title[:50])
        
        # Use Gemini to translate
        prompt = f"""Translate the following article title and summary to English. Preserve technical terms and proper nouns.

Title: {title}

Summary: {summary}

Provide translation in this exact format:
Title: [translated title]
Summary: [translated summary]"""
        
        response = GEMINI_CLIENT.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config={"max_output_tokens": 500, "temperature": 0.3}
        )
        
        # Parse response
        if hasattr(response, 'text'):
            translated_text = response.text.strip()
        elif hasattr(response, 'content'):
            translated_text = response.content.strip()
        else:
            translated_text = str(response).strip()
        
        # Extract translated title and summary
        import re
        title_match = re.search(r'Title:\s*(.+?)(?=\n|Summary:|$)', translated_text, re.DOTALL)
        summary_match = re.search(r'Summary:\s*(.+?)$', translated_text, re.DOTALL)
        
        if title_match and summary_match:
            # Store original for reference
            entry['_original_title'] = entry.get('title')
            entry['_original_summary'] = entry.get('summary', '') or entry.get('description', '')
            entry['_translated'] = True
            
            # Update with translations
            entry['title'] = title_match.group(1).strip()
            entry['summary'] = summary_match.group(1).strip()
            entry['description'] = summary_match.group(1).strip()
            
            logging.info("[TRANSLATE] ✓ Translated: %s", entry['title'][:60])
        
    except Exception as e:
        logging.warning("[TRANSLATE] Failed to translate entry: %s", str(e))
    
    return entry


def fetch_feed_entries(url, feed_name, category="General", config=None):
    """
    Fetch feed content using RSS or web scraping.
    
    For "Scraping Candidates" category, uses web scraping instead of RSS.
    Supports incremental fetching with cache (Group 4.1).
    """
    # Check if this is a scraping candidate
    if is_scraping_candidate(category):
        logging.info(f"  [SCRAPER] Using web scraping for {feed_name}")
        return scrape_site(SESSION if SESSION else requests.Session(), feed_name, url)
    
    # Check if we should fetch this feed (cache logic)
    if config and not should_fetch_feed(feed_name, config):
        logging.debug(f"[CACHE] Skipping {feed_name} (cache still valid)")
        return [], "CACHED"
    
    # Standard RSS fetching
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; RSS-Bot/1.0)'}
        timeout = DEFAULTS["request_timeout"]
        if SESSION:
            resp = SESSION.get(url, timeout=timeout, headers=headers)
        else:
            resp = requests.get(url, timeout=timeout, headers=headers)

        if resp.status_code in [403, 404]:
            msg = f"HTTP {resp.status_code} error"
            save_error_post(url, msg)
            return [], msg

        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "").lower()
        if content_type and not any(x in content_type for x in ["xml", "rss", "atom", "xml+xml", "application/rss"]):
            logging.warning("Unexpected Content-Type for %s: %s — attempting to parse anyway", url, content_type)

        feed = feedparser.parse(resp.content)
        if feed.bozo and not feed.entries:
            msg = f"Parse error: {feed.bozo_exception}"
            save_error_post(url, msg)
            return [], msg

        # Update cache with successful fetch
        if config and config.get("feed_caching", {}).get("enabled"):
            cache = load_feed_cache(feed_name)
            cache["last_fetch"] = datetime.now(LOCAL_TZ).isoformat()
            if feed.entries:
                try:
                    latest_entry = feed.entries[0]
                    if hasattr(latest_entry, 'published_parsed') and latest_entry.published_parsed:
                        cache["last_article_date"] = datetime(*latest_entry.published_parsed[:6], tzinfo=LOCAL_TZ).isoformat()
                except Exception:
                    pass
            cache["fetch_count"] = cache.get("fetch_count", 0) + 1
            save_feed_cache(feed_name, cache)
            logging.debug(f"[CACHE] Updated cache for {feed_name}")

        return feed.entries, "OK"

    except Exception as e:
        msg = str(e)
        save_error_post(url, msg)
        return [], msg


def expand_keywords_with_synonyms(keywords, config):
    """Expand keywords using synonym map from config (Group 2.2).
    Returns list of all keywords including original + expanded synonyms."""
    if not keywords:
        return []
    
    keyword_expansion = config.get("keyword_expansion", {})
    if not keyword_expansion.get("enabled"):
        return keywords  # No expansion
    
    synonym_map = keyword_expansion.get("synonym_map", {})
    depth = keyword_expansion.get("expansion_depth", 1)
    
    expanded = set(keywords)
    
    # Simple one-pass expansion (depth=1 covers 90% of cases)
    for keyword in keywords:
        key_lower = keyword.lower()
        if key_lower in synonym_map:
            expanded.update(synonym_map[key_lower])
        # Also check if keyword matches a key in the map (case-insensitive)
        for map_key, synonyms in synonym_map.items():
            if key_lower == map_key.lower():
                expanded.update(synonyms)
    
    return list(expanded)


def matches_negative_keywords(entry, config):
    """Check if entry matches negative keyword filter (Group 2.3).
    Returns True if entry should be FILTERED OUT (blocked).
    """
    negative_config = config.get("negative_keywords", {})
    if not negative_config.get("enabled"):
        return False  # Not filtering anything
    
    # Gather all text from entry
    parts = [
        entry.get("title", ""),
        entry.get("summary", ""),
        entry.get("description", ""),
    ]
    try:
        content = entry.get("content")
        if content:
            if isinstance(content, list):
                parts += [c.get("value", "") if isinstance(c, dict) else str(c) for c in content]
            else:
                parts.append(str(content))
    except Exception:
        pass
    
    text_to_check = " ".join([p for p in parts if p]).lower()
    
    # Check block terms (case-insensitive)
    block_terms = negative_config.get("block_terms", [])
    for term in block_terms:
        if term.lower() in text_to_check:
            logging.debug(f"Article blocked by negative keyword: {term}")
            return True
    
    # Check block domains (URL-based blocking with wildcard support)
    link = entry.get("link", "").lower()
    block_domains = negative_config.get("block_domains", [])
    for pattern in block_domains:
        pattern_lower = pattern.lower()
        if pattern_lower.startswith("*."):
            # Wildcard match: *.medium.com matches any.medium.com
            domain_part = pattern_lower[2:]  # Remove "*."
            if domain_part in link:
                logging.debug(f"Article blocked by domain pattern: {pattern}")
                return True
        else:
            # Exact domain match
            if pattern_lower in link:
                logging.debug(f"Article blocked by domain pattern: {pattern}")
                return True
    
    return False


def get_semantic_model():
    """Load semantic model on demand (lazy initialization)."""
    global SEMANTIC_MODEL
    if SEMANTIC_MODEL is not None:
        return SEMANTIC_MODEL
    
    if not SEMANTIC_AVAILABLE:
        logging.warning("Semantic model requested but sentence-transformers not available")
        return None
    
    try:
        model_name = "all-MiniLM-L6-v2"  # Fast, lightweight model ~22MB
        logging.info(f"Loading semantic model: {model_name}")
        SEMANTIC_MODEL = SentenceTransformer(model_name)
        return SEMANTIC_MODEL
    except Exception as e:
        logging.error(f"Failed to load semantic model: {e}")
        return None


def semantic_similarity(text1, text2, config=None):
    """Compute semantic similarity between two texts (0-1 range).
    Returns 1.0 if texts are identical, 0.0 if completely different.
    Falls back to fuzzy matching if semantic model unavailable.
    """
    if not text1 or not text2:
        return 0.0
    
    model = get_semantic_model()
    if model is None:
        # Fall back to fuzzy matching
        return rf_ratio(text1.lower(), text2.lower()) / 100.0
    
    try:
        embeddings = model.encode([text1, text2], convert_to_tensor=False)
        # Compute cosine similarity (1 - cosine_distance)
        similarity = 1 - cosine(embeddings[0], embeddings[1])
        return float(similarity)
    except Exception as e:
        logging.warning(f"Semantic similarity computation failed: {e}; falling back to fuzzy")
        return rf_ratio(text1.lower(), text2.lower()) / 100.0


def init_feed_cache():
    """Initialize feed cache directory for incremental fetch tracking."""
    cache_dir = Path(".feed_cache")
    if not cache_dir.exists():
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            logging.debug("Feed cache directory initialized")
        except Exception as e:
            logging.warning(f"Failed to create feed cache: {e}")


def get_feed_cache_file(feed_name):
    """Get cache file path for a feed."""
    import hashlib
    # Create safe filename from feed name
    safe_name = hashlib.md5(feed_name.encode()).hexdigest()[:12]
    return Path(".feed_cache") / f"{safe_name}.json"


def load_feed_cache(feed_name):
    """Load cached metadata for a feed (last fetch time, last article date, etc.)."""
    cache_file = get_feed_cache_file(feed_name)
    if not cache_file.exists():
        return {"feed_name": feed_name, "last_fetch": None, "last_article_date": None, "fetch_count": 0}
    
    try:
        import json
        with open(cache_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Failed to load cache for {feed_name}: {e}")
        return {"feed_name": feed_name, "last_fetch": None, "last_article_date": None, "fetch_count": 0}


def save_feed_cache(feed_name, cache_data):
    """Save cached metadata for a feed."""
    cache_file = get_feed_cache_file(feed_name)
    try:
        import json
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        logging.debug(f"Failed to save cache for {feed_name}: {e}")


def should_fetch_feed(feed_name, config):
    """Check if feed should be fetched based on cache (incremental fetch strategy)."""
    cache_config = config.get("feed_caching", {})
    if not cache_config.get("enabled"):
        return True  # Always fetch if caching disabled
    
    cache = load_feed_cache(feed_name)
    last_fetch = cache.get("last_fetch")
    
    if not last_fetch:
        return True  # Never fetched before
    
    # Check if cache expired
    expire_after = cache_config.get("expire_after", 604800)  # 7 days default
    try:
        from datetime import datetime
        last_fetch_time = datetime.fromisoformat(last_fetch)
        age_seconds = (datetime.now(LOCAL_TZ) - last_fetch_time.replace(tzinfo=LOCAL_TZ)).total_seconds()
        
        if age_seconds > expire_after:
            logging.debug(f"[CACHE] {feed_name}: cache expired ({age_seconds:.0f}s > {expire_after}s), fetching fresh")
            return True
        else:
            logging.debug(f"[CACHE] {feed_name}: using cached data (age: {age_seconds:.0f}s)")
            return False
    except Exception as e:
        logging.debug(f"[CACHE] Error checking cache age for {feed_name}: {e}, fetching anyway")
        return True


def entry_matches(entry, pattern, config=None):
    """Check if entry matches keyword pattern AND passes negative keyword filter."""
    
    # First check: Does it match positive keywords?
    # If pattern is None => no keywords configured -> match everything
    if pattern is None:
        positive_match = True
    else:
        parts = [entry.get("title", ""), entry.get("summary", ""), entry.get("description", "")]
        # include common content blocks
        try:
            content = entry.get("content")
            if content:
                if isinstance(content, list):
                    parts += [c.get("value", "") if isinstance(c, dict) else str(c) for c in content]
                else:
                    parts.append(str(content))
        except Exception:
            pass

        text_to_check = " ".join([p for p in parts if p]).lower()
        positive_match = bool(pattern.search(text_to_check))
    
    if not positive_match:
        return False
    
    # Second check: Does it match negative keywords (block list)?
    if config and matches_negative_keywords(entry, config):
        return False  # Blocked by negative filter
    
    return True


# --- Cross-Run Duplicate Prevention (Option 2 Improvement) ---

def init_article_registry():
    """Initialize article registry directory for tracking published articles across runs."""
    registry_dir = Path(".article_registry")
    if not registry_dir.exists():
        try:
            registry_dir.mkdir(parents=True, exist_ok=True)
            logging.debug("Article registry directory initialized")
        except Exception as e:
            logging.warning(f"Failed to create article registry: {e}")


def load_article_registry():
    """Load the persistent article registry (tracks all published articles)."""
    registry_file = Path(".article_registry") / "articles.json"
    if not registry_file.exists():
        return {}  # Empty registry
    
    try:
        with open(registry_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Failed to load article registry: {e}")
        return {}


def save_article_registry(registry):
    """Save the persistent article registry."""
    registry_dir = Path(".article_registry")
    registry_dir.mkdir(parents=True, exist_ok=True)
    registry_file = registry_dir / "articles.json"
    
    try:
        with open(registry_file, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.debug(f"Failed to save article registry: {e}")


def generate_article_hash(entry):
    """Generate a stable hash for an article based on its URL and title."""
    url = entry.get("link") or entry.get("id") or ""
    title = entry.get("title") or ""
    
    # Combine URL and title for hash
    combined = f"{url}#{title}".lower()
    return hashlib.sha256(combined.encode()).hexdigest()


def is_duplicate_article(entry, registry, registry_config):
    """Check if article has already been published in a previous run.
    
    Args:
        entry: feedparser entry
        registry: article registry dict
        registry_config: config section for cross_run_dedup
    
    Returns:
        (bool, str): (is_duplicate, reason)
    """
    article_hash = generate_article_hash(entry)
    
    if article_hash not in registry:
        return False, ""  # Not a duplicate
    
    published_date = registry[article_hash]['published_date']
    keep_days = registry_config.get("keep_registry_days", 60)
    
    try:
        # Parse previously published date
        pub_datetime = datetime.fromisoformat(published_date)
        age_days = (datetime.now(LOCAL_TZ) - pub_datetime.replace(tzinfo=LOCAL_TZ)).days
        
        if age_days < keep_days:
            reason = f"Published {age_days} days ago"
            return True, reason
        else:
            # Old article, safe to republish
            return False, f"Article from {age_days} days ago (outside {keep_days}-day window)"
    except Exception as e:
        logging.debug(f"Error checking article age: {e}")
        return True, "Registry error"


def update_registry_with_completed_run(entries_in_post, registry, config):
    """Update registry after a successful post generation with published articles."""
    registry_config = config.get("cross_run_dedup", {})
    now = datetime.now(LOCAL_TZ).isoformat()
    
    for entry in entries_in_post:
        article_hash = generate_article_hash(entry)
        registry[article_hash] = {
            'title': entry.get('title', '')[:100],
            'url': entry.get('link') or entry.get('id') or '',
            'source': entry.get('_source_name', 'unknown'),
            'published_date': now,
            'category': entry.get('_article_category', 'general')
        }
    
    # Clean up old entries (older than keep_registry_days)
    keep_days = registry_config.get("keep_registry_days", 60)
    new_registry = {}
    
    for article_hash, data in registry.items():
        try:
            pub_datetime = datetime.fromisoformat(data['published_date'])
            age_days = (datetime.now(LOCAL_TZ) - pub_datetime.replace(tzinfo=LOCAL_TZ)).days
            if age_days < keep_days:
                new_registry[article_hash] = data
        except Exception:
            # Keep entries with parsing errors
            new_registry[article_hash] = data
    
    save_article_registry(new_registry)
    return new_registry


def clean_summary(html):
    """
    Return plaintext summary extracted from HTML; collapse whitespace.
    Optimized to strip common boilerplate (ads, social links) to reduce token noise for LLM.
    """
    if not html:
        return ""
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # Aggressively remove noise tags before text extraction
        for tag in soup(["script", "style", "nav", "footer", "iframe", "form", "button"]):
            tag.decompose()
            
        # Remove elements with "share", "social", "subscribe" in class/id
        for noise_class in ["share", "social", "subscribe", "newsletter", "ads", "related"]:
            for tag in soup.find_all(lambda t: t.get('class') and any(noise_class in c for c in t.get('class'))):
                tag.decompose()
                
        text = soup.get_text(separator=" ", strip=True)
        
        # Remove "Read more..." tails common in RSS
        text = re.sub(r"(Read|Continue) reading.*$", "", text, flags=re.IGNORECASE)
        
        # collapse repeated whitespace
        return " ".join(text.split())
    except Exception:
        # fallback: strip tags crudely
        return " ".join(re.sub(r"<[^>]+>", " ", str(html)).split())


def sanitize_url(url):
    """Return a safe, percent-encoded URL or None if invalid."""
    try:
        if not url or not isinstance(url, str):
            return None
        u = url.strip()
        if not u:
            return None
        # percent-encode problematic chars
        safe = requote_uri(u)
        p = urlparse(safe)
        if not p.scheme or not p.netloc:
            return None
        return safe
    except Exception:
        return None

def get_verified_link(title, url):
    """
    Return a verified link.
    If the title contains a CVE ID, returns a link to NVD.
    Otherwise, returns a sanitized URL.
    """
    if not title:
        return sanitize_url(url)

    # Check for CVE ID in title
    cve_pattern = r"(CVE-\d{4}-\d+)"
    match = re.search(cve_pattern, title, re.IGNORECASE)
    if match:
        cve_id = match.group(1).upper()
        return f"https://nvd.nist.gov/vuln/detail/{cve_id}"
        
    return sanitize_url(url)


def get_github_repo_details(url):
    """
    Fetches repository details and README from GitHub API to provide high-quality context for AI analysis.
    This identifies a GitHub link, fetches metadata/README via API (simulating MCP server access),
    and returns a token-efficient context string.
    """
    try:
        if not url or "github.com" not in url:
            return None
            
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) < 2:
            return None
            
        owner, repo = path_parts[0], path_parts[1]
        
        # Requests session is available globally as SESSION? No, use requests directly or check main
        # But for portability here, use requests with simple headers
        headers = {"User-Agent": "feedmeup-news-brief-generator"}
        if "GITHUB_TOKEN" in os.environ:
            headers["Authorization"] = f"token {os.environ['GITHUB_TOKEN']}"
            
        api_base = f"https://api.github.com/repos/{owner}/{repo}"
        
        # 1. Fetch Metadata (Stars, Description, Topics)
        resp = requests.get(api_base, headers=headers, timeout=5)
        if resp.status_code != 200:
            return None
        data = resp.json()
        
        desc = data.get("description", "No description")
        stars = data.get("stargazers_count", 0)
        lang = data.get("language", "Unknown")
        topics = ", ".join(data.get("topics", []))
        
        # 2. Fetch Latest Release (High signal for "what's new")
        release_notes = ""
        try:
            resp_rel = requests.get(f"{api_base}/releases/latest", headers=headers, timeout=5)
            if resp_rel.status_code == 200:
                rel_data = resp_rel.json()
                tag_name = rel_data.get("tag_name", "Unknown")
                rel_body = rel_data.get("body", "")
                release_notes = f"\nLatest Release ({tag_name}):\n{rel_body[:1000]}"
        except Exception:
            pass

        # 3. Fetch README content
        readme_resp = requests.get(f"{api_base}/readme", headers=headers, timeout=5)
        readme_text = ""
        if readme_resp.status_code == 200:
            try:
                content_b64 = readme_resp.json().get("content", "")
                if content_b64:
                    readme_text = base64.b64decode(content_b64).decode("utf-8", errors="replace")
            except Exception:
                pass
                
        # 4. Construct Context String
        # We limit README to 1500 chars to "bring down use of tokens" while keeping high signal
        context = f"GitHub Repository: {owner}/{repo}\n"
        context += f"Metrics: {stars} Stars | Language: {lang}\n"
        context += f"Description: {desc}\n"
        context += f"Topics: {topics}\n"
        
        if release_notes:
            context += release_notes + "\n"
            
        context += "README Summary:\n"
        context += readme_text[:1500]
        
        return context

    except Exception as e:
        logging.warning(f"[GITHUB] Failed to enrich context for {url}: {e}")
        return None

def get_cve_details(cve_id):
    """
    Fetches structured CVE data from CIRCL.lu (Open API) to replace verbose news articles.
    Returns a highly compressed, fact-dense JSON summary for the Analyst.
    """
    try:
        # Using cve.circl.lu as it's a reliable, free, auth-less API for CVEs
        api_url = f"https://cve.circl.lu/api/cve/{cve_id}"
        resp = requests.get(api_url, timeout=5, headers={"User-Agent": "feedmeup-news"})
        
        if resp.status_code != 200:
            return None
            
        data = resp.json()
        if not data:
            return None
            
        # Extract high-signal fields
        summary = data.get("summary", "No summary available.")
        cvss = data.get("cvss", "Unknown")
        # specific technical cause often found in capec or cwe
        cwe = data.get("cwe", "Unknown")
        
        references = "\n".join(data.get("references", [])[:3])
        
        context = f"Vulnerability: {cve_id}\n"
        context += f"CVSS Score: {cvss} | CWE: {cwe}\n"
        context += f"Official Summary: {summary}\n"
        context += f"Key References:\n{references}"
        
        return context
    except Exception as e:
        logging.warning(f"[CVE] Failed to fetch details for {cve_id}: {e}")
        return None

def extract_highlight_urls(highlights):
    """Extract normalized URLs from highlights to prevent duplicates in category sections.
    
    Args:
        highlights: list of (entry, count) tuples
    
    Returns:
        set of normalized URLs (lowercased, stripped)
    """
    urls = set()
    for entry, _ in highlights:
        link = entry.get("link", "").strip().lower()
        if link:
            urls.add(link)
    return urls


def get_source_tier(domain, config):
    """Determine the tier (1-4) for a given domain based on source authority.
    
    Args:
        domain: normalized domain name (e.g., 'bleepingcomputer.com')
        config: config dict with source_tiers
    
    Returns:
        tuple: (tier_number, max_articles_for_tier)
    """
    tiers = config.get("source_tiers", {})
    
    for tier_name in ["tier_1", "tier_2", "tier_3", "tier_4"]:
        tier_config = tiers.get(tier_name, {})
        domains = tier_config.get("domains", [])
        max_articles = tier_config.get("max_articles", 2)
        
        for tier_domain in domains:
            # Support wildcards like *.blogspot.com
            if tier_domain.startswith("*."):
                pattern = tier_domain[2:]  # Remove *. prefix
                if domain.endswith(pattern):
                    return (int(tier_name.split("_")[1]), max_articles)
            elif domain == tier_domain:
                return (int(tier_name.split("_")[1]), max_articles)
    
    # Default: tier 3 if not found
    return (3, 2)


def calculate_story_score(entry, count, config):
    """Calculate weighted score for a story based on mentions and recency.
    
    Args:
        entry: article entry dict
        count: number of mentions across sources
        config: config dict with recency_boost settings
    
    Returns:
        float: weighted score (mention_count × recency_multiplier)
    """
    recency_config = config.get("recency_boost", {})
    
    if not recency_config.get("enabled", True):
        return float(count)
    
    # Parse publication date
    try:
        if "published_parsed" in entry and entry.published_parsed:
            pub_date = datetime(*entry.published_parsed[:6], tzinfo=LOCAL_TZ)
        else:
            pub_date = datetime.now(LOCAL_TZ)
    except Exception:
        pub_date = datetime.now(LOCAL_TZ)
    
    # Calculate hours since publication
    now = datetime.now(LOCAL_TZ)
    hours_old = (now - pub_date).total_seconds() / 3600
    
    # Apply tiered multipliers
    breaking_hours = recency_config.get("breaking_news_hours", 6)
    same_day_hours = recency_config.get("same_day_hours", 24)
    recent_hours = recency_config.get("recent_hours", 72)
    
    if hours_old < breaking_hours:
        multiplier = recency_config.get("breaking_multiplier", 3.0)
        logging.debug("[RECENCY] Breaking news boost: %.1f\u00d7 for '%s' (%.1fh old)", 
                     multiplier, entry.get("title", "")[:50], hours_old)
    elif hours_old < same_day_hours:
        multiplier = recency_config.get("same_day_multiplier", 2.0)
    elif hours_old < recent_hours:
        multiplier = recency_config.get("recent_multiplier", 1.5)
    else:
        multiplier = recency_config.get("default_multiplier", 1.0)
    
    return count * multiplier


def consolidate_similar_entries(entries, config):
    """Consolidate articles about the same story from multiple sources.
    
    Groups articles with high similarity, tracks all sources, and generates
    a consensus summary using AI synthesis.
    
    Args:
        entries: list of (entry, count) tuples from group_similar_entries
        config: config dict with fuzzy thresholds and gemini settings
    
    Returns:
        list of dicts: [{
            'primary_entry': entry,
            'source_list': [(entry, source_name, timestamp), ...],
            'total_mentions': int,
            'consensus_summary': str,
            'first_reported': datetime,
            'last_updated': datetime,
            'score': float  # weighted score for sorting
        }]
    """
    if not entries:
        return []
    
    consolidated = []
    
    # Use very high threshold for consolidation (0.90+)
    consolidation_threshold = 0.90
    
    for entry, count in entries:
        # Calculate weighted score
        score = calculate_story_score(entry, count, config)
        
        # For now, treat each entry as its own story
        # In Phase 2, we'll add multi-source tracking
        consolidated.append({
            'primary_entry': entry,
            'source_list': [(entry, entry.get('_source_name', 'Unknown'), entry.get('published_parsed'))],
            'total_mentions': count,
            'consensus_summary': entry.get('gemini_excerpt', '') or clean_summary(entry.get('summary', '')),
            'first_reported': None,
            'last_updated': None,
            'score': score
        })
    
    # Sort by weighted score (mention count × recency multiplier)
    consolidated.sort(key=lambda x: x['score'], reverse=True)
    
    return consolidated


# --- CVE Reference Section Separation (Option 3a) ---

def is_cve_article(entry):
    """Check if an article is a CVE reference (not editorial content).
    
    CVE articles are detected by:
    1. Category is "CVE" or "Vulnerability"
    2. Title contains CVE-XXXX-XXXXX pattern
    """
    # Check category
    category = entry.get('_article_category', '').lower()
    if category in ['cve', 'vulnerability']:
        return True
    
    # Check title for CVE pattern
    title = (entry.get('title') or '').upper()
    if re.search(r'CVE-\d{4}-\d+', title):
        return True
    
    return False


def extract_cve_references(entries):
    """Separate CVE articles from editorial content.
    
    Returns:
        (cve_articles, editorial_articles) - two lists
    """
    cve_articles = []
    editorial_articles = []
    
    for entry in entries:
        if is_cve_article(entry):
            cve_articles.append(entry)
        else:
            editorial_articles.append(entry)
    
    return cve_articles, editorial_articles


def format_cve_reference_section(cve_entries):
    """Format CVE articles as a clean reference table (not editorial).
    
    Minimal formatting for quick scanning:
    - CVE ID
    - Severity (if available)
    - Product/Component
    - Source link
    
    Returns:
        markdown string or empty string if no CVEs
    """
    if not cve_entries:
        return ""
    
    # Extract unique CVEs (deduplicate if same CVE listed multiple times)
    seen_cves = {}
    
    for entry in cve_entries:
        title = entry.get('title', '')
        link = entry.get('link', '')
        
        # Extract CVE ID
        cve_match = re.search(r'(CVE-\d{4}-\d+)', title, re.IGNORECASE)
        if not cve_match:
            continue
        
        cve_id = cve_match.group(1).upper()
        
        # Extract severity if mentioned in title
        severity = "Unknown"
        severity_patterns = {
            'CRITICAL': ['critical', '9\\.0|9\\.\\d{1,2}|cvss.*9'],
            'HIGH': ['high', 'critical vulnerability', 'cvss.*[789]'],
            'MEDIUM': ['medium', 'moderate'],
            'LOW': ['low']
        }
        
        title_lower = title.lower()
        for sev_level, patterns in severity_patterns.items():
            if any(re.search(p, title_lower) for p in patterns):
                severity = sev_level
                break
        
        # Extract product name (usually after CVE ID or in parentheses)
        product = "Unknown"
        if '(' in title and ')' in title:
            product_match = re.search(r'\(([^)]+)\)', title)
            if product_match:
                product = product_match.group(1).strip()[:40]
        else:
            # Try to find product name after the CVE ID
            parts = title.split(cve_id)
            if len(parts) > 1:
                product_text = parts[1].strip()
                # Take first few words as product name
                product_words = product_text.split()[:3]
                product = ' '.join(product_words)[:40]
        
        # Prioritize newer/official sources (NVD) over duplicates
        if cve_id not in seen_cves:
            seen_cves[cve_id] = {
                'cve_id': cve_id,
                'severity': severity,
                'product': product,
                'link': link,
                'source': entry.get('_source_name', 'Unknown')
            }
        else:
            # If new source is NVD, prioritize it
            if 'nvd' in entry.get('_source_name', '').lower():
                seen_cves[cve_id] = {
                    'cve_id': cve_id,
                    'severity': severity,
                    'product': product,
                    'link': link,
                    'source': entry.get('_source_name', 'Unknown')
                }
    
    if not seen_cves:
        return ""
    
    # Sort by CVE ID (newest first - higher numbers)
    sorted_cves = sorted(seen_cves.values(), 
                        key=lambda x: tuple(map(int, x['cve_id'].split('-')[1:])),
                        reverse=True)
    
    # Format as markdown table
    table_rows = [
        "| CVE ID | Severity | Product | Source |",
        "|--------|----------|---------|--------|"
    ]
    
    severity_emoji = {
        'CRITICAL': '🔴',
        'HIGH': '🟠',
        'MEDIUM': '🟡',
        'LOW': '🔵',
        'Unknown': '⚪'
    }
    
    for cve in sorted_cves:
        severity_display = f"{severity_emoji.get(cve['severity'], '⚪')} {cve['severity']}"
        
        # Create clickable CVE ID link
        if cve['link']:
            safe_link = sanitize_url(cve['link'])
            cve_link = f"[{cve['cve_id']}]({safe_link})" if safe_link else cve['cve_id']
        else:
            # Fallback to NVD link
            cve_link = f"[{cve['cve_id']}](https://nvd.nist.gov/vuln/detail/{cve['cve_id']})"
        
        product_display = cve['product'][:35]
        source_display = cve['source'][:15]
        
        table_rows.append(
            f"| {cve_link} | {severity_display} | {product_display} | {source_display} |"
        )
    
    # Wrap in a collapsible section
    table_body = "\n".join(table_rows)
    
    cve_section = f"""
<details class="group border-t border-border/50 py-4 mt-8">
  <summary class="cursor-pointer hover:bg-secondary/30 transition-colors list-none flex items-center gap-2 py-2 px-2">
    <span class="text-lg font-bold text-foreground">📋 CVE Reference Bulletin</span>
    <span class="text-xs text-muted-foreground">({len(sorted_cves)} vulnerabilities)</span>
    <span class="text-muted-foreground text-xs shrink-0 group-open:rotate-180 transition-transform ml-auto">▼</span>
  </summary>
  <div class="p-3 bg-secondary/10 rounded-md mt-3 text-sm mx-2 overflow-x-auto">
    <p class="text-muted-foreground text-xs mb-2">⚠️ Reference material: Click CVE IDs for full details. Severity indicators are approximate classifications.</p>
    
{table_body}
    
    <p class="text-muted-foreground text-xs mt-3 italic">💡 Tip: Use the <strong>CVE ID</strong> column as a quick reference. For detailed analysis, also check the editorial sections above for deeper coverage of significant vulnerabilities.</p>
  </div>
</details>
"""
    
    return cve_section.strip()


# --- Micro-Topic Tagging (Option 3b) ---

def extract_article_tags(entry, config):
    """Extract 3-5 technical tags from an article using Gemini.
    
    Uses cached tags if available. Only extracts tags for editorial content,
    not for CVE references (which use the CVE ID as tag).
    
    Args:
        entry: feedparser entry dict
        config: configuration dict
        
    Returns:
        list of tag strings, or empty list if extraction fails
    """
    # Skip tagging if disabled
    tagging_config = config.get("micro_topic_tagging", {})
    if not tagging_config.get("enabled", False):
        return []
    
    # Skip if already tagged
    if entry.get('_tags'):
        return entry.get('_tags', [])
    
    # Skip CVE articles (use CVE ID as tag instead)
    if is_cve_article(entry):
        cve_match = re.search(r'CVE-\d{4}-\d+', entry.get('title', ''), re.IGNORECASE)
        if cve_match:
            return [f"CVE-{cve_match.group(0).upper().split('-')[1]}"]  # e.g., "CVE-2026"
        return []
    
    # Use Gemini to extract tags if available
    if not (GEMINI_CLIENT and GEMINI_AVAILABLE):
        return []
    
    title = entry.get('title', '')
    summary = entry.get('summary', '') or entry.get('description', '')
    
    # Truncate to save tokens
    summary = summary[:300] if summary else ''
    
    try:
        prompt = f"""Extract 3-5 technical tags from this tech news article. 
Tags should be specific technical concepts (technologies, methodologies, vendors, practices).
Return as JSON: {{"tags": ["tag1", "tag2", ...]}}

Article Title: {title}
Article Summary: {summary}

Return ONLY valid JSON, no other text."""
        
        response = GEMINI_CLIENT.models.generate_content(prompt)
        response_text = response.text.strip()
        
        # Parse JSON response
        import json
        data = json.loads(response_text)
        tags = data.get('tags', [])
        
        # Limit to 5 tags, lowercase for consistency
        tags = [t.lower()[:30] for t in tags[:5] if t and isinstance(t, str)]
        
        if tags:
            entry['_tags'] = tags  # Cache in entry
            logging.debug(f"[TAGS] Extracted {len(tags)} tags for: {title[:60]}")
            return tags
    except Exception as e:
        logging.debug(f"[TAGS] Failed to extract tags: {str(e)[:100]}")
        return []
    
    return []


def build_trending_topics_dashboard(reports, top_highlights, config):
    """Build a trending topics dashboard from article tags and frequency.
    
    Analyzes which technical topics appear most frequently across the week,
    grouped by urgency/impact level.
    
    Args:
        reports: dict of category -> entries
        top_highlights: list of (entry, count) tuples 
        config: configuration dict
        
    Returns:
        markdown string with dashboard visualization
    """
    dashboard_config = config.get("trending_topics_dashboard", {})
    if not dashboard_config.get("enabled", False):
        return ""
    
    tagging_config = config.get("micro_topic_tagging", {})
    if not tagging_config.get("enabled", False):
        return ""  # Need tagging enabled for this
    
    # Collect all tags and their frequency
    tag_frequency = {}  # {tag: {count, sources, articles}}
    
    all_entries = []
    for entries in reports.values():
        all_entries.extend(entries)
    
    # Count tag occurrences
    for entry in all_entries:
        tags = entry.get('_tags', [])
        for tag in tags:
            if tag not in tag_frequency:
                tag_frequency[tag] = {
                    'count': 0,
                    'sources': set(),
                    'articles': []
                }
            tag_frequency[tag]['count'] += 1
            tag_frequency[tag]['sources'].add(entry.get('_source_name', 'Unknown'))
            tag_frequency[tag]['articles'].append(entry.get('title', '')[:50])
    
    if not tag_frequency:
        return ""  # No tags found
    
    # Categorize by urgency (based on frequency and highlight mention)
    critical_tags = []  # 5+ sources or in top highlights
    active_tags = []    # 3-4 sources
    emerging_tags = []  # 2 sources
    
    highlight_tags = set()
    for entry, count in top_highlights:
        for tag in entry.get('_tags', []):
            if count >= 3:  # Only count high-mention articles
                highlight_tags.add(tag)
    
    for tag, data in sorted(tag_frequency.items(), key=lambda x: x[1]['count'], reverse=True):
        source_count = len(data['sources'])
        if tag in highlight_tags or source_count >= 5:
            critical_tags.append((tag, source_count, data['count']))
        elif source_count >= 3:
            active_tags.append((tag, source_count, data['count']))
        elif source_count >= 2:
            emerging_tags.append((tag, source_count, data['count']))
    
    if not any([critical_tags, active_tags, emerging_tags]):
        return ""  # Nothing to display
    
    # Build markdown dashboard
    dashboard = """
<details class="group border-t border-border/50 py-4 mt-8">
  <summary class="cursor-pointer hover:bg-secondary/30 transition-colors list-none flex items-center gap-2 py-2 px-2">
    <span class="text-lg font-bold text-foreground">📊 This Week's Trending Topics</span>
    <span class="text-muted-foreground text-xs shrink-0 group-open:rotate-180 transition-transform ml-auto">▼</span>
  </summary>
  <div class="p-3 bg-secondary/10 rounded-md mt-3 text-sm mx-2">
"""
    
    # Critical trends
    if critical_tags:
        dashboard += """    <div class="mb-4">
      <p class="text-xs font-semibold text-destructive mb-2">🔴 CRITICAL TRENDS (5+ sources tracked)</p>
      <ul class="list-none space-y-1.5 ml-2">
"""
        for tag, source_count, count in critical_tags[:5]:
            dashboard += f"""        <li class="text-xs text-muted-foreground">
          <strong class="text-foreground">{tag}</strong> <span class="text-xs text-primary">({source_count} sources, {count} mentions)</span>
        </li>
"""
        dashboard += """      </ul>
    </div>
"""
    
    # Active trends
    if active_tags:
        dashboard += """    <div class="mb-4">
      <p class="text-xs font-semibold text-orange-500 mb-2">🟠 ACTIVE DEVELOPMENTS (3-4 sources)</p>
      <ul class="list-none space-y-1 ml-2">
"""
        for tag, source_count, count in active_tags[:4]:
            dashboard += f"""        <li class="text-xs text-muted-foreground">{tag} <span class="text-xs text-primary">({source_count} sources)</span></li>
"""
        dashboard += """      </ul>
    </div>
"""
    
    # Emerging
    if emerging_tags:
        dashboard += """    <div class="mb-4">
      <p class="text-xs font-semibold text-amber-600 mb-2">🟡 EMERGING TOPICS (2 sources)</p>
      <ul class="list-none space-y-1 ml-2">
"""
        for tag, source_count, count in emerging_tags[:4]:
            dashboard += f"""        <li class="text-xs text-muted-foreground">{tag}</li>
"""
        dashboard += """      </ul>
    </div>
"""
    
    dashboard += """    <p class="text-muted-foreground text-xs mt-4 italic border-t border-border/50 pt-3">
      💡 Insight: These topics represent areas of significant industry activity this week. Track these for strategic security planning.
    </p>
  </div>
</details>
"""
    
    return dashboard.strip()


def format_entries_for_category(entries, exclude_urls=None):
    """Format entries as markdown for a category, newest first.
    Groups similar articles to reduce noise.
    Uses clean RSS summary (Phase 1) instead of expensive AI summary for the long list.
    
    Args:
        entries: list of entry dicts
        exclude_urls: optional set of URLs to exclude (e.g., already in highlights)
    """
    if not entries:
        return ""
    
    # Filter out entries that are already in highlights
    if exclude_urls:
        entries = [e for e in entries if e.get("link", "").strip().lower() not in exclude_urls]
    
    if not entries:
        return ""

    # Sort by date first
    def get_pub_date(entry):
        try:
            published_parsed = entry.get("published_parsed")
            if published_parsed:
                # Validate year is in valid range (1-9999)
                if published_parsed[0] > 0 and published_parsed[0] < 10000:
                    return datetime(*published_parsed[:6], tzinfo=LOCAL_TZ)
        except (ValueError, TypeError, OverflowError, AttributeError):
            pass
        return datetime.now(LOCAL_TZ)

    sorted_entries = sorted(entries, key=get_pub_date, reverse=True)
    
    # Simple clustering logic
    groups = []
    used_indices = set()
    
    # Pre-calculate titles and titles_lower for speed
    pre = []
    for idx, e in enumerate(sorted_entries):
        title = (e.get("title") or "").strip()
        pre.append({"idx": idx, "entry": e, "title_l": title.lower()})
        
    for i, item in enumerate(pre):
        if item["idx"] in used_indices:
            continue
            
        current_group = [item["entry"]]
        used_indices.add(item["idx"])
        
        for j in range(i + 1, len(pre)):
            other = pre[j]
            if other["idx"] in used_indices:
                continue
            
            # Use strict fuzzy matching for this grouping
            score = rf_ratio(item["title_l"], other["title_l"]) / 100.0
            if score >= 0.8: # Threshold
                current_group.append(other["entry"])
                used_indices.add(other["idx"])
        
        groups.append(current_group)

    # Format groups
    formatted = []
    for group in groups:
        # Pick representative (newest/first in sorted list)
        primary = group[0]
        title = primary.get("title", "No Title")
        link = primary.get("link", "")
        
        # Use JIT summary if available (from Highlights), otherwise clean RSS summary
        if primary.get('gemini_excerpt'):
            summary = primary.get('gemini_excerpt')
        else:
            raw_summary = primary.get("summary", "") or primary.get("description", "")
            summary = clean_summary(raw_summary)
        
        # Truncate if too long (standard listing doesn't need huge detail)
        if len(summary) > 300:
            summary = summary[:297] + "..."
            
        safe_link = get_verified_link(title, link)
        link_html = f"<a href='{safe_link}' target='_blank' rel='noopener noreferrer' class=\"read-more-btn\">Read Full Article →</a>" if safe_link else "<p class=\"text-muted-foreground italic\">Read more (link unavailable)</p>"
        similar_html = f"<span class='text-xs font-normal text-muted-foreground ml-2 px-2 py-0.5 bg-muted rounded-full'>+ {len(group)-1} similar</span>" if len(group)>1 else ""
        
        # For the dense preview snippet, extract the first sentence or 70 characters
        snippet = summary.split('.')[0] if '.' in summary else summary
        if len(snippet) > 80:
            snippet = snippet[:77] + "..."
            
        md_block = f"""
<details class="group border-b border-border/50 py-1">
  <summary class="cursor-pointer hover:bg-secondary/30 transition-colors list-none flex items-center justify-between py-1.5 px-2">
    <div class="flex-1 flex flex-col md:flex-row md:items-center gap-1 md:gap-3 overflow-hidden mr-4">
      <span class="text-sm font-medium text-foreground whitespace-nowrap overflow-hidden text-ellipsis md:max-w-[50%]">{title} {similar_html}</span>
      <span class="text-xs text-muted-foreground whitespace-nowrap overflow-hidden text-ellipsis flex-1">{snippet}</span>
    </div>
    <span class="text-muted-foreground text-xs shrink-0 group-open:rotate-180 transition-transform">▼</span>
  </summary>
  <div class="p-3 bg-secondary/10 rounded-md mt-1 mb-2 text-sm mx-2">
    <p class="text-muted-foreground mb-3 leading-relaxed">{summary}</p>
    {link_html}
  </div>
</details>
"""
        
        formatted.append(md_block.strip())
        
    return "\n\n".join(formatted)


def create_news_brief(date_str, content_by_category, highlights, cve_reference_section="", trending_dashboard=""):
    """Create a single news brief post with Top highlights.

    Filename includes local HH-MM to avoid collisions and include time.
    Args:
        date_str: date string (YYYY-MM-DD)
        content_by_category: dict of category -> formatted entries
        highlights: list of (entry, count) tuples for top articles
        cve_reference_section: optional CVE bulletin section (HTML/markdown)
        trending_dashboard: optional trending topics dashboard (HTML/markdown)
    """
    POSTS_DIR.mkdir(parents=True, exist_ok=True)

    now_local = datetime.now(LOCAL_TZ)
    time_filename = now_local.strftime("%H-%M")        # e.g. "13-45" (safe for filenames)
    filename = POSTS_DIR / f"{date_str}-{time_filename}-news-brief.md"

    date_object = datetime.strptime(date_str, "%Y-%m-%d")
    formatted_title_date = date_object.strftime("%b %d, %Y")
    
    # Astro content collection frontmatter format
    front_matter = f"""---
title: "Weekly News Brief on Cloud, Cybersecurity, AI, ML — {formatted_title_date}"
description: "Automated news aggregation covering cloud computing, cybersecurity, AI/ML developments"
pubDate: {now_local.strftime('%Y-%m-%d')}
categories: ["newsbrief"]
tags: ["cloud", "cybersecurity", "ai", "ml", "automation"]
author: "feedmeup"
aiGenerated: true
---
"""

    highlights_section = "## Top Highlights\n\n"
    for i, (entry, count) in enumerate(highlights, start=1):
        title = entry.get("title", "No Title")
        summary = clean_summary(entry.get("summary", "") or entry.get("description", ""))
        if len(summary) > 250:
            summary = summary[:247] + "..."
        
        safe_link = sanitize_url(entry.get("link", ""))
        highlights_section += f"{i}. **{title}** ({count} mentions)\n"
        highlights_section += f"   > {summary}\n"
        if safe_link:
            highlights_section += f"   > <br><a href=\"{safe_link}\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"inline-flex items-center justify-center rounded-md text-xs font-bold tracking-wide transition-colors bg-primary !text-primary-foreground hover:bg-primary/90 hover:!text-primary-foreground h-8 px-3 py-1 no-underline shadow-sm mt-2 mb-2\">Read more →</a>\n\n"
        else:
            highlights_section += f"   > Read more (link unavailable)\n\n"

    # HTML Table for Article Summary
    table = """<div class="not-prose my-8 overflow-hidden rounded-xl border border-border bg-secondary/20 text-card-foreground shadow-lg" style="width:50%;min-width:320px">
  <table class="w-full text-sm text-left">
    <thead class="bg-secondary border-b border-border">
      <tr>
        <th class="px-6 py-3 font-semibold text-foreground">
          <span class="flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-primary"><path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z"/><path d="M7 7h.01"/></svg>
            Category
          </span>
        </th>
        <th class="px-6 py-3 font-semibold text-foreground text-right">
          <span class="flex items-center justify-end gap-2" style="white-space:nowrap">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-primary"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
            Article Count
          </span>
        </th>
      </tr>
    </thead>
    <tbody class="divide-y divide-border">
"""
    total_articles = 0
    for category, entries_text in sorted(content_by_category.items()):
        # The new dense HTML structure relies on <details> tags, so count those instead of - **
        article_count = entries_text.count("<details")
        table += f"""      <tr class="hover:bg-secondary/30 transition-colors">
        <td class="px-6 py-3 font-medium">{category}</td>
        <td class="px-6 py-3 text-right text-muted-foreground">{article_count}</td>
      </tr>
"""
        total_articles += article_count

    table += f"""    </tbody>
    <tfoot class="bg-secondary font-semibold border-t-2 border-border">
      <tr>
        <td class="px-6 py-4 text-foreground">Total Articles Scanned</td>
        <td class="px-6 py-4 text-right text-primary">{total_articles}</td>
      </tr>
    </tfoot>
  </table>
</div>
"""

    body = highlights_section
    body += "## Article Summary\n\n"
    body += table + "\n"

    for category in sorted(content_by_category.keys()):
        body += f"## {category}\n\n"
        body += content_by_category[category] + "\n\n"
    
    # Option 3c: Add trending topics dashboard (if enabled)
    if trending_dashboard:
        body += "\n" + trending_dashboard + "\n\n"
    
    # Option 3a: Add CVE reference section at the end
    if cve_reference_section:
        body += "\n" + cve_reference_section + "\n"

    write_dual_output(filename, front_matter + body)
    logging.info("[NEWS BRIEF] Created: %s", filename)


def cluster_articles_by_theme(articles, num_clusters=3):
    """
    Cluster articles into thematic groups based on title and summary similarity.
    Uses fuzzy matching to group related stories together.
    
    Args:
        articles: list of (entry, count) tuples from highlights
        num_clusters: target number of clusters (default 3-5 groups)
    
    Returns:
        list of dicts: [{cluster_name, articles: [(entry, count), ...], article_count}, ...]
    """
    if not articles:
        return []
    
    try:
        from collections import Counter
        
        # Build clustering by grouping similar titles
        clusters = {}
        cluster_assignments = {}
        
        for idx, (entry, count) in enumerate(articles):
            if idx in cluster_assignments:
                continue
            
            title = (entry.get("title") or "").strip().lower()
            cluster_id = len(clusters)
            clusters[cluster_id] = {'articles': [(entry, count)], 'titles': [title]}
            cluster_assignments[idx] = cluster_id
            
            # Find similar articles for this cluster
            for other_idx in range(idx + 1, len(articles)):
                if other_idx in cluster_assignments:
                    continue
                
                other_entry, other_count = articles[other_idx]
                other_title = (other_entry.get("title") or "").strip().lower()
                similarity = rf_ratio(title.split(), other_title.split()) / 100.0
                
                if similarity >= 0.4:
                    clusters[cluster_id]['articles'].append((other_entry, other_count))
                    clusters[cluster_id]['titles'].append(other_title)
                    cluster_assignments[other_idx] = cluster_id
        
        # Generate cluster names from common keywords
        result = []
        for cluster_id, cluster_data in clusters.items():
            all_words = ' '.join(cluster_data['titles']).split()
            stop_words = {'the', 'a', 'an', 'and', 'or', 'is', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
            keywords = [w for w in all_words if w not in stop_words and len(w) > 3]
            
            if keywords:
                top_keywords = Counter(keywords).most_common(2)
                cluster_name = ' & '.join([k[0].title() for k in top_keywords])
            else:
                cluster_name = f"Topic {cluster_id + 1}"
            
            result.append({
                'cluster_name': cluster_name,
                'articles': cluster_data['articles'],
                'article_count': len(cluster_data['articles'])
            })
        
        result.sort(key=lambda c: c['article_count'], reverse=True)
        return result[:num_clusters]
    
    except Exception as e:
        logging.warning("[CLUSTERING] Failed to cluster articles: %s", str(e))
        return []


def group_similar_entries(entries, threshold=None, max_per_domain=None, max_results=None, config=None):
    """Group entries by fuzzy title similarity, choose recent representative,
    sort by group size then recency, and diversify by normalized domain using tier system.

    Returns list of (entry, count) tuples up to max_results.
    """
    if not entries:
        return []

    fuzz_threshold = float(threshold) if threshold is not None else DEFAULTS["fuzz_threshold"]
    max_per_domain = int(max_per_domain) if max_per_domain is not None else DEFAULTS["max_per_domain"]
    max_results = int(max_results) if max_results is not None else DEFAULTS["max_results"]
    
    # Load config if provided (for tiered domain system)
    use_tiers = config and config.get("source_tiers")

    pre = []
    for idx, e in enumerate(entries):
        title = (e.get("title") or "").strip()
        title_l = title.lower()
        try:
            if "published_parsed" in e and e.published_parsed:
                pub = datetime(*e.published_parsed[:6], tzinfo=LOCAL_TZ)
            else:
                pub = datetime.now(LOCAL_TZ)
        except Exception:
            pub = datetime.now(LOCAL_TZ)
        pre.append({"idx": idx, "entry": e, "title_l": title_l, "pub": pub})

    # Determine if we should use semantic deduplication
    use_semantic = False
    if config:
        semantic_config = config.get("semantic_deduplication", {})
        use_semantic = semantic_config.get("enabled", False) and SEMANTIC_AVAILABLE
        if use_semantic:
            semantic_threshold = semantic_config.get("similarity_threshold", 0.92)
            logging.info("[SEMANTIC] Semantic deduplication enabled (threshold: %.2f)", semantic_threshold)

    grouped = []
    used = set()

    for i, item in enumerate(pre):
        if item["idx"] in used:
            continue

        group_indices = [item["idx"]]
        for other in pre[i+1:]:
            if other["idx"] in used:
                continue
            
            # Use semantic similarity if enabled, otherwise fall back to fuzzy matching
            if use_semantic:
                score = semantic_similarity(item["title_l"], other["title_l"], config)
            else:
                score = rf_ratio(item["title_l"], other["title_l"]) / 100.0
            
            if score >= fuzz_threshold:
                group_indices.append(other["idx"])
                used.add(other["idx"])

        used.add(item["idx"])
        group_items = [x for x in pre if x["idx"] in group_indices]
        rep = max(group_items, key=lambda x: x["pub"]) if group_items else item
        grouped.append({"rep": rep["entry"], "count": len(group_indices), "pub": rep["pub"]})

    # Sort by count desc then pub desc
    grouped.sort(key=lambda g: (g["count"], g["pub"]), reverse=True)

    def normalize_domain(link):
        try:
            net = urlparse(link).netloc.lower().split(":")[0]
            if net.startswith("www."):
                net = net[4:]
            return net
        except Exception:
            return ""

    diversified = []
    seen_domains = {}
    
    for g in grouped:
        if len(diversified) >= max_results:
            break
        entry = g["rep"]
        count = g["count"]
        link = (entry.get("link") or "").strip()
        if not link:
            continue
        
        domain = normalize_domain(link) or "__unknown__"
        
        # Use tiered limits if config provided, otherwise use flat max_per_domain
        if use_tiers:
            tier, tier_max = get_source_tier(domain, config)
            current_count = seen_domains.get(domain, 0)
            
            if current_count < tier_max:
                diversified.append((entry, count))
                seen_domains[domain] = current_count + 1
                logging.debug("[DIVERSITY] Added '%s' from %s (tier %d, %d/%d)", 
                            entry.get("title", "")[:40], domain, tier, current_count + 1, tier_max)
        else:
            # Legacy behavior: flat limit
            if seen_domains.get(domain, 0) < max_per_domain:
                diversified.append((entry, count))
                seen_domains[domain] = seen_domains.get(domain, 0) + 1

    return diversified


def detect_trending_category(reports, highlights, trend_threshold=2):
    """
    Detect the trending category based on article frequency and highlights.
    
    Phase 2: Identifies which category has the most newsworthy content
    (most highlights or highest article count) for analyst opinion post.
    
    Args:
        reports: dict of {category: [entries]}
        highlights: list of (entry, count) tuples from deduplication
        trend_threshold: minimum mention count to consider a trend
    
    Returns:
        dict: {
            'category': str (trending category name),
            'article_count': int,
            'highlight_count': int,
            'top_articles': [entries] (top 3 from highlights in this category)
        }
    """
    if not reports:
        return None
    
    try:
        # Count articles per category
        category_counts = {cat: len(entries) for cat, entries in reports.items()}
        
        # Count highlights per category
        category_highlights = {}
        for entry, count in highlights:
            link = entry.get("link", "")
            cat_found = None
            for cat, entries in reports.items():
                if any(e.get("link") == link for e in entries):
                    cat_found = cat
                    break
            if cat_found:
                category_highlights[cat_found] = category_highlights.get(cat_found, 0) + count
        
        # Score: prioritize high highlight count, then article count
        scored_categories = []
        for cat in reports.keys():
            highlight_count = category_highlights.get(cat, 0)
            article_count = category_counts.get(cat, 0)
            # Score = highlights * 2 + articles (highlights weighted higher)
            score = (highlight_count * 2) + article_count
            scored_categories.append({
                'category': cat,
                'score': score,
                'article_count': article_count,
                'highlight_count': highlight_count
            })
        
        if not scored_categories:
            return None
        
        # Sort by score descending, pick top
        scored_categories.sort(key=lambda x: x['score'], reverse=True)
        trending = scored_categories[0]
        
        # Collect top articles from this category
        top_articles = [e for e, _ in highlights if any(
            e.get("link") == entry.get("link") 
            for entry in reports.get(trending['category'], [])
        )][:3]
        
        logging.info("[TRENDING] Category '%s' trending: %d highlights, %d articles", 
                    trending['category'], trending['highlight_count'], trending['article_count'])
        
        return {
            'category': trending['category'],
            'article_count': trending['article_count'],
            'highlight_count': trending['highlight_count'],
            'top_articles': top_articles
        }
    
    except Exception as e:
        logging.warning("[TRENDING] Error detecting trend: %s", str(e))
        return None


def create_story_clusters_post(date_str, highlights):
    """Create a standalone narrative-style blog post from story clusters."""
    from datetime import datetime
    
    POSTS_DIR.mkdir(parents=True, exist_ok=True)

    now_local = datetime.now(LOCAL_TZ)
    time_filename = now_local.strftime("%H-%M")
    filename = POSTS_DIR / f"{date_str}-{time_filename}-weekly-brief.md"

    date_object = datetime.strptime(date_str, "%Y-%m-%d")
    formatted_title_date = date_object.strftime("%b %d, %Y")
    time_front = now_local.strftime("%H:%M:%S %z")

    front_matter = f"""---
title: "This Week in Security: A Briefing — {formatted_title_date}"
description: "This Week in Security: A Briefing — {formatted_title_date}"
pubDate: {date_str}
tags: ["tech-news"]
draft: false
showCTA: false
showComments: false
---
"""

    # Generate clusters
    clusters = cluster_articles_by_theme(highlights, num_clusters=5) if highlights else []
    
    intro = f"""## This Week in Security: What's Trending

Here's your briefing on the week's most important security stories, organized by theme. We've identified **{len(clusters)}** key topics capturing industry attention from across **{sum(c['article_count'] for c in clusters)}** trending stories.

"""
    
    body = intro
    
    # Generate narrative sections for each cluster
    for idx, cluster in enumerate(clusters, start=1):
        cluster_name = cluster['cluster_name']
        articles = cluster['articles']
        
        # Cluster header
        body += f"### {idx}. {cluster_name} ({len(articles)} stories)\n\n"
        
        # Narrative paragraph with top articles
        body += f"The **{cluster_name}** theme captured {len(articles)} trending stories this week. "
        
        if len(articles) >= 2:
            top_articles = articles[:2]
            body += f"Key developments include:\n\n"
            for rank, (entry, count) in enumerate(top_articles, start=1):
                title = entry.get("title", "No Title")
                summary = clean_summary(entry.get("summary", "") or entry.get("description", ""))
                if len(summary) > 200:
                    summary = summary[:197] + "..."
                safe_link = sanitize_url(entry.get("link", ""))
                
                body += f"**{rank}. {title}** ({count} mentions)\n"
                body += f"   {summary}\n"
                if safe_link:
                    body += f"   [Read more]({safe_link})\n\n"
                else:
                    body += f"\n"
        
        if len(articles) > 2:
            remaining = articles[2:]
            body += f"\nOther notable stories: "
            titles = [e.get("title", "Untitled") for e, c in remaining[:3]]
            body += ", ".join(titles)
            body += "\n"
        
        body += f"\n---\n\n"
    
    closing = """## Stay Informed

These thematic groupings highlight how similar security issues are emerging across multiple vendors and technologies this week. For each topic, consider how your organization's security strategy aligns with the trends.
"""
    
    body += closing
    
    write_dual_output(filename, front_matter + body)
    
    return str(filename)


def create_narrative_briefing(highlights):
    """
    Create an 800-1000 word narrative news briefing from top stories.
    Conversational, friendly tone with critical stories first, includes punchy quotes,
    and forward-looking recommendations ("monitor these", "have a look at these").
    
    Args:
        highlights: list of (entry, count) tuples (top 10 stories)
    
    Returns:
        Narrative briefing text
    """
    if not highlights:
        return ""
    
    # Separate stories by criticality
    critical_stories = []  # Threats, CVEs, breaches
    trend_stories = []     # Emerging trends, new techniques
    tool_stories = []      # Tools, updates, releases
    
    for entry, count in highlights[:10]:
        title = entry.get("title", "").lower()
        category = entry.get('_article_category', '').lower()
        summary = (entry.get("summary", "") or entry.get("description", "")).lower()
        content_sample = (title + " " + category + " " + summary[:200]).lower()
        
        is_critical = any(keyword in content_sample for keyword in 
                         ['breach', 'cve-', 'vulnerability', 'threat', 'ransomware', 
                          'malware', 'attack', 'exploit', 'zero-day', 'critical'])
        is_trend = any(keyword in content_sample for keyword in 
                      ['trend', 'emerging', 'analysis', 'technique', 'pattern', 'report'])
        
        if is_critical:
            critical_stories.append((entry, count))
        elif is_trend:
            trend_stories.append((entry, count))
        else:
            tool_stories.append((entry, count))
    
    # Build narrative
    briefing = "## This Week in Security: Your News Briefing\n\n"
    
    # Extract 3-5 most critical headlines
    top_stories = []
    for entry, count in highlights[:5]:
        title = entry.get("title", "")
        if title:
            # Shorten long titles for readability
            if len(title) > 70:
                title = title[:67].rsplit(' ', 1)[0] + "..."
            top_stories.append((title, count))
            
    # Combine Intro + Rundown into a single paragraph
    total_stories = len(highlights[:10])
    paragraph = f"Welcome to your weekly security roundup. We've tracked down the **{total_stories} most important stories** this week—the ones everyone's talking about, from critical threats to emerging trends that could shape your security posture. "
    
    if top_stories:
        t1, c1 = top_stories[0]
        paragraph += f"Leading the news this week is **{t1}**, which has sparked conversation across {c1} sources. "
        
        if len(top_stories) > 1:
            t2, c2 = top_stories[1]
            paragraph += f"Meanwhile, the industry is closely tracking **{t2}** with {c2} mentions, "
            
            remaining = top_stories[2:]
            if remaining:
                titles = [f"**{t}**" for t, c in remaining]
                if len(titles) == 1:
                    paragraph += f"along with emerging details on {titles[0]}. "
                else:
                    last = titles.pop()
                    joined = ", ".join(titles)
                    paragraph += f"along with emerging details on {joined}, and {last}. "
            else:
                paragraph = paragraph.rstrip(", ") + ". "
        
        paragraph += "Here's the full breakdown of what you need to know."
    else:
        paragraph += "Let's dive in."
        
    # Wrap text to prevention horizontal scrolling / code block rendering issues
    briefing += textwrap.fill(paragraph, width=100) + "\n\n"
    
    # Critical stories section (if any)
    if critical_stories:
        briefing += "### 🚨 Critical Threats This Week\n\n"
        briefing += "First, the stories that demand your immediate attention:\n\n"
        
        for idx, (entry, count) in enumerate(critical_stories[:3], 1):
            title = entry.get("title", "No Title")
            summary = clean_summary(entry.get("summary", "") or entry.get("description", ""))
            link = get_verified_link(title, entry.get("link", ""))
            
            # Extract punchy quote or create one from summary
            sentences = [s.strip() for s in summary.split('.') if len(s.strip()) > 20]
            quote = sentences[0][:120] if sentences else summary[:120]
            
            briefing += f"**{idx}. {title}**\n"
            briefing += f"   Mentioned across {count} industry sources this week. {quote.rstrip('.')}.\n"
            if link:
                briefing += f"   [Get the details →]({link})\n\n"
            else:
                briefing += f"\n"
    
    # Trend stories section
    if trend_stories:
        briefing += "### 📈 Emerging Trends & Analysis\n\n"
        briefing += "Here's what the security community is exploring and learning:\n\n"
        
        for idx, (entry, count) in enumerate(trend_stories[:3], 1):
            title = entry.get("title", "No Title")
            summary = clean_summary(entry.get("summary", "") or entry.get("description", ""))
            link = get_verified_link(title, entry.get("link", ""))
            
            sentences = [s.strip() for s in summary.split('.') if len(s.strip()) > 20]
            quote = sentences[0][:120] if sentences else summary[:120]
            
            briefing += f"**{idx}. {title}**\n"
            briefing += f"   {quote.rstrip('.')}. Catching attention from {count} news sources.\n"
            if link:
                briefing += f"   [Learn more →]({link})\n\n"
            else:
                briefing += f"\n"
    
    # Tools & updates section
    if tool_stories:
        briefing += "### 🛠️ Tools, Updates & Releases\n\n"
        briefing += "New capabilities and releases worth knowing about:\n\n"
        
        for idx, (entry, count) in enumerate(tool_stories[:3], 1):
            title = entry.get("title", "No Title")
            summary = clean_summary(entry.get("summary", "") or entry.get("description", ""))
            link = get_verified_link(title, entry.get("link", ""))
            
            sentences = [s.strip() for s in summary.split('.') if len(s.strip()) > 20]
            quote = sentences[0][:100] if sentences else summary[:100]
            
            briefing += f"**{idx}. {title}**\n"
            briefing += f"   {quote.rstrip('.')}. Referenced in {count} stories this week.\n"
            if link:
                briefing += f"   [Explore →]({link})\n\n"
            else:
                briefing += f"\n"
    
    # Closing with forward-looking recommendations
    briefing += "### What You Should Do Next\n\n"
    briefing += "**Monitor these** in your environment next week:\n"
    briefing += "- Any new CVE announcements related to systems you operate\n"
    briefing += "- Emerging attack techniques being discussed in the community\n"
    briefing += "- Updates and patches for tools your team uses\n\n"
    briefing += "**Have a look at** the full deep-dives in the trending stories below. Each one provides context that could inform your security decisions this week.\n\n"
    
    briefing += "---\n\n"
    return briefing


def create_weekly_scan_post(date_str, content_by_category, highlights, cve_reference_section="", trending_dashboard=""):
    """
    Create the Weekly Scan post (aggregated news with trend metrics).
    
    Phase 2: Main news aggregation post showing all articles, highlights, and category stats.
    This is the refactored version of create_news_brief for Phase 2 output.
    
    Args:
        date_str: YYYY-MM-DD date string
        content_by_category: dict of {category: formatted_articles_str}
        highlights: list of (entry, count) tuples
    
    Returns:
        Path to created post file
    """
    POSTS_DIR.mkdir(parents=True, exist_ok=True)

    now_local = datetime.now(LOCAL_TZ)
    time_filename = now_local.strftime("%H-%M")
    filename = POSTS_DIR / f"{date_str}-{time_filename}-weekly-scan.md"

    date_object = datetime.strptime(date_str, "%Y-%m-%d")
    formatted_title_date = date_object.strftime("%b %d, %Y")
    time_front = now_local.strftime("%H:%M:%S %z")

    front_matter = f"""---
title: "Weekly Scan: Cloud, Cybersecurity, AI News — {formatted_title_date}"
description: "Weekly Scan: Cloud, Cybersecurity, AI News — {formatted_title_date}"
pubDate: {date_str}
tags: ["tech-news"]
draft: false
showCTA: false
showComments: false
---
"""

    # Highlights section with narrative briefing + consolidated threat intel/vulnerability
    highlights_section = ""
    
    # Add narrative news briefing at the top
    if highlights:
        narrative = create_narrative_briefing(highlights)
        if narrative:
            highlights_section += narrative
    
    # Top Trending Stories - detailed list
    highlights_section += "## Top Trending Stories\n\n"
    
    # Separate threat intel/vulnerability from other articles
    threat_intel_vuln = []
    other_highlights = []
    
    for entry, count in highlights:
        category = entry.get('_article_category', '')
        # Check for threat intel or vulnerability categories (handle various formats)
        if 'threat' in category.lower() or 'vulnerability' in category.lower() or 'cve' in category.lower():
            threat_intel_vuln.append((entry, count))
        else:
            other_highlights.append((entry, count))
    
    # Build top trending with consolidated threat intel/vulnerability entry
    item_num = 1
    
    # First add consolidated threat intel & vulnerability if they exist
    if threat_intel_vuln:
        top_threats = sorted(threat_intel_vuln, key=lambda x: x[1], reverse=True)[:3]
        
        highlights_section += f"<details class=\"group border-b border-border/50 py-1\">\n"
        highlights_section += f"  <summary class=\"cursor-pointer hover:bg-secondary/30 transition-colors list-none flex items-center justify-between py-1.5 px-2\">\n"
        highlights_section += f"    <div class=\"flex-1 flex flex-col md:flex-row md:items-center gap-1 md:gap-3 overflow-hidden mr-4\">\n"
        highlights_section += f"      <span class=\"text-sm font-medium text-destructive whitespace-nowrap overflow-hidden text-ellipsis md:max-w-[50%]\">{item_num}. Key Threat Intel & Vulnerability Stories ({sum(c for e, c in threat_intel_vuln)} mentions)</span>\n"
        highlights_section += f"    </div>\n"
        highlights_section += f"    <span class=\"text-muted-foreground text-xs shrink-0 group-open:rotate-180 transition-transform\">▼</span>\n"
        highlights_section += f"  </summary>\n"
        highlights_section += f"  <div class=\"p-3 bg-secondary/10 rounded-md mt-1 mb-2 text-sm mx-2\">\n"
        highlights_section += f"    <p class=\"text-muted-foreground mb-4\">This week's critical security updates and vulnerability disclosures:</p>\n"
        highlights_section += f"    <ul class=\"list-disc pl-5 mb-4 text-muted-foreground\">\n"
        for entry, count in top_threats:
            title = entry.get("title", "No Title")
            link = get_verified_link(title, entry.get("link", ""))
            if link:
                highlights_section += f"      <li><a href=\"{link}\" class=\"text-primary hover:underline\">{title}</a> ({count} mentions)</li>\n"
            else:
                highlights_section += f"      <li>{title} ({count} mentions)</li>\n"
        highlights_section += f"    </ul>\n"
        highlights_section += f"  </div>\n"
        highlights_section += f"</details>\n\n"
        item_num += 1
    
    # Then add other trending stories
    for entry, count in other_highlights:
        title = entry.get("title", "No Title")
        summary = clean_summary(entry.get("summary", "") or entry.get("description", ""))
        if len(summary) > 250:
            summary = summary[:247] + "..."
        
        safe_link = get_verified_link(title, entry.get("link", ""))
        # For the dense preview snippet, extract the first sentence or 70 characters
        snippet = summary.split('.')[0] if '.' in summary else summary
        if len(snippet) > 80:
            snippet = snippet[:77] + "..."
            
        safe_link = get_verified_link(title, entry.get("link", ""))
        highlights_section += f"<details class=\"group border-b border-border/50 py-1\">\n"
        highlights_section += f"  <summary class=\"cursor-pointer hover:bg-secondary/30 transition-colors list-none flex items-center justify-between py-1.5 px-2\">\n"
        highlights_section += f"    <div class=\"flex-1 flex flex-col md:flex-row md:items-center gap-1 md:gap-3 overflow-hidden mr-4\">\n"
        highlights_section += f"      <span class=\"text-sm font-medium text-foreground whitespace-nowrap overflow-hidden text-ellipsis md:max-w-[50%]\">{item_num}. {title} ({count} mentions)</span>\n"
        highlights_section += f"      <span class=\"text-xs text-muted-foreground whitespace-nowrap overflow-hidden text-ellipsis flex-1\">{snippet}</span>\n"
        highlights_section += f"    </div>\n"
        highlights_section += f"    <span class=\"text-muted-foreground text-xs shrink-0 group-open:rotate-180 transition-transform\">▼</span>\n"
        highlights_section += f"  </summary>\n"
        highlights_section += f"  <div class=\"p-3 bg-secondary/10 rounded-md mt-1 mb-2 text-sm mx-2\">\n"
        highlights_section += f"    <p class=\"text-muted-foreground mb-3 leading-relaxed\">{summary}</p>\n"
        if safe_link:
            highlights_section += f"    <a href=\"{safe_link}\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"read-more-btn\">Read Full Article →</a>\n"
        else:
            highlights_section += f"    <p class=\"text-muted-foreground italic\">Read more (link unavailable)</p>\n"
        highlights_section += f"  </div>\n"
        highlights_section += f"</details>\n\n"
        item_num += 1

    # HTML Table for Article Summary
    table = """<div class="not-prose my-8 overflow-hidden rounded-xl border border-border bg-secondary/20 text-card-foreground shadow-lg" style="width:50%;min-width:320px">
  <table class="w-full text-sm text-left">
    <thead class="bg-secondary border-b border-border">
      <tr>
        <th class="px-6 py-3 font-semibold text-foreground">
          <span class="flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-primary"><path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z"/><path d="M7 7h.01"/></svg>
            Category
          </span>
        </th>
        <th class="px-6 py-3 font-semibold text-foreground text-right">
          <span class="flex items-center justify-end gap-2" style="white-space:nowrap">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-primary"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
            Article Count
          </span>
        </th>
      </tr>
    </thead>
    <tbody class="divide-y divide-border">
"""
    total_articles = 0
    for category, entries_text in sorted(content_by_category.items()):
        # The new dense HTML structure relies on <details> tags, so count those instead of - **
        article_count = entries_text.count("<details")
        table += f"""      <tr class="hover:bg-secondary/30 transition-colors">
        <td class="px-6 py-3 font-medium">{category}</td>
        <td class="px-6 py-3 text-right text-muted-foreground">{article_count}</td>
      </tr>
"""
        total_articles += article_count

    table += f"""    </tbody>
    <tfoot class="bg-secondary font-semibold border-t-2 border-border">
      <tr>
        <td class="px-6 py-4 text-foreground">Total Articles Scanned</td>
        <td class="px-6 py-4 text-right text-primary">{total_articles}</td>
      </tr>
    </tfoot>
  </table>
</div>
"""

    body = highlights_section
    body += "## Article Summary\n\n"
    body += table + "\n"

    # Category sections
    for category in sorted(content_by_category.keys()):
        body += f"## {category}\n\n"
        body += content_by_category[category] + "\n\n"
    
    # Option 3c: Add trending topics dashboard (if enabled)
    if trending_dashboard:
        body += "\n" + trending_dashboard + "\n\n"
    
    # Option 3a: Add CVE reference section at the end
    if cve_reference_section:
        body += "\n" + cve_reference_section + "\n"

    write_dual_output(filename, front_matter + body)
    
    logging.info("[WEEKLY SCAN] Created: %s", filename)
    logging.info("[PHASE 2] Weekly Scan (with Narrative News Briefing) + Analyst Opinion posts generated successfully")
    return filename


def find_historical_context(keyword_topics, lookback_weeks=12):
    """
    Search past posts for similar topics to provide historical context.
    
    Args:
        keyword_topics: List of keywords/topics to search for (e.g., ['cybersecurity', 'ransomware'])
        lookback_weeks: How many weeks back to search
    
    Returns:
        list of dicts with {title, date, summary} from past posts
    """
    historical_posts = []
    cutoff_date = datetime.now(LOCAL_TZ) - timedelta(weeks=lookback_weeks)
    
    try:
        for post_file in sorted(POSTS_DIR.glob("*.md"), reverse=True):
            # Skip analyst opinion posts to avoid self-reference
            if "analyst-opinion" in post_file.name:
                continue
                
            file_mtime = datetime.fromtimestamp(post_file.stat().st_mtime, tz=LOCAL_TZ)
            if file_mtime < cutoff_date:
                break
            
            with open(post_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Check if any keywords appear in the post
            content_lower = content.lower()
            matching_keywords = [kw for kw in keyword_topics if kw.lower() in content_lower]
            
            if matching_keywords:
                # Extract title from front matter
                title_match = re.search(r'title:\s*["\']?([^"\'\n]+)["\']?', content)
                title = title_match.group(1) if title_match else post_file.stem
                
                # Extract date from front matter
                date_match = re.search(r'date:\s*(\d{4}-\d{2}-\d{2})', content)
                post_date = date_match.group(1) if date_match else "Unknown"
                
                # Extract first 200 chars of body (after front matter)
                body_start = content.find("---", content.find("---") + 3) + 3
                body = content[body_start:].strip()[:200]
                
                historical_posts.append({
                    'title': title,
                    'date': post_date,
                    'summary': body,
                    'keywords': matching_keywords
                })
    
    except Exception as e:
        logging.warning("[HISTORY] Failed to search historical context: %s", str(e))
    
    return historical_posts[:3]  # Return top 3 similar posts


def generate_gemini_opinion_analysis(article, category, historical_posts, config):
    """
    Generate investigative journalism analysis for analyst opinion post.
    
    Uses gemini-3-flash-preview for cost-effective reasoning depth.
    Hybrid Strategy: Flash for investigative analysis, Flash for weekly summaries.
    
    Transforms article into deep investigative journalism with technical accountability:
    - Technical Analysis & Threat Intelligence (900-1100 words): Technical breakdown, defense failures, threat ecosystem, attribution, monetization
    - Defense Strategy (600+ words): Immediate actions, medium-term planning, strategic vision
    
    Args:
        article: The article of the week
        category: Trend category
        historical_posts: List of similar past posts for comparison
        config: Config dict with synthesis settings
    
    Returns:
        dict with {technical_analysis, defense_strategy}
    """
    if not GEMINI_CLIENT or not GEMINI_AVAILABLE:
        return {
            'technical_analysis': article.get('gemini_excerpt', clean_summary(article.get("summary", "") or article.get("description", ""))),
            'defense_strategy': ""
        }
    
    try:
        # Optimization: Use "Internal MCP Agents" to fetch high-signal context (GitHub/CVE) 
        # This reduces token usage by avoiding raw HTML scrapes and providing structured technical data.
        link = article.get("link", "")
        article_title = article.get("title", "Unknown")
        article_text = ""
        
        # 1. GitHub Agent
        repo_details = get_github_repo_details(link)
        
        # 2. CVE Agent
        cve_pattern = r"(CVE-\d{4}-\d+)"
        cve_match = re.search(cve_pattern, article_title, re.IGNORECASE)
        cve_details = None
        if cve_match:
            cve_details = get_cve_details(cve_match.group(1).upper())

        # Select best context source
        if repo_details:
            article_text = repo_details
            logging.info(f"[ANALYST] Enriched context with GitHub data for {article.get('title')}")
        elif cve_details:
            article_text = cve_details
            logging.info(f"[ANALYST] Enriched context with CVE data for {article.get('title')}")
        else:
            # Fallback to standard summary
            article_text = clean_summary(article.get("summary", "") or article.get("description", ""))[:2000]

        
        # Build historical context string
        history_context = ""
        if historical_posts:
            history_context = "\n\nRelated past articles:\n"
            for hp in historical_posts:
                history_context += f"- {hp['date']}: {hp['title']}\n"
        
        # Unified Prompt: Analyst Opinion (Investigative Journalism style)
        prompt = f"""
ROLE: Senior Threat Intelligence Analyst & Investigative Journalist.
AUDIENCE: CISOs, Security Architects, and Executive Leadership.
TONE: Authoritative, narrative-driven, skeptical of hype, executive-ready. (Example style: Krebs, Schneier, Troy Hunt).

TASK: Write a cohesive "Analyst Opinion" deep-dive on the provided article.
DO NOT output a generic list of bullet points. Write a COMPELLING NARRATIVE.

SOURCE DATA:
Title: {article_title}
Context: {article_text}
{history_context if history_context else ""}

---

OUTPUT FORMAT (Markdown):

### The Mechanic: What's Actually Happening
(Write 2-4 paragraphs explaining the technical reality. Cut through marketing fluff. Explain the attack chain, the vulnerability mechanics, or the architectural shift. Use "we" or "I" to sound personal and expert.)

### The "So What?": Why This Matters
(Analyze the broader impact. Does this break a unified security model? Does it lower the barrier to entry for attackers? Cite specific examples or metrics if available in the context.)

### Strategic Defense: What To Do About It
(Provide a bifurcated strategy. Be specific—name tools, logs, and configurations by name.)

**1. Immediate Actions (Tactical Response)**
*   Actionable step 1
*   Actionable step 2
*   Actionable step 3

**2. Long-Term Strategy (The Pivot)**
*   Strategic shift 1
*   Strategic shift 2

---

CONSTRAINTS:
- Total length: ~1000-1500 words.
- Use bolding for emphasis.
- AVOID: "In the rapidly evolving landscape," "It is crucial to," or generic ChatGPT filler.
- If the text is about a specific CVE, include the CVSS score and vector if known.
"""

        response = GEMINI_CLIENT.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config={"max_output_tokens": 3000, "temperature": 0.5}
        )
        
        # Handle response
        if hasattr(response, 'text'):
            full_analysis = response.text.strip()
        elif hasattr(response, 'content'):
            full_analysis = response.content.strip()
        else:
            full_analysis = str(response).strip()
            
        logging.info("[OPINION] Generated full narrative analysis for: %s", article_title)
        
        # Return as a single block since we merged the prompts.
        # The caller expects specific keys, so we will split or just return the full block in 'technical_analysis'
        # and leave 'defense_strategy' empty (or split logically if needed).
        # For simplicity/cohesion, we put the whole thing in technical_analysis and the caller renders it.
        
        return {
            'technical_analysis': full_analysis,
            'defense_strategy': "" # Included in the cohesive narrative above
        }
    
    except Exception as e:
        logging.warning("[OPINION] Gemini analysis failed: %s; using fallback", str(e))
        
        # Provide structured fallback content when Gemini is unavailable
        article_summary = article.get('gemini_excerpt', clean_summary(article.get("summary", "") or article.get("description", "")))
        
        fallback_technical = f"""
### The Mechanic: What's Actually Happening

{article_summary}

**Key Points**

This article relates to the {category.upper()} security category. The content addresses important developments in this area that security teams should be aware of.

*Note: Summary analysis provided instead.*
"""
        
        fallback_defense = f"""
### Strategic Defense: What To Do About It

**1. Immediate Actions (Tactical Response)**
*   Review this article for relevant context to your organization's security posture
*   Share findings with your security team for discussion
*   Assess applicability to your systems and infrastructure

**2. Long-Term Strategy (The Pivot)**
*   Track evolution of this threat/trend over time
*   Integrate learnings into future security architecture decisions

*Note: Summary analysis provided instead.*
"""
        
        return {
            'technical_analysis': fallback_technical,
            'defense_strategy': fallback_defense
        }


def create_analyst_opinion_post(date_str, trending_data, config):
    """
    Create the Analyst Opinion post with Top 3 Articles of the Week.
    
    Phase 3 Enhanced: Deep investigative analysis for top 3 trending stories:
    - Full technical analysis for each article (900-1100 words per story)
    - Defense strategy for each article (600+ words per story)
    - Maintains complete analytical depth across all 3 articles
    
    Args:
        date_str: YYYY-MM-DD date string
        trending_data: dict from detect_trending_category() with category, articles, etc.
        config: config dict with synthesis settings
    
    Returns:
        Path to created post file
    """
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    
    if not trending_data:
        logging.warning("[OPINION] No trending data; skipping analyst opinion post")
        return None

    now_local = datetime.now(LOCAL_TZ)
    time_filename = now_local.strftime("%H-%M")
    filename = POSTS_DIR / f"{date_str}-{time_filename}-analyst-opinion.md"

    date_object = datetime.strptime(date_str, "%Y-%m-%d")
    formatted_title_date = date_object.strftime("%b %d, %Y")
    time_front = now_local.strftime("%H:%M:%S %z")

    category = trending_data['category'].title()
    article_count = trending_data['article_count']
    highlight_count = trending_data['highlight_count']
    top_articles = trending_data.get('top_articles', [])

    if not top_articles:
        logging.warning("[OPINION] No articles in trending data; skipping opinion post")
        return None
    
    # Get top 3 articles (or fewer if not available)
    top_3_articles = top_articles[:3]

    front_matter = f"""---
title: "Analyst Top 3: {category} — {formatted_title_date}"
description: "Analyst Top 3: {category} — {formatted_title_date}"
pubDate: {date_str}
tags: ["analysis", "{category}"]
draft: false
showCTA: false
showComments: false
---
"""

    # Introduction
    intro_section = f"""## This Week's Top 3: {category}

The **{category}** category captured significant attention this week with **{article_count}** articles and **{highlight_count}** trending stories.

Here are the **Top 3 Articles of the Week**—comprehensive analysis of the most impactful stories:

"""

    # Build full analysis for each of the top 3 articles
    articles_body = ""
    for rank, article in enumerate(top_3_articles, start=1):
        article_title = article.get("title", "No Title")
        article_link = sanitize_url(article.get("link", ""))
        article_summary = article.get('gemini_excerpt', clean_summary(article.get("summary", "") or article.get("description", "")))
        
        # Article header
        articles_body += f"## Article {rank}: {article_title}\n\n"
        articles_body += f"{article_summary}\n\n"
        if article_link:
            articles_body += f"<a href=\"{article_link}\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"inline-flex items-center justify-center rounded-md text-sm font-bold tracking-wide transition-colors bg-primary !text-primary-foreground hover:bg-primary/90 hover:!text-primary-foreground h-9 px-4 py-2 no-underline shadow-sm mt-4\">Read Full Article →</a>\n\n"
        
        # Get historical context and Gemini analysis for this article
        keywords_for_history = [category.lower()] + (article.get('keywords_hit', []) if isinstance(article.get('keywords_hit'), list) else [])
        historical_posts = find_historical_context(keywords_for_history, lookback_weeks=12)
        gemini_analysis = generate_gemini_opinion_analysis(article, category, historical_posts, config)
        
        # Technical Analysis section with full depth
        articles_body += f"### Technical Analysis: What's Really Happening\n\n"
        articles_body += f"{gemini_analysis['technical_analysis']}\n\n"
        
        # Defense Strategy section with full depth
        if gemini_analysis['defense_strategy']:
            articles_body += f"### Defense Strategy: What Security Teams Should Do\n\n"
            articles_body += f"{gemini_analysis['defense_strategy']}\n\n"
        
        articles_body += "---\n\n"
    
    # Closing
    closing_section = """**Analyst Note:** These top 3 articles this week synthesize industry trends with expert assessment. For strategic decisions, conduct thorough validation with your security, compliance, and risk teams."""

    body = intro_section + articles_body + closing_section

    write_dual_output(filename, front_matter + body)
    
    logging.info("[ANALYST OPINION] Created with Top 3 deep analysis: %s", filename)
    return filename


def main():
    config = load_config()
    # allow overriding via env for quick debugging in CI/local
    log_level = os.environ.get("LOG_LEVEL", config.get("log_level", DEFAULTS["log_level"])).upper()
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO), format="%(levelname)s: %(message)s")
    logging.info("Loaded config keys: %s", list(config.keys()))
    logging.info("Configured sources count: %d", len(config.get("sources", [])))
    logging.info("Configured keywords: %s", config.get("filters", {}).get("keywords", []))

    init_requests_session(
        retries=config.get("request_retries", DEFAULTS["request_retries"]),
        backoff=config.get("request_backoff", DEFAULTS["request_backoff"]),
        timeout=config.get("request_timeout", DEFAULTS["request_timeout"]),
        status_forcelist=config.get("request_status_forcelist", DEFAULTS["request_status_forcelist"]),
    )

    # Group 4: Initialize feed caching system (if enabled)
    feed_cache_config = config.get("feed_caching", {})
    if feed_cache_config.get("enabled", False):
        init_feed_cache()
        logging.info("[CACHE] Feed incremental caching enabled")

    # Option 2: Initialize cross-run deduplication (if enabled)
    cross_run_dedup_config = config.get("cross_run_dedup", {})
    article_registry = {}
    if cross_run_dedup_config.get("enabled", False):
        init_article_registry()
        article_registry = load_article_registry()
        logging.info("[DEDUP] Cross-run duplicate detection enabled (registry size: %d articles)", len(article_registry))
    
    # Group 2: Initialize semantic deduplication (if enabled)
    semantic_config = config.get("semantic_deduplication", {})
    if semantic_config.get("enabled", False) and SEMANTIC_AVAILABLE:
        init_feed_cache()  # Cache dir for embeddings
        logging.info("[SEMANTIC] Semantic deduplication will be used (model: %s)", 
                    semantic_config.get("model", "all-MiniLM-L6-v2"))
    elif semantic_config.get("enabled", False) and not SEMANTIC_AVAILABLE:
        logging.warning("[SEMANTIC] Semantic deduplication requested but sentence-transformers not available")

    # Phase 1: Initialize Gemini API for summarization (if enabled and API key provided)
    gemini_config = config.get("gemini", {})
    gemini_api_key = os.environ.get("GEMINI_API_KEY", gemini_config.get("api_key", ""))
    gemini_enabled = config.get("synthesis", {}).get("enable_gemini_summarization", False)
    gemini_model = gemini_config.get("model", "gemini-1.5-flash")
    gemini_prompt_template = gemini_config.get("summarization_prompt", "")
    
    # Load translation configuration
    translation_enabled = config.get("translation", {}).get("enabled", False)
    
    if gemini_enabled:
        init_gemini_client(gemini_api_key, gemini_model)
        if translation_enabled:
            logging.info("[TRANSLATE] Auto-translation enabled for Korean/Japanese/Chinese content")
    else:
        logging.info("[GEMINI] Summarization disabled in config")
        if translation_enabled:
            logging.warning("[TRANSLATE] Translation requires Gemini API; forcing translation_enabled=False")
            translation_enabled = False

    logging.info("%s Starting news aggregation... %s", YELLOW, RESET)

    keywords = config.get("filters", {}).get("keywords", [])
    sources = config.get("sources", [])
    pattern = compile_keywords_pattern(keywords, config)  # Pass config for keyword expansion

    logging.info("Configuration: sources=%d, keywords=%s, gemini_enabled=%s", len(sources), keywords, gemini_enabled)

    reports = {}
    all_matched_entries = []
    errors = 0
    total_entries = 0
    recent_entries = 0
    matched_entries = 0
    
    # Get lookback days from config (default: 7 days for weekly scans)
    lookback_days = config.get("lookback_days", 7)
    cutoff_date = datetime.now(LOCAL_TZ) - timedelta(days=lookback_days)

    logging.debug("Looking for entries after: %s (last %d days)", cutoff_date.strftime('%Y-%m-%d'), lookback_days)

    for i, source in enumerate(sources, 1):
        feed_name = source.get("name", source.get("url"))
        url = source.get("url")
        category = source.get("category", "General")

        logging.info("[%d/%d] %s", i, len(sources), feed_name)
        entries, status = fetch_feed_entries(url, feed_name, category, config)  # Pass config for caching

        if status == "CACHED":
            logging.info("  ↻ Using cached data (not fetched)")
            continue
        elif status != "OK":
            errors += 1
            logging.warning("  ✗ Failed: %s", status)
            continue

        logging.info("  ✓ Found %d total entries", len(entries))
        total_entries += len(entries)

        recent_count = 0
        matched_count = 0

        for entry in entries:
            # Translate non-English content if translation is enabled
            translate_enabled = config.get("translation", {}).get("enabled", True)
            if translate_enabled and gemini_enabled:
                entry = translate_entry(entry, config)
            
            # Safely parse publication date with validation for invalid dates
            try:
                published_parsed = entry.get("published_parsed")
                if published_parsed:
                    # Validate year is in valid range (1-9999)
                    if published_parsed[0] > 0 and published_parsed[0] < 10000:
                        pub_date = datetime(*published_parsed[:6], tzinfo=LOCAL_TZ)
                    else:
                        pub_date = datetime.now(LOCAL_TZ)
                else:
                    pub_date = datetime.now(LOCAL_TZ)
            except (ValueError, TypeError, OverflowError, AttributeError):
                # Handle any datetime construction errors
                pub_date = datetime.now(LOCAL_TZ)

            if pub_date >= cutoff_date:
                recent_count += 1
                recent_entries += 1

                if entry_matches(entry, pattern, config):  # Pass config for negative keyword filtering
                    matched_count += 1
                    matched_entries += 1
                    
                    # Option 2: Check if article is a duplicate from previous runs
                    if cross_run_dedup_config.get("enabled", False):
                        is_dup, reason = is_duplicate_article(entry, article_registry, cross_run_dedup_config)
                        if is_dup:
                            logging.debug(f"    [DEDUP] Skipping duplicate: {entry.get('title', '')[:50]}... ({reason})")
                            continue
                    
                    # Store source name for attribution
                    entry['_source_name'] = feed_name
                    
                    # Translate non-English content if enabled
                    if translation_enabled and GEMINI_CLIENT:
                        entry = translate_entry(entry, config)
                    
                    # Phase 1: Gemini Summarization MOVED to post-deduplication (Cost Saver)
                    # We no longer summarize every matching article here.
                    # See "JIT Summarization" block below.
                    
                    reports.setdefault(category, []).append(entry)
                    # Store category in entry for later filtering
                    entry['_article_category'] = category
                    all_matched_entries.append(entry)

        logging.debug("    Recent: %d, Matched: %d", recent_count, matched_count)

    logging.info("PROCESSING SUMMARY")
    logging.info("Total entries found: %d", total_entries)
    logging.info("Recent entries (last 30 days): %d", recent_entries)
    logging.info("Entries matching keywords: %d", matched_entries)
    logging.info("Feed errors: %d/%d", errors, len(sources))
    logging.info("Categories found: %s", list(reports.keys()) if reports else 'None')

    if not reports:
        logging.warning("No matching news found")
        if errors == len(sources):
            logging.warning("  - All feeds failed to load")
        elif recent_entries == 0:
            logging.warning("  - No articles published in last %d days", lookback_days)
        elif matched_entries == 0:
            logging.warning("  - No articles matched keywords; try broader keywords")
        return

    fuzz_threshold = config.get("fuzz_threshold", DEFAULTS["fuzz_threshold"])
    max_per_domain = config.get("max_per_domain", DEFAULTS["max_per_domain"])
    max_results = config.get("max_results", DEFAULTS["max_results"])

    # Use tiered domain diversity and get initial highlights
    top_highlights = group_similar_entries(
        all_matched_entries, 
        threshold=fuzz_threshold, 
        max_per_domain=max_per_domain, 
        max_results=max_results,
        config=config  # Pass config for tiered domain system
    )
    
    # Apply consolidation and recency-based scoring
    logging.info("📊 Applying recency boost and consolidating similar stories...")
    consolidated_highlights = consolidate_similar_entries(top_highlights, config)
    
    # Extract back to (entry, count) format for compatibility
    top_highlights = [(item['primary_entry'], item['total_mentions']) for item in consolidated_highlights]
    
    logging.info("✅ Top %d highlights selected (weighted by recency)", len(top_highlights))

    # Phase 1.5: Just-In-Time Gemini Summarization for Top Highlights
    # Only summarize the stories that actually made it to the Top N list to save tokens.
    if gemini_enabled and GEMINI_CLIENT and gemini_prompt_template and top_highlights:
        logging.info("⚡ JIT Summarization: Generating AI summaries for %d top highlights...", len(top_highlights))
        for i, (entry, count) in enumerate(top_highlights):
            # Skip if already has summary
            if entry.get('gemini_excerpt'):
                continue
                
            logging.info("   Summarizing [%d/%d]: %s...", i+1, len(top_highlights), (entry.get("title") or "")[:40])
            try:
                summary_data = summarize_with_gemini(entry, keywords, gemini_prompt_template, config)
                entry['gemini_excerpt'] = summary_data['excerpt']
                entry['gemini_title'] = summary_data['title']
                entry['keywords_hit'] = summary_data['keywords_hit']
            except Exception as e:
                logging.warning("   Failed to summarize: %s", str(e))
    
    # Option 3b: Extract micro-topic tags from editorial articles
    tagging_config = config.get("micro_topic_tagging", {})
    if tagging_config.get("enabled", False) and gemini_enabled and GEMINI_CLIENT:
        logging.info("🏷️  Extracting micro-topic tags from %d articles...", len(all_matched_entries))
        tags_extracted = 0
        for entry in all_matched_entries:
            tags = extract_article_tags(entry, config)
            if tags:
                tags_extracted += 1
        logging.info("🏷️  Tags extracted: %d articles tagged", tags_extracted)

    now_local = datetime.now(LOCAL_TZ)
    yesterday = now_local - timedelta(days=1)
    today = yesterday.strftime("%Y-%m-%d")
    
    # Extract URLs from highlights to prevent duplicates in category sections
    highlight_urls = extract_highlight_urls(top_highlights)
    logging.info("Excluding %d highlight articles from category sections to prevent duplicates", len(highlight_urls))
    
    # Option 3a: Extract and separate CVE references from editorial content
    all_cve_articles = []
    content_by_category = {}
    for cat, entries in reports.items():
        # Separate CVEs from editorial content
        cve_articles, editorial_articles = extract_cve_references(entries)
        all_cve_articles.extend(cve_articles)
        
        # Format editorial content only (CVEs get their own section)
        content_by_category[cat] = format_entries_for_category(editorial_articles, exclude_urls=highlight_urls)
    
    # Generate CVE reference section (if any CVEs found)
    cve_reference_section = format_cve_reference_section(all_cve_articles)
    logging.info("[CVE] Extracted %d CVE references for separate bulletin", len(all_cve_articles))
    
    # Option 3c: Generate trending topics dashboard (if tagging enabled)
    trending_dashboard = build_trending_topics_dashboard(reports, top_highlights, config)
    if trending_dashboard:
        logging.info("[TRENDING] Trending topics dashboard generated")

    # Phase 2: Dual-post output (Weekly Scan + Analyst Opinion + Story Clusters)
    phase2_enabled = config.get("synthesis", {}).get("enable_opinion_post", False)
    
    if phase2_enabled:
        # Create Weekly Scan post (with Story Clusters briefing + consolidated threat intel/vulnerability)
        weekly_scan_file = create_weekly_scan_post(today, content_by_category, top_highlights, cve_reference_section, trending_dashboard)
        logging.info("%s [PHASE 2] Weekly Scan generated: %s", GREEN, weekly_scan_file)
        
        # Detect trending category for analyst opinion
        trend_threshold = config.get("synthesis", {}).get("trend_threshold", 2)
        trending_data = detect_trending_category(reports, top_highlights, trend_threshold=trend_threshold)
        
        # Create Analyst Opinion post
        if trending_data:
            opinion_file = create_analyst_opinion_post(today, trending_data, config)
            logging.info("%s [PHASE 2] Analyst Opinion generated: %s", GREEN, opinion_file)
        else:
            logging.warning("[PHASE 2] Could not detect trending category; skipping opinion post")
        
        # Option 2: Update cross-run dedup registry with all published articles
        if cross_run_dedup_config.get("enabled", False):
            article_registry = update_registry_with_completed_run(all_matched_entries, article_registry, config)
            logging.info("[DEDUP] Article registry updated: %d articles tracked", len(article_registry))
        
        logging.info("%s News aggregation complete: Weekly Scan (with Story Clusters) + Analyst Opinion posts generated", GREEN)
    else:
        # Legacy Phase 1: Single post (news brief)
        create_news_brief(today, content_by_category, top_highlights, cve_reference_section, trending_dashboard)
        logging.info("%s [PHASE 1] News brief generated with %d articles across %d categories", GREEN, matched_entries, len(reports))
        
        # Option 2: Update cross-run dedup registry with all published articles
        if cross_run_dedup_config.get("enabled", False):
            article_registry = update_registry_with_completed_run(all_matched_entries, article_registry, config)
            logging.info("[DEDUP] Article registry updated: %d articles tracked", len(article_registry))


if __name__ == "__main__":
    main()