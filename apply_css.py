import glob, re

# This regex matches the exact long HTML string for the button class previously injected
css_pattern = re.compile(r'class=[\'\"]inline-flex items-center justify-center.*?[\'\"]')
files = glob.glob('site/content/newsfeed/*.md') + glob.glob('site/content/posts/*.md') + ['scripts/fetch_news.py']

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if css_pattern.search(content):
            new_content = css_pattern.sub('class="read-more-btn"', content)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'Updated {filepath}')
    except Exception as e:
        print(f"Skipping {filepath}: {e}")
