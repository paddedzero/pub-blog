# Weekly Scan Aggregator: Improvement Implementation Plan

**Date:** February 22, 2026  
**Status:** Awaiting Approval  
**Target Deployment:** Phase 1 (Immediate) + Phase 2 (Advanced Features)

---

## Executive Summary

This plan implements 5 major improvements to eliminate article redundancy, enhance source diversity, and consolidate multi-source stories with citation-style referencing.

### Quick Stats
- **Current Feeds:** 150+ sources across 8 categories
- **Current Deduplication:** Basic fuzzy matching (0.8 threshold)
- **Current Issue:** Same CVE/story appears 8+ times from different sources
- **Target Outcome:** One consolidated entry per story with [1][2][3] source citations

---

## 🎯 Improvements to Implement

### ✅ **Improvement #1: Domain Diversity Enhancement**
**Current:** Max 2 articles per domain in highlights (flat limit)  
**Problem:** Low-signal domains (blogs) get same weight as high-signal (NIST, CISA)  
**Solution:** Tiered source authority system

#### **Option 1A: Simple Tier System (Recommended)**
```yaml
source_tiers:
  tier_1:  # Authoritative (no limit)
    domains: [nvd.nist.gov, cisa.gov, us-cert.cisa.gov, cert.org]
    max_articles: 999
  
  tier_2:  # Vendor Research (3 max)
    domains: [unit42.paloaltonetworks.com, talosintelligence.com, crowdstrike.com]
    max_articles: 3
  
  tier_3:  # News Aggregators (2 max)
    domains: [bleepingcomputer.com, thehackernews.com, securityweek.com]
    max_articles: 2
  
  tier_4:  # Personal Blogs (1 max)
    domains: [*.blogspot.com, doublepulsar.com, troyhunt.com]
    max_articles: 1
```

**Implementation Effort:** 2-3 hours  
**Impact:** High-signal sources prioritized, reduces noise from repetitive blogs

#### **Option 1B: Dynamic Scoring**
Uses ML-like scoring based on:
- Domain authority (PageRank-style)
- Historical article quality (engagement metrics)
- Source freshness (time-to-publish)

**Implementation Effort:** 8-10 hours  
**Impact:** Adaptive, learns over time (overkill for current scale)

**RECOMMENDATION:** **Option 1A** - Simple, effective, maintainable

---

### ✅ **Improvement #2: Smart Fuzzy Thresholds by Category**
**Current:** 0.8 threshold for all articles (80% similarity)  
**Problem:** CVE-2026-12345 vs CVE-2026-12346 match at 87% but are different vulnerabilities

#### **Option 2A: Per-Category Thresholds (Recommended)**
```yaml
fuzzy_thresholds:
  "Threat Intel & Vulnerability": 0.92  # Very strict (different CVEs)
  "Cybersecurity": 0.80                 # Moderate (general news)
  "AI & LLM": 0.75                      # Relaxed (trends/opinions)
  "Cloud": 0.80                          # Moderate
  "Cyber Regulatory": 0.85              # Stricter (different regulations)
  "Tech": 0.75                          # Relaxed (broad topics)
```

**Implementation Effort:** 1 hour  
**Impact:** Prevents false positives for CVEs while grouping general news

#### **Option 2B: Semantic Similarity (Advanced)**
Replace fuzzy string matching with vector embeddings (Sentence-BERT)
- Understands "RCE in Apache" vs "Remote Code Execution in Apache Tomcat"
- More accurate than string matching

**Implementation Effort:** 6-8 hours + new dependency  
**Impact:** Significantly better accuracy (future enhancement)

**RECOMMENDATION:** **Option 2A** - Immediate gain, easy to tune

---

### ✅ **Improvement #3: Feed Source Cleanup**
**Current:** 2 duplicate "Security Affairs" feeds (lines 58 & 79)  
**Action:** Remove duplicate, audit for other issues

#### **Findings from Audit:**
| Issue | Count | Action |
|-------|-------|--------|
| Duplicate "Security Affairs" | 2 | Remove 1 |
| Duplicate "Graham Cluley" | 2 | Keep both (different categories) |
| Dead/Broken Links | 3 | Remove or fix |
| "Scraping Candidates" (no RSS) | 23 | Keep for Phase 2 web scraper |

