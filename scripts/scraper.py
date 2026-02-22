"""
Web Scraper Module for Non-RSS Feed Sources
Handles article extraction from sites without RSS feeds using BeautifulSoup.
"""

import logging
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo

# Rate limiting: delay between requests to same domain
SCRAPE_DELAY = 2  # seconds
LOCAL_TZ = ZoneInfo("America/New_York")


class ArticleScraper:
    """Base class for site-specific scrapers."""
    
    def __init__(self, session, site_name, base_url):
        self.session = session
        self.site_name = site_name
        self.base_url = base_url
        self.last_request_time = 0
        
    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < SCRAPE_DELAY:
            time.sleep(SCRAPE_DELAY - elapsed)
        self.last_request_time = time.time()
    
    def _fetch_page(self, url):
        """Fetch HTML content with error handling."""
        try:
            self._rate_limit()
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logging.warning(f"[SCRAPER] Failed to fetch {url}: {e}")
            return None
    
    def scrape(self):
        """Override in subclass. Returns list of article dicts."""
        raise NotImplementedError


class MicrosoftMSRCScraper(ArticleScraper):
    """Scraper for Microsoft Security Response Center blog."""
    
    def scrape(self):
        """Extract articles from MSRC blog page."""
        articles = []
        soup = self._fetch_page(self.base_url)
        if not soup:
            return articles
        
        try:
            # Find article containers (adjust selectors based on actual HTML structure)
            # This is a template - needs verification with actual site
            article_elements = soup.select('article, .post, .entry, .blog-post')
            
            for element in article_elements[:10]:  # Limit to 10 most recent
                try:
                    # Extract title
                    title_elem = element.select_one('h2 a, h3 a, .title a, .entry-title a')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    link = urljoin(self.base_url, title_elem.get('href', ''))
                    
                    # Extract summary/excerpt
                    summary_elem = element.select_one('.excerpt, .summary, p')
                    summary = summary_elem.get_text(strip=True) if summary_elem else ""
                    
                    # Extract date (try multiple selectors)
                    date_elem = element.select_one('time, .date, .published, .post-date')
                    pub_date = None
                    if date_elem:
                        date_str = date_elem.get('datetime') or date_elem.get_text(strip=True)
                        pub_date = self._parse_date(date_str)
                    
                    if not pub_date:
                        pub_date = datetime.now(LOCAL_TZ)
                    
                    articles.append({
                        'title': title,
                        'link': link,
                        'summary': summary,
                        'description': summary,
                        'published_parsed': pub_date.timetuple()[:6],
                    })
                    
                except Exception as e:
                    logging.debug(f"[MSRC] Error parsing article: {e}")
                    continue
                    
        except Exception as e:
            logging.warning(f"[MSRC] Scraping error: {e}")
        
        logging.info(f"[SCRAPER] {self.site_name}: extracted {len(articles)} articles")
        return articles
    
    def _parse_date(self, date_str):
        """Parse various date formats."""
        from dateutil import parser
        try:
            return parser.parse(date_str).replace(tzinfo=LOCAL_TZ)
        except Exception:
            return datetime.now(LOCAL_TZ)


class PacketStormScraper(ArticleScraper):
    """Scraper for Packet Storm Security news."""
    
    def scrape(self):
        """Extract articles from Packet Storm news page."""
        articles = []
        soup = self._fetch_page(self.base_url)
        if not soup:
            return articles
        
        try:
            # Packet Storm has a news list structure
            news_items = soup.select('.news, .article, .item, li.newsitem')
            
            for item in news_items[:10]:
                try:
                    title_elem = item.select_one('a, h3 a, .title a')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    link = urljoin(self.base_url, title_elem.get('href', ''))
                    
                    # Extract description
                    desc_elem = item.select_one('p, .description, .summary')
                    description = desc_elem.get_text(strip=True) if desc_elem else ""
                    
                    # Date extraction
                    date_elem = item.select_one('.date, time')
                    pub_date = datetime.now(LOCAL_TZ)
                    if date_elem:
                        pub_date = self._parse_date(date_elem.get_text(strip=True))
                    
                    articles.append({
                        'title': title,
                        'link': link,
                        'summary': description,
                        'description': description,
                        'published_parsed': pub_date.timetuple()[:6],
                    })
                    
                except Exception as e:
                    logging.debug(f"[PacketStorm] Error parsing item: {e}")
                    continue
                    
        except Exception as e:
            logging.warning(f"[PacketStorm] Scraping error: {e}")
        
        logging.info(f"[SCRAPER] {self.site_name}: extracted {len(articles)} articles")
        return articles
    
    def _parse_date(self, date_str):
        """Parse date strings."""
        from dateutil import parser
        try:
            return parser.parse(date_str).replace(tzinfo=LOCAL_TZ)
        except Exception:
            return datetime.now(LOCAL_TZ)


