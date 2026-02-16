#!/usr/bin/env python3
"""
Migrate Jekyll posts from feedmeup to Astro format for pub-blog.

This script:
1. Fetches all posts from the feedmeup GitHub repository
2. Converts Jekyll front matter to Astro content collection format
3. Saves converted posts to src/content/posts/
"""

import re
import requests
from pathlib import Path
from datetime import datetime

# Configuration
GITHUB_API_URL = "https://api.github.com/repos/paddedzero/feedmeup/contents/_posts"
OUTPUT_DIR = Path("src/content/posts")

def convert_front_matter(jekyll_content):
    """Convert Jekyll front matter to Astro format."""
    
    # Extract front matter
    pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.search(pattern, jekyll_content, re.DOTALL)
    
    if not match:
        print("Warning: No front matter found")
        return jekyll_content
    
    front_matter_str, content = match.groups()
    
    # Parse Jekyll front matter fields
    fm_dict = {}
    for line in front_matter_str.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            fm_dict[key.strip()] = value.strip()
    
    # Convert date format
    # Jekyll: "2026-01-01 22:43:00 +0000"
    # Astro: "2026-01-01"
    date_str = fm_dict.get('date', '')
    if date_str:
        # Extract just the date part (YYYY-MM-DD)
        date_match = re.match(r'(\d{4}-\d{2}-\d{2})', date_str)
        if date_match:
            pub_date = date_match.group(1)
        else:
            pub_date = datetime.now().strftime('%Y-%m-%d')
    else:
        pub_date = datetime.now().strftime('%Y-%m-%d')
    
    # Extract categories
    categories_str = fm_dict.get('categories', '[]')
    # Parse categories properly - Jekyll uses [Cat1, Cat2]
    # Convert to Astro ["cat1", "cat2"]
    categories_match = re.findall(r'\[(.*?)\]', categories_str)
    if categories_match:
        cats_inner = categories_match[0]
        # Split by comma and clean up
        cat_list = [c.strip().strip('"').strip("'").lower().replace(' ', '-') 
                    for c in cats_inner.split(',') if c.strip()]
        categories = '["' + '", "'.join(cat_list) + '"]'
    else:
        categories = '["uncategorized"]'

    
    # Build Astro front matter
    title = fm_dict.get('title', '').strip('"')
    description = title[:150] if len(title) > 150 else title  # Use title as description
    
    # Determine tags based on category
    if 'analyst-opinion' in categories:
        tags = '["analysis", "commentary", "ai-generated"]'
    elif 'newsbrief' in categories:
        tags = '["cloud", "cybersecurity", "ai", "ml", "automation"]'
    else:
        tags = '["tech-news"]'
    
    astro_front_matter = f"""---
title: "{title}"
description: "{description}"
pubDate: {pub_date}
categories: {categories}
tags: {tags}
author: "feedmeup"
aiGenerated: true
---
"""
    
    return astro_front_matter + content


def migrate_posts():
    """Fetch and migrate all posts from feedmeup."""
    
    print("Fetching posts list from feedmeup...")
    
    # Fetch posts list
    response = requests.get(GITHUB_API_URL)
    if response.status_code != 200:
        print(f"Error fetching posts: {response.status_code}")
        return
    
    posts = response.json()
    print(f"Found {len(posts)} posts to migrate")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    migrated_count = 0
    skipped_count = 0
    
    for post in posts:
        filename = post['name']
        download_url = post['download_url']
        
        output_path = OUTPUT_DIR / filename
        
        # Skip if already migrated
        if output_path.exists():
            print(f"  ⏭️  Skipping (already exists): {filename}")
            skipped_count += 1
            continue
        
        # Download post content
        print(f"  📥 Downloading: {filename}")
        content_response = requests.get(download_url)
        
        if content_response.status_code != 200:
            print(f"  ❌ Failed to download: {filename}")
            continue
        
        jekyll_content = content_response.text
        
        # Convert front matter
        astro_content = convert_front_matter(jekyll_content)
        
        # Save to output directory
        output_path.write_text(astro_content, encoding='utf-8')
        print(f"  ✅ Migrated: {filename}")
        migrated_count += 1
    
    print(f"\n{'='*50}")
    print(f"Migration complete!")
    print(f"  📄 Migrated: {migrated_count} posts")
    print(f"  ⏭️  Skipped: {skipped_count} posts (already exist)")
    print(f"  📁 Output: {OUTPUT_DIR.absolute()}")
    print(f"{'='*50}")


if __name__ == "__main__":
    migrate_posts()