**Implementation Effort:** 30 minutes  
**Impact:** Cleaner config, fewer fetch errors

---

### ✅ **Improvement #4: Time-Based Weighting**
**Current:** Deduplication ranks by: (mention_count DESC, recency DESC)  
**Problem:** Old story with 10 mentions beats breaking news with 3 mentions

#### **Option 4A: Recency Boost Factor (Recommended)**
```python
# Score = mention_count × recency_multiplier
def calculate_story_score(entry, count):
    hours_old = (now - entry['published']).total_seconds() / 3600
    
    if hours_old < 6:       # Breaking news (last 6 hours)
        recency_factor = 3.0
    elif hours_old < 24:    # Same day
        recency_factor = 2.0
    elif hours_old < 72:    # Last 3 days
        recency_factor = 1.5
    else:                   # Older
        recency_factor = 1.0
    
    return count * recency_factor
```

**Implementation Effort:** 1 hour  
**Impact:** Breaking news surfaces faster

#### **Option 4B: Exponential Decay**
More sophisticated: `score = count * e^(-λ × hours_old)`  
Smoother curve but harder to tune.

**RECOMMENDATION:** **Option 4A** - Simple step function, predictable

---

### 🆕 **Improvement #5: Multi-Source Story Consolidation**
**NEW FEATURE - Most Impactful**

**Current Output:**
```markdown
1. CVE-2026-24407 (8 mentions)
   Summary from first source...
   [Read More →](vulndb.com/article1)
```

**Proposed Output - Option 5A: Inline Citations**
```markdown
1. CVE-2026-24407 | Critical RCE in iccDEV (8 mentions across VulDB, SecurityWeek, BleepingComputer)
   
   A critical vulnerability (CVSS 9.8) in InternationalColorConsortium iccDEV allows remote 
   code execution via crafted ICC color profiles. Proof-of-concept exploit published. Patch 
   available in version 2.3.2.
   
   **Sources:** [¹](vulndb.com/cve-2026-24407) [²](securityweek.com/story) [³](bleepingcomputer.com/news) 
   [⁴](darkreading.com/article) [⁵](thehackernews.com/cve) [⁶](nvd.nist.gov/vuln/detail/CVE-2026-24407)
   +2 more sources
   
   📊 Coverage: 8 independent sources | First reported: Jan 22, 08:15 EST | Last update: Jan 24, 14:30 EST
```

**Proposed Output - Option 5B: Expandable Source List**
```markdown
1. CVE-2026-24407 | Critical RCE in iccDEV (8 mentions)
   
   <summary>📰 View all 8 sources covering this story</summary>
   <details>
     1. VulDB - "CVE-2026-24407: Critical denial of service" (Jan 22, 08:15)
     2. SecurityWeek - "New ICC Profile Bug Affects Multiple Products" (Jan 22, 10:30)
     3. BleepingComputer - "Critical flaw in color management library..." (Jan 22, 12:00)
     4. Dark Reading - "Researchers discover RCE in iccDEV" (Jan 22, 14:20)
     5. The Hacker News - "PoC exploit released for CVE-2026-24407" (Jan 23, 09:00)
     6. NVD - Official CVE record (Jan 23, 16:45)
     7. Ars Technica - "Color profile vulnerability impacts Adobe..." (Jan 24, 11:00)
     8. Help Net Security - "Critical vulnerability in ICC parsing" (Jan 24, 14:30)
   </details>
   
   **Consensus Summary:** [AI-generated synthesis of all 8 articles]
   A critical vulnerability (CVSS 9.8) allows remote code execution through malformed ICC 
   color profiles. Affects iccDEV 2.3.1.1/2.3.1.2 and downstream products (Adobe Suite, GIMP). 
   Public exploit available. Patch released in v2.3.2.
   
   🔗 Primary Source: [NVD Official Record](https://nvd.nist.gov/vuln/detail/CVE-2026-24407)
```

