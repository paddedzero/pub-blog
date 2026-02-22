import os
import glob
import re

POSTS_DIR = "site/content/newsfeed"

def process_test():
    md_files = glob.glob(os.path.join(POSTS_DIR, "*.md"))
    content = ""
    with open("site/content/newsfeed/2026-01-25-03-21-weekly-scan.md", 'r', encoding='utf-8') as f:
        content = f.read()
        
    pattern = re.compile(
        r'- \*\*(.*?)\*\* —\s*(.*?)\n\s*<a href="(.*?)">.*?</a>(.*?)\n',
        re.MULTILINE
    )
    
    matches = pattern.findall(content)
    print(f"Found {len(matches)} markdown bullet articles.")
    if len(matches) > 0:
        print(f"Sample 1: {matches[0]}")
        print(f"Sample 2: {matches[-1]}")

if __name__ == "__main__":
    process_test()
