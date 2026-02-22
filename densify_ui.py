import os
import glob
import re

POSTS_DIR = "site/content/newsfeed"

def extract_snippet(summary):
    """Extract a short snippet for the dense single-line preview"""
    snippet = summary.split('.')[0] if '.' in summary else summary
    if len(snippet) > 80:
        snippet = snippet[:77] + "..."
    return snippet

def process_files():
    md_files = glob.glob(os.path.join(POSTS_DIR, "*.md"))
    updated_count = 0
    
    # Matches any historically generated <details> that uses the bulky tailwind padding/border
    bulky_pattern = re.compile(
        r'<details class="mb-4 group border border-border rounded-lg overflow-hidden.*?>\s*'
        r'<summary.*?>\s*'
        r'<span class="text-foreground.*?">(.*?)</span>\s*'
        r'<span class="text-muted-foreground.*?">▼</span>\s*'
        r'</summary>\s*'
        r'<div class="p-4.*?">\s*'
        r'<p class="text-muted-foreground.*?">(.*?)</p>\s*'
        r'(.*?)\s*' # Optional link block or read more text
        r'</div>\s*'
        r'</details>',
        re.MULTILINE | re.DOTALL
    )
    
    # Matches the very old Markdown Bullets
    # Example:
    # - **Title** — Summary
    #   <a href="link">Read more</a> *(Covered by: XYZ)*
    bullet_pattern = re.compile(
        r'- \*\*(.*?)\*\* —\s*(.*?)\n\s*<a href="(.*?)".*?>(.*?)</a>(.*?)(?:\n|$)',
        re.MULTILINE
    )
    
    def bulky_replacer(match):
        title_with_potential_badges = match.group(1).strip()
        summary = match.group(2).strip()
        link_block = match.group(3).strip()
        
        snippet = extract_snippet(summary)
        
        dense = (
            f"<details class=\"group border-b border-border/50 py-1\">\n"
            f"  <summary class=\"cursor-pointer hover:bg-secondary/30 transition-colors list-none flex items-center justify-between py-1.5 px-2\">\n"
            f"    <div class=\"flex-1 flex flex-col md:flex-row md:items-center gap-1 md:gap-3 overflow-hidden mr-4\">\n"
            f"      <span class=\"text-sm font-medium text-foreground whitespace-nowrap overflow-hidden text-ellipsis md:max-w-[50%]\">{title_with_potential_badges}</span>\n"
            f"      <span class=\"text-xs text-muted-foreground whitespace-nowrap overflow-hidden text-ellipsis flex-1\">{snippet}</span>\n"
            f"    </div>\n"
            f"    <span class=\"text-muted-foreground text-xs shrink-0 group-open:rotate-180 transition-transform\">▼</span>\n"
            f"  </summary>\n"
            f"  <div class=\"p-3 bg-secondary/10 rounded-md mt-1 mb-2 text-sm mx-2\">\n"
            f"    <p class=\"text-muted-foreground mb-3 leading-relaxed\">{summary}</p>\n"
        )
        if link_block:
            dense += f"    {link_block}\n"
        else:
            dense += f"    <p class=\"text-muted-foreground italic\">Read more (link unavailable)</p>\n"
            
        dense += f"  </div>\n</details>"
        return dense
        
    def bullet_replacer(match):
        title = match.group(1).strip()
        summary = match.group(2).strip()
        link = match.group(3).strip()
        trailing = match.group(5).strip() # Could be " *(Covered by: ...)*"
        
        snippet = extract_snippet(summary)
        
        link_html = f"<a href='{link}' target='_blank' rel='noopener noreferrer' class=\"read-more-btn\">Read Full Article →</a>" if link else "<p class=\"text-muted-foreground italic\">Read more (link unavailable)</p>"
        
        if trailing:
            link_html += f" <span class=\"text-xs text-muted-foreground ml-2\">{trailing}</span>"
            
        dense = (
            f"<details class=\"group border-b border-border/50 py-1\">\n"
            f"  <summary class=\"cursor-pointer hover:bg-secondary/30 transition-colors list-none flex items-center justify-between py-1.5 px-2\">\n"
            f"    <div class=\"flex-1 flex flex-col md:flex-row md:items-center gap-1 md:gap-3 overflow-hidden mr-4\">\n"
            f"      <span class=\"text-sm font-medium text-foreground whitespace-nowrap overflow-hidden text-ellipsis md:max-w-[50%]\">{title}</span>\n"
            f"      <span class=\"text-xs text-muted-foreground whitespace-nowrap overflow-hidden text-ellipsis flex-1\">{snippet}</span>\n"
            f"    </div>\n"
            f"    <span class=\"text-muted-foreground text-xs shrink-0 group-open:rotate-180 transition-transform\">▼</span>\n"
            f"  </summary>\n"
            f"  <div class=\"p-3 bg-secondary/10 rounded-md mt-1 mb-2 text-sm mx-2\">\n"
            f"    <p class=\"text-muted-foreground mb-3 leading-relaxed\">{summary}</p>\n"
            f"    {link_html}\n"
            f"  </div>\n"
            f"</details>\n"
        )
        return dense

    for file_path in md_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original_content = content
        
        # 1. Update all bulky articles to dense list format
        content = bulky_pattern.sub(bulky_replacer, content)
        
        # 2. Update all OLD markdown bullet articles to dense list format
        content = bullet_pattern.sub(bullet_replacer, content)
        
        # 3. Fix broken table article counts
        def count_replacer(match):
            cat_name = match.group(1).strip()
            cat_section_pattern = re.compile(rf'## {re.escape(cat_name)}\n(.*?)(?=## |\Z)', re.DOTALL)
            section_match = cat_section_pattern.search(content)
            if section_match:
                count = section_match.group(1).count('<details')
                return f"| {cat_name} | {count} |"
            return match.group(0)
            
        content = re.sub(r'\|\s*([^|]*?)\s*\|\s*\d+\s*\|', count_replacer, content)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {file_path}")
            updated_count += 1
            
    print(f"\nSuccessfully densified UI in {updated_count} files out of {len(md_files)}.")

if __name__ == "__main__":
    process_files()
