# MIGRATION PLAN: pub-blog → feedmeup (Dual-Repo Air-Gapped System)

> **Created:** 2026-02-26
> **Last Updated:** 2026-02-26
> **Status:** PENDING EXECUTION
> **Private Engine:** pub-blog (this repo)
> **Public Site:** [paddedzero/feedmeup](https://github.com/paddedzero/feedmeup)

---

## ARCHITECTURE OVERVIEW

```
pub-blog (PRIVATE — The Engine)
  │
  ├─ fetch_news.py runs → outputs to site/content/newsfeed/ (preview)
  │
  ├─ sanitize_for_distribution.py runs
  │  ├─ Copies entire site to temp_dist/ (MINUS exclusions)
  │  ├─ Patches astro.config.mjs base path: /pub-blog → /feedmeup
  │  └─ Generates .github/workflows/deploy.yml for feedmeup
  │
  └─ GitHub Action pushes temp_dist/ → paddedzero/feedmeup
     └─ Full snapshot sync (every push = complete site state)

feedmeup (PUBLIC — The Site)
  │
  ├─ Receives complete Astro site from pub-blog
  ├─ Builds and deploys via its own deploy.yml
  └─ Serves to world via GitHub Pages
```

---

## ⛔ SAFEGUARDS — READ BEFORE EVERY EXECUTION

### NEVER Touch These (Destroy Protection)

| Rule | Detail |
|------|--------|
| ❌ NEVER delete `site/content/newsfeed/` in pub-blog | This is your live preview and source of truth |
| ❌ NEVER delete `site/content/posts/` in pub-blog | Your authored blog posts |
| ❌ NEVER delete `src/` in pub-blog | Your Astro components, layouts, pages, styles |
| ❌ NEVER delete `site/config.ts` | Imported by astro.config.mjs |
| ❌ NEVER force push to feedmeup | Normal push only; preserve git history |
| ❌ NEVER commit `.env` or `scripts/` to feedmeup | Secret sauce stays private |
| ❌ NEVER commit `config.yaml` to feedmeup | Contains RSS feed URLs and API key refs |
| ❌ NEVER modify `astro.config.mjs` in pub-blog | Only patch the COPY in temp_dist/ |
| ❌ NEVER run sanitize script without denylist check | Verify EXCLUDE set before every run |

### Always Verify Before Push

- [ ] `temp_dist/` does NOT contain `scripts/` folder
- [ ] `temp_dist/` does NOT contain `.env` or `.env.production`
- [ ] `temp_dist/` does NOT contain `config.yaml`
- [ ] `temp_dist/` does NOT contain `site/content/_drafts/`
- [ ] `temp_dist/` does NOT contain `__pycache__/`
- [ ] `temp_dist/` does NOT contain `.venv/`
- [ ] `temp_dist/astro.config.mjs` has `base: '/feedmeup'` (NOT `/pub-blog`)
- [ ] `temp_dist/.github/workflows/deploy.yml` exists

---

## PHASE 1: Modify `fetch_news.py` (Dual Output)

### Status: `[x] COMPLETED`

### What Changes
- Add secondary output path: `temp_dist/site/content/newsfeed/`
- After writing posts to `site/content/newsfeed/`, copy them to `temp_dist/site/content/newsfeed/`
- Use `os.makedirs(path, exist_ok=True)` for both targets

### What Does NOT Change
- All existing filtering, deduplication, formatting logic
- All existing posts in `site/content/newsfeed/`
- `POSTS_DIR` constant stays as `Path("site/content/newsfeed")`
- No changes to `config.yaml`

### Implementation Checklist
- [ ] Add `DIST_POSTS_DIR = Path("temp_dist/site/content/newsfeed")` constant
- [ ] Add `DIST_ERRORS_DIR = Path("temp_dist/site/content/errors")` constant
- [ ] After every file write to `POSTS_DIR`, also write to `DIST_POSTS_DIR`
- [ ] After every file write to `ERRORS_DIR`, also write to `DIST_ERRORS_DIR`
- [ ] Test: Run `fetch_news.py` → verify both paths have identical output
- [ ] Verify: Original `site/content/newsfeed/` is untouched

### Safeguard
```python
# SAFEGUARD: Never delete existing preview posts
# Only WRITE new files, never rm -rf the directory
assert POSTS_DIR.exists(), "POSTS_DIR missing — aborting to prevent data loss"
```

---

## PHASE 2: Create `sanitize_for_distribution.py` (NEW SCRIPT)

### Status: `[x] COMPLETED`

### Location
`scripts/sanitize_for_distribution.py`

### Strategy: DENYLIST (copy everything EXCEPT exclusions)

This is safer than an allowlist because new files added to pub-blog will automatically flow to feedmeup without plan updates.

### Exclusion Set (DENY these from temp_dist/)

```python
EXCLUDE_DIRS = {
    'scripts',           # fetch_news.py, config.yaml, scraper.py — SECRET SAUCE
    '.git',              # Git internals
    '.github',           # Will be regenerated with feedmeup-specific deploy.yml
    'node_modules',      # Reinstalled via npm ci
    'dist',              # Build output — rebuilt in feedmeup
    '.astro',            # Astro cache — rebuilt
    '.venv',             # Python virtualenv
    '__pycache__',       # Python bytecode
    'temp_dist',         # Prevent recursive copy
    '.feed_cache',       # Feed caching data (private)
    '.article_registry', # Cross-run dedup registry (private)
    '.playwright-mcp',   # Dev tooling
    'site/content/_drafts',  # DRAFT POSTS — folder-based detection
}

EXCLUDE_FILES = {
    '.env',                         # Environment secrets
    '.env.production',              # Production secrets
    'requirements.txt',             # Python deps (not needed in feedmeup)
    'apply_css.py',                 # Dev script
    'densify_ui.py',                # Dev script
    'test_negative_keywords.py',    # Test file
    'test_regex.py',                # Test file
    'test_tagging_dashboard.py',    # Test file
    'validate_filtering.py',        # Validation script
    'run2.log',                     # Log file
    'run3.log',                     # Log file
    'FEED_IMPROVEMENTS_PROPOSAL.md',   # Dev planning doc
    'IMPLEMENTATION_SUMMARY_GROUP2_4.md', # Dev planning doc
    'IMPROVEMENT_PLAN.md',          # Dev planning doc
    'NEXT_STEPS.md',                # Dev planning doc
    'VALIDATION_COMPLETE.md',       # Dev planning doc
    'MIGRATION_PLAN.md',            # THIS FILE — do not push to public
}
```

### What Gets Copied (Result of Denylist)

```
temp_dist/
├── astro.config.mjs        ← PATCHED: base: '/feedmeup'
├── package.json
├── package-lock.json        ← For reproducible npm ci
├── svelte.config.js
├── tsconfig.json
├── LICENSE
├── README.md
├── public/
│   ├── favicon.svg
│   └── images/
├── site/
│   ├── config.ts
│   ├── hero.md
│   ├── cta.md
│   ├── assets/
│   │   ├── site.webmanifest
│   │   └── images/
│   └── content/
│       ├── about/
│       ├── appearances/
│       ├── errors/
│       ├── newsfeed/          ← All published news posts
│       ├── posts/             ← All published blog posts
│       ├── projects/
│       └── _components/       ← Astro inline components (NOT a draft folder)
├── src/
│   ├── content.config.ts
│   ├── env.d.ts
│   ├── components/
│   ├── layouts/
│   ├── lib/
│   ├── pages/
│   └── styles/
└── .github/
    └── workflows/
        └── deploy.yml         ← GENERATED: feedmeup-specific deploy Action
```

### Patching Logic

#### astro.config.mjs patch
```python
# PATCH: Change base path from pub-blog to feedmeup
content = content.replace("base: '/pub-blog'", "base: '/feedmeup'")
```

#### deploy.yml generation
- Copy from `pub-blog/.github/workflows/deploy.yml`
- No path changes needed (it uses relative paths)

### Implementation Checklist
- [ ] Create `scripts/sanitize_for_distribution.py`
- [ ] Implement denylist exclusion logic
- [ ] Implement `astro.config.mjs` base path patching
- [ ] Implement `.github/workflows/deploy.yml` copy for feedmeup
- [ ] Add validation assertions (see Safeguards below)
- [ ] Test: Run script → verify temp_dist/ structure
- [ ] Test: Verify NO excluded files in temp_dist/
- [ ] Test: Verify `astro.config.mjs` has correct base path

### Safeguards (Built Into Script)

```python
# POST-COPY VALIDATION — script must pass ALL checks or abort

def validate_temp_dist():
    """Validate temp_dist/ is safe to push to public repo."""
    errors = []

    # 1. No scripts/ folder
    if Path("temp_dist/scripts").exists():
        errors.append("FATAL: temp_dist/scripts/ exists — SECRET SAUCE LEAK")

    # 2. No .env files
    for env_file in Path("temp_dist").rglob(".env*"):
        errors.append(f"FATAL: {env_file} found — SECRET LEAK")

    # 3. No config.yaml
    if Path("temp_dist/scripts/config.yaml").exists():
        errors.append("FATAL: config.yaml found — RSS FEEDS EXPOSED")

    # 4. No _drafts folder
    if Path("temp_dist/site/content/_drafts").exists():
        errors.append("FATAL: _drafts/ found — DRAFT POSTS EXPOSED")

    # 5. No Python files in root
    for py_file in Path("temp_dist").glob("*.py"):
        errors.append(f"FATAL: {py_file} found — DEV SCRIPT EXPOSED")

    # 6. No __pycache__
    for cache in Path("temp_dist").rglob("__pycache__"):
        errors.append(f"FATAL: {cache} found — PYTHON CACHE EXPOSED")

    # 7. No .venv
    if Path("temp_dist/.venv").exists():
        errors.append("FATAL: .venv/ found — VIRTUALENV EXPOSED")

    # 8. astro.config.mjs has correct base
    astro_config = Path("temp_dist/astro.config.mjs")
    if astro_config.exists():
        content = astro_config.read_text()
        if "/pub-blog" in content:
            errors.append("FATAL: astro.config.mjs still references /pub-blog")
        if "/feedmeup" not in content:
            errors.append("FATAL: astro.config.mjs missing /feedmeup base path")

    # 9. deploy.yml exists
    if not Path("temp_dist/.github/workflows/deploy.yml").exists():
        errors.append("FATAL: deploy.yml missing — feedmeup cannot build")

    # 10. No .feed_cache or .article_registry
    if Path("temp_dist/.feed_cache").exists():
        errors.append("FATAL: .feed_cache/ found — CACHE DATA EXPOSED")
    if Path("temp_dist/.article_registry").exists():
        errors.append("FATAL: .article_registry/ found — REGISTRY EXPOSED")

    if errors:
        print("=" * 60)
        print("⛔ SANITIZATION FAILED — ABORTING PUSH")
        print("=" * 60)
        for e in errors:
            print(f"  {e}")
        print("=" * 60)
        sys.exit(1)
    else:
        print("✅ All sanitization checks passed. Safe to push.")
```

---

## PHASE 3: Create GitHub Action — `news-distribution.yml`

### Status: `[x] COMPLETED`

### Location
`pub-blog/.github/workflows/news-distribution.yml`

### Trigger
- **Scheduled:** Monday 08:00 UTC (`cron: '0 8 * * 1'`)
- **Manual:** `workflow_dispatch` (trigger anytime from Actions tab)

### Action Steps

```yaml
name: Distribute to feedmeup

on:
  schedule:
    - cron: '0 8 * * 1'  # Monday 08:00 UTC
  workflow_dispatch:       # Manual trigger

permissions:
  contents: write

jobs:
  distribute:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout pub-blog
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run news aggregation
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: python scripts/fetch_news.py

      - name: Sanitize for public distribution
        run: python scripts/sanitize_for_distribution.py

      - name: Push to feedmeup
        uses: cpina/github-action-push-to-another-repository@v1.7.2
        env:
          API_TOKEN_GITHUB: ${{ secrets.FEEDMEUP_PAT }}
        with:
          source-directory: 'temp_dist'
          destination-github-username: 'paddedzero'
          destination-repository-name: 'feedmeup'
          user-email: 'action@github.com'
          user-name: 'GitHub Action'
          target-branch: 'main'

      - name: Cleanup temp_dist
        if: always()
        run: rm -rf temp_dist/
```

### Implementation Checklist
- [ ] Create `.github/workflows/news-distribution.yml`
- [ ] Verify: Uses `cpina/github-action-push-to-another-repository@v1.7.2`
- [ ] Verify: Source directory is `temp_dist` (not `temp_dist/`)
- [ ] Verify: Destination is `paddedzero/feedmeup`
- [ ] Verify: Uses `${{ secrets.FEEDMEUP_PAT }}` (not GITHUB_TOKEN)
- [ ] Verify: Cleanup step runs even if push fails (`if: always()`)

### Safeguard
```yaml
# SAFEGUARD: Sanitize script includes validation
# If validation fails, script exits with code 1
# This prevents the push step from executing
```

---

## PHASE 4: Update `.gitignore` (pub-blog)

### Status: `[x] COMPLETED`

### Changes

```gitignore
# Distribution staging (ephemeral, created per-run)
/temp_dist/

# Draft posts (private, not distributed)
site/content/_drafts/
```

### What NOT to Change
- All existing `.gitignore` rules stay as-is
- `.env` is already excluded
- `node_modules/` is already excluded
- `dist/` is already excluded

### ⚠️ Note: `feeds.json` removal
The original plan referenced `feeds.json` — this file does **not exist** in pub-blog. Your feed sources are in `scripts/config.yaml`, which is protected by the `scripts/` folder exclusion in the sanitize script. No `.gitignore` change needed for it.

### Implementation Checklist
- [ ] Add `/temp_dist/` to `.gitignore`
- [ ] Add `site/content/_drafts/` to `.gitignore`
- [ ] Verify: No existing rules removed

---

## PHASE 5: Create `site/content/_drafts/` Folder

### Status: `[x] COMPLETED`

### Purpose
Any markdown file placed in this folder is:
- ✅ Visible in pub-blog (for local preview)
- ❌ Excluded from feedmeup (sanitize script skips it)

### Workflow
```
Draft lifecycle:
  1. Create post: site/content/_drafts/my-secret-idea.md
  2. Preview locally: npm run dev (visible on pub-blog)
  3. Ready to publish: MOVE to site/content/posts/my-secret-idea.md
  4. Next sync: sanitize picks it up, pushes to feedmeup
```

### Implementation Checklist
- [ ] Create `site/content/_drafts/` directory
- [ ] Add a `.gitkeep` file (so Git tracks the empty folder)
- [ ] Test: Place a test draft, run sanitize, verify NOT in temp_dist/

---

## PHASE 6: Sync Behavior — Full Snapshot (NOT Append-Only)

### How `cpina/github-action-push-to-another-repository` Works

**Each push to feedmeup is a complete snapshot of `temp_dist/`.** This means:

| Scenario | Result |
|----------|--------|
| New post added to pub-blog | ✅ Appears in feedmeup on next sync |
| Post edited in pub-blog | ✅ Updated in feedmeup on next sync |
| Post deleted from pub-blog | ⚠️ Also removed from feedmeup on next sync |
| Post moved to `_drafts/` | ✅ Removed from feedmeup (draft hidden) |
| New component added in `src/` | ✅ Appears in feedmeup on next sync |
| Theme change in pub-blog | ✅ Reflected in feedmeup on next sync |

### Important Implication
**If you delete a post from `site/content/posts/` in pub-blog, it will disappear from feedmeup on the next sync.** This is by design — pub-blog is the single source of truth.

---

## PHASE 7: PAT Configuration (GitHub UI — Manual)

### Status: `[ ] NOT STARTED`

### Step 1: Generate Personal Access Token
- [ ] Go to: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
- [ ] Click: "Generate new token (classic)"
- [ ] Name: `feedmeup-distribution-pat`
- [ ] Expiration: 90 days (set calendar reminder to rotate)
- [ ] Scopes: ✅ `repo` (full control of private repositories)
- [ ] ❌ DO NOT select: `admin:org`, `delete_repo`, `admin:org_hook`, `admin:repo_hook`
- [ ] Click: "Generate token"
- [ ] Copy token (shown only once)

### Step 2: Add to pub-blog Secrets
- [ ] Go to: pub-blog → Settings → Secrets and variables → Actions
- [ ] Click: "New repository secret"
- [ ] Name: `FEEDMEUP_PAT`
- [ ] Value: [paste token from Step 1]
- [ ] Click: "Add secret"
- [ ] Verify: Secret appears in list (value hidden)

### Step 3: Verify Action Configuration
- [ ] Open: `.github/workflows/news-distribution.yml`
- [ ] Confirm line: `destination-repository-name: 'feedmeup'`
- [ ] Confirm line: `destination-github-username: 'paddedzero'`
- [ ] Confirm line: `API_TOKEN_GITHUB: ${{ secrets.FEEDMEUP_PAT }}`

### Step 4: Dry-Run Manual Test
- [ ] Go to: pub-blog → Actions → "Distribute to feedmeup"
- [ ] Click: "Run workflow" → "Run workflow" (manual dispatch)
- [ ] Monitor: Watch logs for each step
- [ ] Verify: "Sanitize for public distribution" step shows "✅ All sanitization checks passed"
- [ ] Verify: "Push to feedmeup" step completes without errors
- [ ] Check: paddedzero/feedmeup now has site/, src/, astro.config.mjs
- [ ] Check: paddedzero/feedmeup does NOT have scripts/, .env, _drafts/
- [ ] Verify: feedmeup's `astro.config.mjs` has `base: '/feedmeup'`

### Step 5: Enable Scheduled Execution
- [ ] Confirm: Cron schedule is active in `news-distribution.yml`
- [ ] Monitor: Actions tab shows workflow listed
- [ ] Note: GitHub only runs scheduled Actions on the DEFAULT branch (main)
- [ ] Set calendar reminder: Rotate PAT before expiration (90 days)

---

## PHASE 8: feedmeup Post-Sync Setup (One-Time)

### Status: `[ ] NOT STARTED`

After the first successful sync, feedmeup needs:

### GitHub Pages Configuration
- [ ] Go to: feedmeup → Settings → Pages
- [ ] Source: "GitHub Actions" (not "Deploy from a branch")
- [ ] Verify: deploy.yml was pushed by sync Action
- [ ] Trigger: feedmeup's deploy.yml should auto-run on push to main
- [ ] Check: Site builds at `https://paddedzero.github.io/feedmeup/`

### Verify Site Renders
- [ ] Visit: `https://paddedzero.github.io/feedmeup/`
- [ ] Check: Newsfeed page loads with posts
- [ ] Check: Blog posts page loads
- [ ] Check: About page loads
- [ ] Check: All links use `/feedmeup/` base path (not `/pub-blog/`)
- [ ] Check: CSS/styles render correctly
- [ ] Check: Images load from correct paths

---

## PHASE 9: Make pub-blog Private (FINAL STEP)

### Status: `[ ] NOT STARTED`

> ⚠️ DO THIS ONLY AFTER feedmeup is fully verified and working.

- [ ] Verify: feedmeup site is live and accessible at `https://paddedzero.github.io/feedmeup/`
- [ ] Verify: All content renders correctly on feedmeup
- [ ] Verify: Scheduled Action has run at least once successfully
- [ ] Go to: pub-blog → Settings → General → Danger Zone
- [ ] Click: "Change repository visibility"
- [ ] Select: "Make private"
- [ ] Confirm: Type repository name to confirm
- [ ] After: Verify feedmeup still works (it's independent — should be fine)
- [ ] After: Verify scheduled Actions still run (private repos have Action minutes limits on free plan)

### ⚠️ GitHub Actions Minutes Warning
Private repos on the **free plan** get **2,000 minutes/month**. Your weekly Action should use ~5-10 min per run × 4 runs = ~40 min/month. Well within limits.

---

## PHASE 10: QA & Security Review (Handoffs)

### QA Requirements Auditor Checklist
- [ ] fetch_news.py outputs to BOTH `site/content/newsfeed/` and `temp_dist/site/content/newsfeed/`
- [ ] Preview visible on pub-blog (local dev server)
- [ ] sanitize_for_distribution.py excludes `_drafts/` correctly
- [ ] sanitize_for_distribution.py excludes `scripts/` correctly
- [ ] temp_dist/ contains complete buildable Astro project
- [ ] feedmeup receives all posts without duplication
- [ ] feedmeup site builds successfully with `npm ci && npm run build`
- [ ] feedmeup base path is `/feedmeup/` (not `/pub-blog/`)
- [ ] Manual workflow trigger works
- [ ] Scheduled workflow trigger fires on Monday 08:00 UTC

### AppSec Sentinel Checklist
- [ ] PAT scope: `repo` ONLY (no admin, no delete_repo)
- [ ] PAT stored as GitHub secret (not hardcoded in YAML)
- [ ] `${{ secrets.FEEDMEUP_PAT }}` not logged in Action output
- [ ] `.env` never appears in temp_dist/ or feedmeup
- [ ] `config.yaml` never appears in temp_dist/ or feedmeup
- [ ] `scripts/` folder never appears in temp_dist/ or feedmeup
- [ ] `_drafts/` folder never appears in temp_dist/ or feedmeup
- [ ] `.feed_cache/` and `.article_registry/` never appear in temp_dist/
- [ ] No Python `*.py` files in temp_dist/ root
- [ ] pub-blog set to PRIVATE (after feedmeup is verified)
- [ ] feedmeup is PUBLIC (no secrets in any committed files)
- [ ] Git history in feedmeup contains no secrets (clean from first push)
- [ ] Sanitization validation runs BEFORE push step (fail-fast)
- [ ] No `--force` flag used in git push to feedmeup

---

## EXECUTION ORDER (Do Not Skip Steps)

```
1. ☑ Phase 5: Create site/content/_drafts/ folder
2. ☑ Phase 4: Update .gitignore
3. ☑ Phase 1: Modify fetch_news.py (dual output)
4. ☑ Phase 2: Create sanitize_for_distribution.py
5. ☑ Phase 3: Create news-distribution.yml
6. ☐ Phase 7 Steps 1-2: Generate PAT + add to secrets (MANUAL — GitHub UI)
7. ☐ Phase 7 Steps 3-4: Verify config + dry-run (MANUAL — GitHub UI)
8. ☐ Phase 8: Configure feedmeup GitHub Pages (MANUAL — GitHub UI)
9. ☐ Phase 10: QA Requirements Auditor review
10. ☐ Phase 10: AppSec Sentinel review
11. ☐ Phase 7 Step 5: Enable scheduled execution
12. ☐ Phase 9: Make pub-blog private (ONLY after all above pass)
```

---

## ROLLBACK PLAN

If something goes wrong after making pub-blog private:

1. **feedmeup broken?** → Make pub-blog public again (Settings → Change visibility → Public)
2. **Bad push to feedmeup?** → `git revert HEAD` in feedmeup to undo last commit
3. **PAT expired?** → Generate new token, update `FEEDMEUP_PAT` secret in pub-blog
4. **Secrets leaked?** → Immediately rotate PAT, revoke old token, check feedmeup git history
5. **Posts missing?** → They're still in pub-blog's `site/content/` — re-run sync Action

---

## MAINTENANCE SCHEDULE

| Task | Frequency | Action |
|------|-----------|--------|
| PAT Rotation | Every 90 days | Generate new token, update secret |
| Sync Verification | Weekly (after Monday run) | Check feedmeup received new posts |
| Draft Review | As needed | Move from `_drafts/` to `posts/` when ready |
| Exclusion List Review | Monthly | Verify no new sensitive files need adding |
| Action Minutes Check | Monthly | Verify pub-blog hasn't exceeded 2,000 min/month |
