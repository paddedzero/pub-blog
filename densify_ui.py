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
        
        # 3. Replace Markdown Table with styled HTML Table
        def table_replacer(match):
            table_rows_str = match.group(1)
            row_pattern = re.compile(r'\|\s*([^|]*?)\s*\|\s*\d+\s*\|')
            rows = row_pattern.findall(table_rows_str)
            
            html_table = """<div class="relative w-full overflow-auto mb-6 border border-border/50 rounded-lg">
  <table class="w-full text-sm">
    <thead class="bg-secondary/30">
      <tr class="border-b border-border/50 transition-colors">
        <th class="h-10 px-4 text-left align-middle font-medium text-muted-foreground font-semibold">Category</th>
        <th class="h-10 px-4 text-right align-middle font-medium text-muted-foreground font-semibold">Article Count</th>
      </tr>
    </thead>
    <tbody class="[&_tr:last-child]:border-0">\n"""
            
            total_count = 0
            for cat_name in rows:
                cat_name = cat_name.strip()
                if cat_name in ["Category", "---"]: continue
                
                # Count actual details tags in the content for this category
                cat_section_pattern = re.compile(rf'## {re.escape(cat_name)}\n(.*?)(?=## |\Z)', re.DOTALL)
                section_match = cat_section_pattern.search(content)
                count = 0
                if section_match:
                    count = section_match.group(1).count('<details')
                
                html_table += f"""      <tr class="border-b border-border/50 transition-colors hover:bg-muted/50">
        <td class="p-3 px-4 align-middle font-medium">{cat_name}</td>
        <td class="p-3 px-4 align-middle text-right">{count}</td>
      </tr>\n"""
                total_count += count
                
            html_table += f"""    </tbody>
    <tfoot class="bg-primary/5 font-medium text-foreground border-t border-border/50">
      <tr>
        <td class="p-3 px-4 align-middle font-bold text-primary">Total Articles Scanned</td>
        <td class="p-3 px-4 align-middle text-right font-bold text-primary">{total_count}</td>
      </tr>
    </tfoot>
  </table>
</div>"""
            
            return "## Article Summary\n\n" + html_table

        content = re.sub(
            r'## Article Summary\n\n\| Category \| Article Count \|\n\|---\|---\|\n(.*?)\n+(?:\*\*Total Articles Scanned: \d+\*\*|Total Articles Scanned: \d+)',
            table_replacer,
            content,
            flags=re.DOTALL
        )

        # 4. Upgrade any existing HTML Table (Phase 11 or broken Phase 12) to clean Premium Card Table
        def premium_table_replacer(match):
            html_content = match.group(0)
            
            # Extract categories from ANY td variant (Phase 11 or Phase 12 classes)
            cat_pattern = re.compile(r'<td class="(?:p-3 px-4 align-middle|px-6 py-3) font-medium">(.*?)</td>')
            categories = cat_pattern.findall(html_content)
            # Deduplicate while preserving order (broken runs may have dupes)
            seen = set()
            unique_cats = []
            for c in categories:
                if c not in seen:
                    seen.add(c)
                    unique_cats.append(c)
            categories = unique_cats
            
            html_table = """<div class="not-prose my-8 overflow-hidden rounded-xl border border-border bg-secondary/20 text-card-foreground shadow-lg">
  <table class="w-full text-sm text-left">
    <thead class="bg-secondary/40 border-b border-border">
      <tr>
        <th class="px-6 py-3 font-semibold text-foreground">
          <span class="flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-primary"><path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z"/><path d="M7 7h.01"/></svg>
            Category
          </span>
        </th>
        <th class="px-6 py-3 font-semibold text-foreground text-right">
          <span class="flex items-center justify-end gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-primary"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
            Article Count
          </span>
        </th>
      </tr>
    </thead>
    <tbody class="divide-y divide-border">\n"""
            
            total_count = 0
            for cat_name in categories:
                cat_section_pattern = re.compile(rf'## {re.escape(cat_name)}\n(.*?)(?=## |\Z)', re.DOTALL)
                section_match = cat_section_pattern.search(content)
                count = 0
                if section_match:
                    count = section_match.group(1).count('<details')
                
                html_table += f"""      <tr class="hover:bg-secondary/30 transition-colors">
        <td class="px-6 py-3 font-medium">{cat_name}</td>
        <td class="px-6 py-3 text-right text-muted-foreground">{count}</td>
      </tr>\n"""
                total_count += count
                
            html_table += f"""    </tbody>
    <tfoot class="bg-secondary/40 font-semibold border-t-2 border-border">
      <tr>
        <td class="px-6 py-4 text-foreground">Total Articles Scanned</td>
        <td class="px-6 py-4 text-right text-primary">{total_count}</td>
      </tr>
    </tfoot>
  </table>
</div>"""
            
            return "## Article Summary\n\n" + html_table + "\n\n"

        # Match from "## Article Summary" all the way to the next "## " heading
        # This captures the ENTIRE block including all nested divs/tables
        content = re.sub(
            r'## Article Summary\n\n<div class="(?:relative|not-prose)[^>]*>.*?(?=\n## [A-Z])',
            premium_table_replacer,
            content,
            flags=re.DOTALL
        )

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {file_path}")
            updated_count += 1
            
    print(f"\nSuccessfully densified UI in {updated_count} files out of {len(md_files)}.")

if __name__ == "__main__":
    process_files()