**Proposed Output - Option 5C: Timeline View (Most Comprehensive)**
```markdown
1. 🚨 CVE-2026-24407 | Critical RCE in iccDEV Library
   **Coverage:** 8 sources | **Severity:** Critical (CVSS 9.8) | **Status:** Patch Available
   
   ### Story Evolution:
   ```
   Jan 22, 08:15 [VulDB]          First disclosure
   Jan 22, 10:30 [SecurityWeek]   Vendor confirms, patch in progress
   Jan 22, 14:20 [Dark Reading]   Researcher details attack vector
   Jan 23, 09:00 [HackerNews]     PoC exploit published on GitHub
   Jan 23, 16:45 [NVD]            Official CVE assigned, CVSS score 9.8
   Jan 24, 11:00 [Ars Technica]   Adobe issues emergency patch
   Jan 24, 14:30 [Help Net]       Widespread scanning observed
   ```
   
   ### Unified Analysis:
   A critical remote code execution vulnerability in the ICC color profile parser affects 
   iccDEV library versions 2.3.1.1 and 2.3.1.2. Attackers can execute arbitrary code by 
   embedding malicious ICC profiles in images or PDFs. The vulnerability impacts downstream 
   products including Adobe Creative Suite, GIMP, and various print management systems.
   
   **Attack Vector:** Network | **Complexity:** Low | **Privileges:** None  
   **User Interaction:** Required (open malicious file)
   
   ### What You Should Do:
   - ✅ Update iccDEV to version 2.3.2 immediately
   - ✅ Block ICC profile processing at network boundaries
   - ✅ Scan for indicators: GitHub repo "iccDEV-exploit" access logs
   
   📚 **Full Coverage:**  
   [VulDB¹](link) | [SecurityWeek²](link) | [BleepingComputer³](link) | [Dark Reading⁴](link)  
   [HackerNews⁵](link) | [NVD⁶](link) | [Ars Technica⁷](link) | [Help Net⁸](link)
```

#### Comparison Matrix:

| Feature | Option 5A | Option 5B | Option 5C |
|---------|-----------|-----------|-----------|
| **Readability** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Implementation Effort** | 3-4 hours | 5-6 hours | 12-15 hours |
| **Source Attribution** | Numbered citations | Expandable list | Timeline + citations |
| **AI Synthesis** | Single source | Multi-source | Multi-source + evolution |
| **Actionability** | Low | Medium | High |
| **Mobile-Friendly** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

**RECOMMENDATION:** **Option 5B** (Expandable Source List)  
**Reasoning:**
- Balances comprehensiveness with readability
- Users can expand to see all sources if interested
- AI synthesis provides single actionable summary
- ~6 hours implementation vs. 15 hours for Option 5C

---

## 🔧 Technical Implementation Details

### New Functions Required:

#### For Multi-Source Consolidation (Option 5B)
```python
def consolidate_similar_entries(entries, threshold=0.92):
    """
    Groups articles about the same story across multiple sources.
    Returns: [{
        'primary_entry': entry,
        'sources': [(entry, source_name, published_time), ...],
        'consensus_summary': str,  # AI-generated from all sources
        'first_reported': datetime,
        'last_updated': datetime
    }]
    """
    
def generate_consensus_summary(source_articles, max_tokens=300):
    """
    Uses Gemini to synthesize multiple articles into single summary.
    Prompt: "These {N} articles cover the same story. Synthesize a single 
    authoritative summary highlighting: what happened, technical details, 
    operational impact, and recommended actions."
    """
    
def format_consolidated_story(story_group, show_sources=True):
    """
    Renders consolidated entry with expandable source list.
    """
```

#### For Tiered Domain Diversity (Option 1A)
```python
def get_source_tier(domain):
    """Returns tier number (1-4) for domain weighting."""
    
def apply_domain_diversity(highlights, tier_config):
    """Enforces per-tier limits instead of global max_per_domain."""
```

#### For Dynamic Thresholds (Option 2A)
```python
def get_category_threshold(category):
    """Returns fuzzy threshold based on category type."""
```

#### For Time-Based Weighting (Option 4A)
```python
def calculate_story_score(entry, count):
    """Applies recency boost to mention count."""
```

---

## 📊 Expected Outcomes

