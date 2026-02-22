import glob, re
import sys

def main():
    files = glob.glob('site/content/newsfeed/*.md')
    
    # 1. Category headers regex
    # Matches: ## AI & LLM
    # Excludes specific control headers
    cat_pattern = re.compile(r'^## (?!This Week in Security|Top Trending Stories|Article Summary|Top Trending|Article summary|This week in security)(.+)$', re.MULTILINE)
    
    def cat_replacer(match):
        category = match.group(1).strip()
        return (f"<h2 class=\"mt-8 mb-4 pb-2 border-b-2 border-primary/20 text-2xl font-bold tracking-tight text-primary flex items-center gap-2\">\n"
                f"  <span class=\"bg-primary/10 text-primary px-3 py-1 rounded-md text-sm uppercase tracking-wider\">Category</span>\n"
                f"  {category}\n"
                f"</h2>")

    # 2. Top Trending Normal items regex
    # Matches: 1. **Title** (X mentions)\n   > Summary\n   > <a href="...">Read more</a>
    # Note: the summary might have embedded HTML if clean_summary failed, but usually it's just raw text.
    tt_normal_pattern = re.compile(
        r'^(\d+)\.\s+\*\*(.+?)\*\*\s+\((\d+)\s+mentions\)\n\s+>\s+(.*?)\n\s+>\s+<a\s+href="([^"]+)">Read\s+more</a>|'
        r'^(\d+)\.\s+\*\*(.+?)\*\*\s+\((\d+)\s+mentions\)\n\s+>\s+(.*?)\n\s+>\s+Read\s+more\s+\(link\s+unavailable\)',
        re.MULTILINE
    )

    def tt_normal_replacer(match):
        if match.group(1): # Link available
            num = match.group(1)
            title = match.group(2)
            mentions = match.group(3)
            summary = match.group(4)
            link = match.group(5)
            link_html = f'<a href="{link}" target="_blank" rel="noopener noreferrer" class="read-more-btn">Read Full Article →</a>'
        else: # Link unavailable
            num = match.group(6)
            title = match.group(7)
            mentions = match.group(8)
            summary = match.group(9)
            link_html = f'<p class="text-muted-foreground italic">Read more (link unavailable)</p>'
            
        return (f"<details class=\"mb-4 group border border-border rounded-lg overflow-hidden\">\n"
                f"  <summary class=\"font-bold cursor-pointer bg-secondary/50 p-3 hover:bg-secondary transition-colors list-none flex items-center justify-between\">\n"
                f"    <span class=\"text-foreground\">{num}. {title} ({mentions} mentions)</span>\n"
                f"    <span class=\"text-muted-foreground text-sm group-open:rotate-180 transition-transform\">▼</span>\n"
                f"  </summary>\n"
                f"  <div class=\"p-4 bg-background\">\n"
                f"    <p class=\"text-muted-foreground mb-4\">{summary}</p>\n"
                f"    {link_html}\n"
                f"  </div>\n"
                f"</details>")

    # 3. Top Trending Threat Intel items regex
    # This one is trickier. Let's find: 1. **Key Threat Intel & Vulnerability Stories** (X mentions)\n   > This week's critical...\n   > • [Title](Link) (X mentions)
    # Because lists can vary in length, we capture the whole block of bullets.
    tt_threat_pattern = re.compile(
        r'^(\d+)\.\s+\*\*Key Threat Intel & Vulnerability Stories\*\*\s+\((\d+)\s+mentions\)\n\s+>\s+This week\'s critical security updates and vulnerability disclosures:\n((?:\s+>\s+•.*?(?:\n|$))+)',
        re.MULTILINE
    )

    def tt_threat_replacer(match):
        num = match.group(1)
        mentions = match.group(2)
        bullets_raw = match.group(3)
        
        # parse the bullets
        bullets_html = ""
        for line in bullets_raw.split('\n'):
            line = line.strip()
            if not line: continue
            if line.startswith('> • '):
                content = line[4:] # strip "> • "
                
                # Try to parse [Title](Link) (count mentions)
                m = re.match(r'^\[(.+?)\]\((.+?)\)\s+\((.+?)\)$', content)
                if m:
                    title, link, count = m.groups()
                    bullets_html += f"      <li><a href=\"{link}\" class=\"text-primary hover:underline\">{title}</a> ({count})</li>\n"
                else:
                    bullets_html += f"      <li>{content}</li>\n"
                    
        return (f"<details class=\"mb-4 group border border-border rounded-lg overflow-hidden\">\n"
                f"  <summary class=\"font-bold cursor-pointer bg-secondary/50 p-3 hover:bg-secondary transition-colors list-none flex items-center justify-between\">\n"
                f"    <span class=\"text-foreground\">{num}. Key Threat Intel & Vulnerability Stories ({mentions} mentions)</span>\n"
                f"    <span class=\"text-muted-foreground text-sm group-open:rotate-180 transition-transform\">▼</span>\n"
                f"  </summary>\n"
                f"  <div class=\"p-4 bg-background\">\n"
                f"    <p class=\"text-muted-foreground mb-4\">This week's critical security updates and vulnerability disclosures:</p>\n"
                f"    <ul class=\"list-disc pl-5 mb-4 text-muted-foreground\">\n"
                f"{bullets_html}"
                f"    </ul>\n"
                f"  </div>\n"
                f"</details>")

    count = 0
    for filepath in files:
        changed = False
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Apply replacements
            new_content = tt_threat_pattern.sub(tt_threat_replacer, content)
            new_content = tt_normal_pattern.sub(tt_normal_replacer, new_content)
            new_content = cat_pattern.sub(cat_replacer, new_content)

            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {filepath}")
                count += 1
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            
    print(f"Successfully processed {count} files.")

if __name__ == '__main__':
    main()
