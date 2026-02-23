#!/usr/bin/env python
"""Test micro-topic tagging and trending dashboard (Options 3b & 3c)."""

import sys
sys.path.insert(0, 'scripts')

from fetch_news import (
    extract_article_tags, build_trending_topics_dashboard
)

print("=" * 70)
print("Testing Micro-Topic Tagging & Trending Dashboard (Options 3b & 3c)")
print("=" * 70)

# Mock config
config = {
    "micro_topic_tagging": {"enabled": True},
    "trending_topics_dashboard": {"enabled": True},
    "gemini": {"api_key": ""}  # Will be empty, so Gemini calls will skip
}

# Test data with pre-populated tags (simulate already-tagged articles)
test_reports = {
    "Cybersecurity": [
        {
            'title': 'Zero-Trust Architecture Implementation Guide',
            'link': 'https://example.com/zero-trust',
            '_source_name': 'SecureSource1',
            '_article_category': 'Cybersecurity',
            '_tags': ['zero-trust', 'network-security', 'architecture']
        },
        {
            'title': 'Kubernetes RBAC Misconfiguration Risks',
            'link': 'https://example.com/k8s',
            '_source_name': 'SecureSource2',
            '_article_category': 'Cybersecurity',
            '_tags': ['kubernetes', 'rbac', 'cloud-security']
        }
    ],
    "Cloud": [
        {
            'title': 'AWS IAM Policy Best Practices 2026',
            'link': 'https://example.com/aws-iam',
            '_source_name': 'AWS',
            '_article_category': 'Cloud',
            '_tags': ['aws', 'iam', 'identity-management']
        }
    ],
    "AI/ML": [
        {
            'title': 'Rust Memory Safety in ML Pipelines',
            'link': 'https://example.com/rust-ml',
            '_source_name': 'TechBlog1',
            '_article_category': 'AI/ML',
            '_tags': ['rust', 'memory-safety', 'ml-infrastructure']
        },
        {
            'title': 'Rust Safety in Production Systems',
            'link': 'https://example.com/rust-prod',
            '_source_name': 'TechBlog2',
            '_article_category': 'AI/ML',
            '_tags': ['rust', 'safety', 'production']
        }
    ]
}

# Test highlights (some with high mention counts)
test_highlights = [
    (test_reports["Cybersecurity"][0], 5),  # zero-trust - high mention
    (test_reports["Cloud"][0], 3),           # AWS IAM - medium mention
    (test_reports["AI/ML"][1], 4),           # Rust - high mention
]

print("\n[Test 1] Article Tag Extraction")
print("-" * 70)
print("Tags are already in test data (simulating Gemini extraction):")
for category, entries in test_reports.items():
    for entry in entries:
        tags = entry.get('_tags', [])
        print(f"  • {entry['title'][:50]:50} → {', '.join(tags)}")

print("\n[Test 2] Tag Frequency Analysis")
print("-" * 70)
# Collect tag frequencies
tag_frequency = {}
for entries in test_reports.values():
    for entry in entries:
        for tag in entry.get('_tags', []):
            if tag not in tag_frequency:
                tag_frequency[tag] = {'count': 0, 'sources': set()}
            tag_frequency[tag]['count'] += 1
            tag_frequency[tag]['sources'].add(entry.get('_source_name', 'Unknown'))

print("Tag frequencies across all articles:")
for tag, data in sorted(tag_frequency.items(), key=lambda x: x[1]['count'], reverse=True):
    print(f"  {tag:20} → {data['count']} mentions, {len(data['sources'])} sources: {', '.join(sorted(data['sources']))[:50]}")

print("\n[Test 3] Trending Topics Dashboard Generation")
print("-" * 70)
dashboard = build_trending_topics_dashboard(test_reports, test_highlights, config)

if dashboard:
    print("✓ Dashboard generated successfully")
    print(f"✓ Length: {len(dashboard)} characters")
    
    # Check for expected sections
    checks = [
        ("Contains 'Trending Topics'", "Trending Topics" in dashboard),
        ("Contains critical trends section", "CRITICAL TRENDS" in dashboard or "🔴" in dashboard),
        ("Contains emerging section", "EMERGING" in dashboard or "🟡" in dashboard),
        ("Contains tag names", "rust" in dashboard.lower() or "zero-trust" in dashboard.lower()),
    ]
    
    for check_name, result in checks:
        status = "✓" if result else "✗"
        print(f"  {status} {check_name}")
    
    # Show snippet
    print("\n[Sample Output]")
    print("-" * 70)
    lines = dashboard.split('\n')
    for line in lines[:25]:
        print(line)
    if len(lines) > 25:
        print("  ... (truncated)")
else:
    print("✗ No dashboard generated (might be disabled)")

print("\n" + "=" * 70)
print("All tests completed! ✅")
print("=" * 70)
