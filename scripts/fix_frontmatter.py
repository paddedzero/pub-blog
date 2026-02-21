#!/usr/bin/env python3
"""
Fix post front matter to match Spaceship's schema.

Spaceship schema:
  title: string (required)
  description: string (required)
  pubDate: date (required)
  tags: list (default ['others'])
  draft: bool (default false)
  featured: bool (optional)
  ogImage: string (optional)
  showCTA: bool (default true)    -> we'll set false
  showComments: bool (default true) -> we'll set false

We remove: categories, author, aiGenerated, updatedDate
We add: draft: false
We ensure: description is always present (use title if missing)
"""

import re
from pathlib import Path

POSTS_DIR = Path("site/content/posts")

def fix_frontmatter(content: str, filename: str) -> str:
    # Match frontmatter block
    match = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n(.*)$', content, re.DOTALL)
    if not match:
        print(f"  ⚠️  No frontmatter: {filename}")
        return content

    fm_str, body = match.groups()

    # Parse fields
    fields = {}
    for line in fm_str.splitlines():
        if ':' in line:
            key, _, value = line.partition(':')
            fields[key.strip()] = value.strip()

    # Extract values
    title = fields.get('title', '').strip('"').strip("'")
    description = fields.get('description', '').strip('"').strip("'")
    pub_date = fields.get('pubDate', fields.get('pubdate', '')).strip()

    # tags: parse list like ["cloud", "ai"] or keep as-is
    tags_raw = fields.get('tags', '["tech-news"]').strip()
    # Normalize to proper list string
    tag_items = re.findall(r'"([^"]+)"|\'([^\']+)\'', tags_raw)
    tag_list = [a or b for a, b in tag_items]
    if not tag_list:
        tag_list = ['tech-news']
    tags_str = '["' + '", "'.join(tag_list) + '"]'

    # Ensure description is present
    if not description:
        description = title[:150]

    # Escape double quotes in title and description
    title_safe = title.replace('"', '\\"')
    desc_safe = description.replace('"', '\\"')

    # Build new front matter (Spaceship-compatible)
    new_fm = f'''---
title: "{title_safe}"
description: "{desc_safe}"
pubDate: {pub_date}
tags: {tags_str}
draft: false
showCTA: false
showComments: false
---
'''
    return new_fm + body

def main():
    posts = list(POSTS_DIR.glob("*.md"))
    # Skip template files
    posts = [p for p in posts if not p.name.startswith('_')]
    print(f"Found {len(posts)} posts to fix")

    for post_path in sorted(posts):
        content = post_path.read_text(encoding='utf-8')
        fixed = fix_frontmatter(content, post_path.name)
        post_path.write_text(fixed, encoding='utf-8')
        print(f"  ✅ Fixed: {post_path.name}")

    print(f"\nDone! Updated {len(posts)} posts in {POSTS_DIR}")

if __name__ == "__main__":
    main()