class CISAScraper(ArticleScraper):
    """Scraper for CISA alerts and advisories."""
    
    def scrape(self):
        """Extract articles from CISA alerts page."""
        articles = []
        soup = self._fetch_page(self.base_url)
        if not soup:
            return articles
        
        try:
            # CISA typically has a table or list of alerts
            alert_items = soup.select('tr, .item, .alert-item, article')
            
            for item in alert_items[:15]:  # More alerts since they're shorter
                try:
                    # Find link/title
                    link_elem = item.select_one('a')
                    if not link_elem:
                        continue
                    
                    title = link_elem.get_text(strip=True)
                    link = urljoin(self.base_url, link_elem.get('href', ''))
                    
                    # Extract ID/description
                    desc_parts = [td.get_text(strip=True) for td in item.select('td')]
                    description = ' - '.join(desc_parts) if desc_parts else title
                    
                    # Date
                    date_elem = item.select_one('.date, time, td:first-child')
                    pub_date = datetime.now(LOCAL_TZ)
                    if date_elem:
                        pub_date = self._parse_date(date_elem.get_text(strip=True))
                    
                    articles.append({
                        'title': title,
                        'link': link,
                        'summary': description,
                        'description': description,
                        'published_parsed': pub_date.timetuple()[:6],
                    })
                    
                except Exception as e:
                    logging.debug(f"[CISA] Error parsing alert: {e}")
                    continue
                    
        except Exception as e:
            logging.warning(f"[CISA] Scraping error: {e}")
        
        logging.info(f"[SCRAPER] {self.site_name}: extracted {len(articles)} articles")
        return articles
    
    def _parse_date(self, date_str):
        """Parse date strings."""
        from dateutil import parser
        try:
            # CISA uses MM/DD/YYYY format typically
            return parser.parse(date_str).replace(tzinfo=LOCAL_TZ)
        except Exception:
            return datetime.now(LOCAL_TZ)


class GenericBlogScraper(ArticleScraper):
    """Generic scraper for blog-style sites."""
    
    def scrape(self):
        """Extract articles using common blog HTML patterns."""
        articles = []
        soup = self._fetch_page(self.base_url)
        if not soup:
            return articles
        
        try:
            # Try multiple common selectors
            article_elements = (
                soup.select('article') or
                soup.select('.post') or
                soup.select('.entry') or
                soup.select('.blog-post') or
                soup.select('.item')
            )
            
            for element in article_elements[:10]:
                try:
                    # Title extraction
                    title_elem = (
                        element.select_one('h2 a') or
                        element.select_one('h3 a') or
                        element.select_one('.title a') or
                        element.select_one('a')
                    )
                    
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    link = urljoin(self.base_url, title_elem.get('href', ''))
                    
                    # Summary extraction
                    summary_elem = (
                        element.select_one('.excerpt') or
                        element.select_one('.summary') or
                        element.select_one('p')
                    )
                    summary = summary_elem.get_text(strip=True)[:500] if summary_elem else ""
                    
                    # Date extraction
                    date_elem = (
                        element.select_one('time') or
                        element.select_one('.date') or
                        element.select_one('.published')
                    )
                    
                    pub_date = datetime.now(LOCAL_TZ)
                    if date_elem:
                        date_str = date_elem.get('datetime') or date_elem.get_text(strip=True)
                        pub_date = self._parse_date(date_str)
                    
                    articles.append({
                        'title': title,
                        'link': link,
                        'summary': summary,
                        'description': summary,
                        'published_parsed': pub_date.timetuple()[:6],
                    })
                    
                except Exception as e:
                    logging.debug(f"[{self.site_name}] Error parsing article: {e}")
                    continue
                    
        except Exception as e:
            logging.warning(f"[{self.site_name}] Scraping error: {e}")
        
        logging.info(f"[SCRAPER] {self.site_name}: extracted {len(articles)} articles")
        return articles
    
    def _parse_date(self, date_str):
        """Parse date with multiple format support."""
        from dateutil import parser
        try:
            return parser.parse(date_str).replace(tzinfo=LOCAL_TZ)
        except Exception:
            return datetime.now(LOCAL_TZ)


# Scraper registry: maps site names to scraper classes
SCRAPER_REGISTRY = {
    'Microsoft MSRC': MicrosoftMSRCScraper,
    'Packet Storm Security': PacketStormScraper,
    'CISA': CISAScraper,
    # Add more as they're implemented
}


def scrape_site(session, site_name, url):
    """
    Scrape articles from a site using the appropriate scraper.
    
    Args:
        session: requests.Session object
        site_name: Name of the site (for scraper selection)
        url: Base URL to scrape
    
    Returns:
        tuple: (list of articles, status string)
    """
    try:
        # Select scraper
        scraper_class = SCRAPER_REGISTRY.get(site_name, GenericBlogScraper)
        scraper = scraper_class(session, site_name, url)
        
        # Execute scraping
        articles = scraper.scrape()
        
        if articles:
            return articles, "OK"
        else:
            return [], "NO_ARTICLES"
            
    except Exception as e:
        logging.error(f"[SCRAPER] {site_name} failed: {e}")
        return [], f"ERROR: {str(e)}"


def is_scraping_candidate(category):
    """Check if a feed category should use scraping."""
    return category == "Scraping Candidates"
