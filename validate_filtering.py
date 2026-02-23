#!/usr/bin/env python3
"""Validate that negative keyword filtering is working correctly."""
import sys
from pathlib import Path

# Negative keywords that should NOT appear in output
NEGATIVE_KEYWORDS = [
    "press release",
    "announces partnership", 
    "is pleased to announce",
    "excited to introduce",
    "new product launch",
    "we're thrilled",
    "partnership announcement",
    "customer success story",
    "tutorial",
    "how-to guide",
    "getting started",
    "course",
    "certification",
    "webinar",
    "workshop",
    "training session",
    "case study",
    "white paper",
    "whitepaper",
    "testimonial",
    "success story",
    "customer spotlight",
]

def validate_post(filepath):
    """Check if post contains negative keywords."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read().lower()
    
    found_issues = []
    for keyword in NEGATIVE_KEYWORDS:
        if keyword.lower() in content:
            found_issues.append(keyword)
    
    return found_issues

# Get latest post
posts_dir = Path("site/content/newsfeed")
latest_post = sorted(posts_dir.glob("*-weekly-scan.md"), reverse=True)[0]

print(f"Validation Report: {latest_post.name}\n")
print("=" * 60)

issues = validate_post(latest_post)

if not issues:
    print("✅ PASS: No negative keywords found in output\n")
    print("Summary:")
    print(f"  - File: {latest_post.name}")
    print(f"  - Checked: {len(NEGATIVE_KEYWORDS)} negative keywords")
    print(f"  - Result: CLEAN - Filtering is working!")
else:
    print(f"⚠️  ISSUES FOUND: {len(issues)} negative keywords detected\n")
    print("Keywords found in post:")
    for kw in sorted(set(issues)):
        print(f"  - {kw}")
    print("\nThese should have been filtered out.")

print("=" * 60)

# Get file stats
file_size = latest_post.stat().st_size
with open(latest_post, 'r', encoding='utf-8', errors='replace') as f:
    lines = len(f.readlines())
    
print(f"\nFile Statistics:")
print(f"  - Size: {file_size:,} bytes ({file_size // 1024}KB)")
print(f"  - Lines: {lines:,}")
print(f"  - Status: {'✅ FILTERED' if not issues else '⚠️  UNFILTERED'}")