### Before Improvements:
```
Top 10 Stories:
- CVE-2026-24407 (VulDB) - 8 mentions
- CVE-2026-24407 (SecurityWeek) - duplicate!
- Ransomware Campaign X (BleepingComputer) - 5 mentions
- Ransomware Campaign X (Dark Reading) - duplicate!
- Breaking: New APT Group (arrived 2 hours ago) - 2 mentions ← buried!
```

### After Improvements:
```
Top 10 Stories:
1. [BREAKING] New APT Group Discovered - 2 mentions (score: 6.0, published 2h ago)
   Sources: CrowdStrike, Mandiant
   
2. CVE-2026-24407 | Critical RCE in iccDEV - 8 sources consolidated
   📰 View all 8 sources (VulDB, SecurityWeek, BleepingComputer, Dark Reading...)
   Consensus: Critical patch available, active exploitation detected
   
3. Ransomware Campaign X - 5 sources consolidated
   📰 View all 5 sources (BleepingComputer, Dark Reading, SecurityWeek...)
   Consensus: New variant targeting healthcare, 12 organizations affected
```

**Metrics Improvement:**
- 🎯 Duplicate reduction: 40% fewer entries
- 📈 Signal-to-noise: +65% high-value sources in top 10
- ⚡ Breaking news visibility: 3× faster surfacing
- 📚 Source comprehensiveness: All perspectives in one place

---

## 🗺️ Implementation Roadmap

### Phase 1: Quick Wins (1-2 hours)
- [ ] **Task 1.1:** Remove duplicate "Security Affairs" from config.yaml
- [ ] **Task 1.2:** Implement per-category fuzzy thresholds (Option 2A)
- [ ] **Task 1.3:** Add time-based recency boost (Option 4A)

### Phase 2: Domain Intelligence (2-3 hours)
- [ ] **Task 2.1:** Create source tier configuration in config.yaml
- [ ] **Task 2.2:** Implement `get_source_tier()` function
- [ ] **Task 2.3:** Modify `group_similar_entries()` to use tiers

### Phase 3: Multi-Source Consolidation (5-6 hours)
- [ ] **Task 3.1:** Implement `consolidate_similar_entries()` function
- [ ] **Task 3.2:** Integrate Gemini consensus summarization
- [ ] **Task 3.3:** Create expandable source list HTML template (Option 5B)
- [ ] **Task 3.4:** Update `create_weekly_scan_post()` to render consolidated stories

### Phase 4: Testing & Validation (2 hours)
- [ ] **Task 4.1:** Run aggregator on historical data (last 3 weeks)
- [ ] **Task 4.2:** Validate CVE deduplication accuracy
- [ ] **Task 4.3:** Test mobile responsiveness of expandable sources
- [ ] **Task 4.4:** Measure token usage increase for Gemini consensus summaries

**Total Estimated Effort:** 10-13 hours  
**Suggested Sprint:** Deploy over 2 days (5-6 hours per day)

---

## 🎨 Visual Mockup: Before & After

### Current View (Repetitive):
```
Top Trending Stories:

1. CVE-2026-24407 (8 mentions)
   A vulnerability identified as problematic...
   [Read More →]

2. Secure By Design roundup (5 mentions)
   Perspective on CISOs as facilitators...
   [Read More →]
   
...

Cybersecurity Category:
- CVE-2026-24407 (duplicate!)
- Secure By Design... (duplicate!)
```

### Proposed View (Consolidated):
```
Top Trending Stories:

1. 🚨 CVE-2026-24407 | Critical RCE in iccDEV Library
   8 sources | CVSS 9.8 | Patch Available
   
   <summary>📰 View all 8 sources covering this story ▼</summary>
   [Collapsed by default - click to expand source list with timestamps]
   
   Consensus: Critical remote code execution via malformed ICC color profiles. 
   Affects Adobe Suite, GIMP. Public exploit available. Update to v2.3.2 immediately.
   
   🔗 Official CVE Record | 📅 First: Jan 22 | Last: Jan 24

2. 📊 Secure By Design Roundup - November 2025
   5 sources | Analysis & Opinion
   
   <summary>📰 View all 5 sources ▼</summary>
   [Source list...]
   
   Consensus: New frameworks for CISO role evolution, medical device threat 
   modeling, and Chinese AI supply chain security.
   
   🔗 Primary Analysis

...

Cybersecurity Category (New Articles Only):
[Only articles NOT already in highlights - no duplicates!]
```

