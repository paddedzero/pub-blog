#!/usr/bin/env python3
"""Test negative keyword filtering directly."""
import sys
sys.path.insert(0, 'scripts')

from fetch_news import matches_negative_keywords
import yaml

# Load config
config = yaml.safe_load(open('scripts/config.yaml'))

# Test articles
test_articles = [
    {
        "title": "Webinar: How Modern SOC Teams Use AI",
        "summary": "Join us for a webinar on modern SOC practices",
        "description": "",
        "link": "https://example.com/webinar"
    },
    {
        "title": "Fast, Cheap + Good Whitepaper",
        "summary": "Our latest whitepaper on AppSec",
        "description": "",
        "link": "https://example.com/whitepaper"
    },
    {
        "title": "New Security Certification Program",
        "summary": "Get certified in IAM security",
        "description": "",
        "link": "https://example.com/cert"
    },
    {
        "title": "Critical CVE-2026-1234 Remote Code Execution",
        "summary": "A new critical RCE vulnerability was discovered",
        "description": "",
        "link": "https://example.com/cve"
    }
]

print("Testing negative keyword filtering:\n")
print("=" * 60)

for i, article in enumerate(test_articles, 1):
    blocked = matches_negative_keywords(article, config)
    status = "❌ BLOCKED" if blocked else "✅ PASS"
    print(f"{i}. {article['title']}")
    print(f"   Status: {status}")
    print()

print("=" * 60)
print(f"\nConfig negative_keywords enabled: {config.get('negative_keywords', {}).get('enabled')}")
print(f"Block terms count: {len(config.get('negative_keywords', {}).get('block_terms', []))}")