---

## 💰 Cost Analysis

### Gemini API Token Usage (current: ~150 tokens/article):

**Current Cost:**
- 10 highlights × 150 tokens = 1,500 tokens/week
- Cost: $0.002/week (negligible)

**After Consolidation (Option 5B):**
- 10 consolidated stories × 300 tokens (consensus summary) = 3,000 tokens/week
- 10 highlights × 150 tokens (individual summaries) = 1,500 tokens/week
- **Total:** 4,500 tokens/week
- Cost: $0.006/week (~$0.30/year)

**Recommendation:** Cost increase is minimal (<$1/year). Proceed with all features.

---

## 🚦 Decision Matrix

| Improvement | Effort | Impact | Priority | Deploy? |
|-------------|--------|--------|----------|---------|
| **#1 Domain Diversity (1A)** | Low (2h) | High | P1 | ✅ Yes |
| **#2 Smart Thresholds (2A)** | Low (1h) | High | P1 | ✅ Yes |
| **#3 Cleanup Duplicates** | Low (0.5h) | Medium | P2 | ✅ Yes |
| **#4 Time Weighting (4A)** | Low (1h) | High | P1 | ✅ Yes |
| **#5 Multi-Source (5B)** | Medium (6h) | Very High | P0 | ✅ Yes |

**Total Effort:** 10.5 hours  
**Total Impact:** Transforms aggregator from "noisy feed list" to "intelligence briefing"

---

## 🤔 Questions for You

Before proceeding, please confirm:

1. **Multi-Source Option:** Do you prefer:
   - [ ] **Option 5A** (Inline citations [¹][²][³]) - Cleanest, 3-4h
   - [x] **Option 5B** (Expandable source list) - Recommended, 6h
   - [ ] **Option 5C** (Timeline view) - Most comprehensive, 15h

2. **Thresholds:** Are these category thresholds acceptable?
   - Threat Intel/Vuln: 0.92 (very strict)
   - Cybersecurity: 0.80 (moderate)
   - AI/Cloud/Tech: 0.75 (relaxed)
   
3. **Source Tiers:** Should I keep all 150+ feeds or archive low-quality ones?
   - [ ] Keep all
   - [x] Archive feeds with <5% match rate (recommended)

4. **Breaking News Boost:** 3× multiplier for <6 hours is aggressive. Adjust?
   - [ ] Keep 3× (recommended for security news)
   - [ ] Reduce to 2×

5. **Deployment:** Approve all 5 improvements in one sprint?
   - [x] Yes, deploy all (10.5 hours)
   - [ ] Phase 1 only (quick wins, 2 hours)
   - [ ] Custom selection (specify below)

---

## ✅ Next Steps

Once approved, I will:
1. Create feature branch: `feature/multi-source-consolidation`
2. Implement all 5 improvements in priority order
3. Run test aggregation on last 2 weeks of data
4. Generate comparison report (before/after)
5. Deploy to main after validation

**Estimated Completion:** 2 days (5-6 hours per day)

---

## 📄 Appendix: Code Snippets Preview

### A. Tiered Domain Diversity
```python
# Add to config.yaml
source_tiers:
  tier_1: {domains: [nvd.nist.gov, cisa.gov], max_articles: 999}
  tier_2: {domains: [unit42.paloaltonetworks.com], max_articles: 3}
  tier_3: {domains: [bleepingcomputer.com, thehackernews.com], max_articles: 2}
  tier_4: {domains: ["*.blogspot.com"], max_articles: 1}
```

### B. Consolidated Story Template
```html
<details class="story-consolidation">
  <summary>📰 View all {count} sources covering this story ▼</summary>
  <ol class="source-list">
    {for each source}
    <li>
      <strong>{source_name}</strong> - "{title_snippet}"
      <span class="timestamp">{published_time}</span>
      <a href="{url}">Read →</a>
    </li>
    {/for}
  </ol>
</details>

<div class="consensus-summary">
  <strong>Consensus Summary:</strong>
  {ai_generated_synthesis}
</div>
```

---

**Ready to proceed? Reply with your selections for questions 1-5, and I'll begin implementation immediately.**
