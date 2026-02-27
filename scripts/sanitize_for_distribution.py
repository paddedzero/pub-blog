#!/usr/bin/env python3
"""
sanitize_for_distribution.py — Deep Sanitization for pub-blog → feedmeup Distribution

This script creates a clean copy of the pub-blog Astro site in temp_dist/,
excluding all private/sensitive files (scripts, secrets, drafts, dev files).

Strategy: DENYLIST (copy everything EXCEPT exclusions)
Target: paddedzero/feedmeup (public GitHub Pages site)

Usage:
    python scripts/sanitize_for_distribution.py

Output:
    temp_dist/ — Clean, buildable Astro project ready for push to feedmeup

Safety:
    - Validates output before completing (10-point check)
    - Aborts with exit code 1 if ANY check fails
    - Never modifies source files in pub-blog
"""

import os
import sys
import shutil
import logging
import fnmatch
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# ============================================================================
# CONFIGURATION — Denylist of files/folders to EXCLUDE from distribution
# ============================================================================

# Directories to completely exclude (relative to project root)
EXCLUDE_DIRS = {
    "scripts",              # fetch_news.py, config.yaml, scraper.py — SECRET SAUCE
    ".git",                 # Git internals
    ".github",              # Will be regenerated with feedmeup-specific deploy Action
    "node_modules",         # Reinstalled via npm ci in feedmeup
    "dist",                 # Build output — rebuilt in feedmeup
    ".astro",               # Astro cache — rebuilt
    ".venv",                # Python virtualenv
    "__pycache__",          # Python bytecode
    "temp_dist",            # Prevent recursive copy
    ".feed_cache",          # Feed caching data (private)
    ".article_registry",    # Cross-run dedup registry (private)
    ".playwright-mcp",      # Dev tooling
    ".semantic_cache",      # Semantic dedup cache (private)
}

# Specific subdirectory paths to exclude (relative to project root)
EXCLUDE_SUBPATHS = {
    os.path.join("site", "content", "_drafts"),  # Draft posts — folder-based detection
}

# File patterns to exclude (matched against filename only)
EXCLUDE_FILE_PATTERNS = [
    ".env",                 # Environment secrets
    ".env.production",      # Production secrets
    ".envrc",               # direnv secrets
    "requirements.txt",     # Python deps (not needed in feedmeup)
    "*.py",                 # All Python scripts in project root
    "*.log",                # Log files
    "*.pyc",                # Python bytecode
    "*.pyo",                # Python optimized bytecode
    ".gitignore",           # Will be generated fresh for feedmeup
]

# Specific filenames to exclude (exact match, relative to project root)
EXCLUDE_FILES = {
    "apply_css.py",
    "densify_ui.py",
    "test_negative_keywords.py",
    "test_regex.py",
    "test_tagging_dashboard.py",
    "validate_filtering.py",
    "FEED_IMPROVEMENTS_PROPOSAL.md",
    "IMPLEMENTATION_SUMMARY_GROUP2_4.md",
    "IMPROVEMENT_PLAN.md",
    "NEXT_STEPS.md",
    "VALIDATION_COMPLETE.md",
    "MIGRATION_PLAN.md",
    "run2.log",
    "run3.log",
}

# Source and destination
PROJECT_ROOT = Path(".")
TEMP_DIST = Path("temp_dist")

# ============================================================================
# CORE LOGIC
# ============================================================================


def should_exclude_dir(dir_name, dir_path_rel):
    """Check if a directory should be excluded from distribution."""
    # Check directory name against exclusion set
    if dir_name in EXCLUDE_DIRS:
        return True
    # Check if directory name starts with . (hidden dirs) except specific ones we want
    if dir_name.startswith(".") and dir_name not in {".github"}:
        return True
    # Check full relative path against subpath exclusions
    dir_path_normalized = dir_path_rel.replace("\\", "/")
    for excluded_subpath in EXCLUDE_SUBPATHS:
        excluded_normalized = excluded_subpath.replace("\\", "/")
        if dir_path_normalized == excluded_normalized or dir_path_normalized.startswith(excluded_normalized + "/"):
            return True
    return False


def should_exclude_file(filename, file_path_rel):
    """Check if a file should be excluded from distribution."""
    # Check exact filename match
    if filename in EXCLUDE_FILES:
        return True
    # Check file patterns
    for pattern in EXCLUDE_FILE_PATTERNS:
        if fnmatch.fnmatch(filename, pattern):
            # But allow .py files inside src/ (e.g., none currently, but future-proof)
            if pattern == "*.py" and file_path_rel.replace("\\", "/").startswith("src/"):
                continue
            return True
    return False


def clean_temp_dist():
    """Remove temp_dist/ if it exists, then create fresh."""
    if TEMP_DIST.exists():
        logging.info("[CLEAN] Removing existing temp_dist/...")
        shutil.rmtree(TEMP_DIST)
    TEMP_DIST.mkdir(parents=True, exist_ok=True)
    logging.info("[CLEAN] Created fresh temp_dist/")


def copy_project_to_temp_dist():
    """Copy project files to temp_dist/ using denylist exclusion."""
    copied_files = 0
    excluded_files = 0
    excluded_dirs_log = []

    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Get relative path from project root
        rel_root = os.path.relpath(root, PROJECT_ROOT)
        if rel_root == ".":
            rel_root = ""

        # Filter directories in-place (prevents os.walk from descending)
        original_dirs = dirs[:]
        dirs[:] = []
        for d in original_dirs:
            dir_rel = os.path.join(rel_root, d) if rel_root else d
            if should_exclude_dir(d, dir_rel):
                excluded_dirs_log.append(dir_rel)
                logging.debug("[EXCLUDE DIR] %s", dir_rel)
            else:
                dirs.append(d)

        # Copy files
        for filename in files:
            file_rel = os.path.join(rel_root, filename) if rel_root else filename
            if should_exclude_file(filename, file_rel):
                excluded_files += 1
                logging.debug("[EXCLUDE FILE] %s", file_rel)
                continue

            src = Path(root) / filename
            dst = TEMP_DIST / file_rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied_files += 1

    logging.info("[COPY] Copied %d files to temp_dist/", copied_files)
    logging.info("[COPY] Excluded %d files and %d directories", excluded_files, len(excluded_dirs_log))

    if excluded_dirs_log:
        logging.info("[EXCLUDED DIRS] %s", ", ".join(sorted(excluded_dirs_log)))

    return copied_files


def patch_astro_config():
    """Patch astro.config.mjs to use feedmeup base path instead of pub-blog."""
    astro_config = TEMP_DIST / "astro.config.mjs"
    if not astro_config.exists():
        logging.error("[PATCH] astro.config.mjs not found in temp_dist/!")
        return False

    content = astro_config.read_text(encoding="utf-8")
    original = content

    # Patch base path: '/pub-blog' → '/feedmeup'
    content = content.replace("base: '/pub-blog'", "base: '/feedmeup'")

    if content == original:
        logging.warning("[PATCH] No base path change made — may already be patched or pattern not found")
    else:
        astro_config.write_text(content, encoding="utf-8")
        logging.info("[PATCH] astro.config.mjs: base: '/pub-blog' → base: '/feedmeup'")

    return True


def generate_feedmeup_deploy_action():
    """Generate a deploy.yml for feedmeup GitHub Pages deployment."""
    deploy_yml_dir = TEMP_DIST / ".github" / "workflows"
    deploy_yml_dir.mkdir(parents=True, exist_ok=True)

    deploy_content = """name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node 22
        uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build site
        id: build
        run: |
          set +e
          npm run build -- --verbose 2>&1 | tee build_output.txt
          BUILD_EXIT=$?
          if [ $BUILD_EXIT -ne 0 ]; then
            echo "## Build Failed" >> $GITHUB_STEP_SUMMARY
            echo '```' >> $GITHUB_STEP_SUMMARY
            tail -100 build_output.txt >> $GITHUB_STEP_SUMMARY
            echo '```' >> $GITHUB_STEP_SUMMARY
            exit $BUILD_EXIT
          fi

      - name: Setup Pages
        uses: actions/configure-pages@v5

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: ./dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""

    deploy_yml_path = deploy_yml_dir / "deploy.yml"
    deploy_yml_path.write_text(deploy_content, encoding="utf-8")
    logging.info("[GENERATE] Created .github/workflows/deploy.yml for feedmeup")


def generate_feedmeup_gitignore():
    """Generate a .gitignore for feedmeup (standard Node/Astro project)."""
    gitignore_content = """# Dependencies
node_modules/

# Build output
dist/
.astro/

# Environment
.env
.env.production

# OS files
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
*.log
npm-debug.log*
"""

    gitignore_path = TEMP_DIST / ".gitignore"
    gitignore_path.write_text(gitignore_content, encoding="utf-8")
    logging.info("[GENERATE] Created .gitignore for feedmeup")


# ============================================================================
# VALIDATION — 10-Point Safety Check
# ============================================================================


def validate_temp_dist():
    """Validate temp_dist/ is safe to push to public feedmeup repo.
    
    Returns True if all checks pass, exits with code 1 if any fail.
    This is the LAST LINE OF DEFENSE before pushing to a public repo.
    """
    errors = []
    warnings = []

    logging.info("=" * 60)
    logging.info("⛔ RUNNING SANITIZATION VALIDATION (10-POINT CHECK)")
    logging.info("=" * 60)

    # 1. No scripts/ folder
    if (TEMP_DIST / "scripts").exists():
        errors.append("FATAL: temp_dist/scripts/ exists — SECRET SAUCE LEAK")
    else:
        logging.info("  ✅ [1/10] No scripts/ folder")

    # 2. No .env files anywhere
    env_files = list(TEMP_DIST.rglob(".env")) + list(TEMP_DIST.rglob(".env.*"))
    # Filter out .env files inside .github/workflows (template expressions are fine)
    env_files = [f for f in env_files if ".github" not in str(f)]
    if env_files:
        for ef in env_files:
            errors.append(f"FATAL: {ef} found — SECRET LEAK")
    else:
        logging.info("  ✅ [2/10] No .env files")

    # 3. No config.yaml (RSS feed sources)
    config_files = list(TEMP_DIST.rglob("config.yaml"))
    # Exclude site/config.ts (that's the Astro site config, it's fine)
    config_yamls = [f for f in config_files if f.name == "config.yaml"]
    if config_yamls:
        for cf in config_yamls:
            errors.append(f"FATAL: {cf} found — RSS FEEDS EXPOSED")
    else:
        logging.info("  ✅ [3/10] No config.yaml files")

    # 4. No _drafts folder
    drafts = list(TEMP_DIST.rglob("_drafts"))
    if drafts:
        for d in drafts:
            errors.append(f"FATAL: {d} found — DRAFT POSTS EXPOSED")
    else:
        logging.info("  ✅ [4/10] No _drafts/ folder")

    # 5. No Python files in root
    root_py_files = list(TEMP_DIST.glob("*.py"))
    if root_py_files:
        for pf in root_py_files:
            errors.append(f"FATAL: {pf} found — DEV SCRIPT EXPOSED")
    else:
        logging.info("  ✅ [5/10] No Python files in root")

    # 6. No __pycache__
    pycache_dirs = list(TEMP_DIST.rglob("__pycache__"))
    if pycache_dirs:
        for pc in pycache_dirs:
            errors.append(f"FATAL: {pc} found — PYTHON CACHE EXPOSED")
    else:
        logging.info("  ✅ [6/10] No __pycache__/ directories")

    # 7. No .venv
    if (TEMP_DIST / ".venv").exists():
        errors.append("FATAL: .venv/ found — VIRTUALENV EXPOSED")
    else:
        logging.info("  ✅ [7/10] No .venv/ directory")

    # 8. astro.config.mjs has correct base path
    astro_config = TEMP_DIST / "astro.config.mjs"
    if astro_config.exists():
        content = astro_config.read_text(encoding="utf-8")
        if "/pub-blog" in content:
            errors.append("FATAL: astro.config.mjs still references /pub-blog")
        elif "/feedmeup" not in content:
            errors.append("FATAL: astro.config.mjs missing /feedmeup base path")
        else:
            logging.info("  ✅ [8/10] astro.config.mjs has correct base: '/feedmeup'")
    else:
        errors.append("FATAL: astro.config.mjs not found in temp_dist/")

    # 9. deploy.yml exists
    if (TEMP_DIST / ".github" / "workflows" / "deploy.yml").exists():
        logging.info("  ✅ [9/10] .github/workflows/deploy.yml exists")
    else:
        errors.append("FATAL: .github/workflows/deploy.yml missing — feedmeup cannot build")

    # 10. No .feed_cache or .article_registry
    cache_leak = False
    if (TEMP_DIST / ".feed_cache").exists():
        errors.append("FATAL: .feed_cache/ found — CACHE DATA EXPOSED")
        cache_leak = True
    if (TEMP_DIST / ".article_registry").exists():
        errors.append("FATAL: .article_registry/ found — REGISTRY EXPOSED")
        cache_leak = True
    if not cache_leak:
        logging.info("  ✅ [10/10] No .feed_cache/ or .article_registry/")

    # Results
    logging.info("=" * 60)
    if errors:
        logging.error("⛔ SANITIZATION FAILED — ABORTING DISTRIBUTION")
        logging.error("=" * 60)
        for e in errors:
            logging.error("  %s", e)
        logging.error("=" * 60)
        logging.error("Fix the issues above and re-run. NO files were pushed.")
        sys.exit(1)
    else:
        logging.info("✅ ALL 10 SANITIZATION CHECKS PASSED")
        logging.info("✅ temp_dist/ is safe to push to paddedzero/feedmeup")
        logging.info("=" * 60)
        return True


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def main():
    logging.info("=" * 60)
    logging.info("🔧 SANITIZE FOR DISTRIBUTION — pub-blog → feedmeup")
    logging.info("=" * 60)

    # Step 1: Clean temp_dist/
    clean_temp_dist()

    # Step 2: Copy project (minus exclusions)
    copied = copy_project_to_temp_dist()
    if copied == 0:
        logging.error("No files copied — something is wrong. Aborting.")
        sys.exit(1)

    # Step 3: Patch astro.config.mjs base path
    patch_astro_config()

    # Step 4: Generate feedmeup-specific files
    generate_feedmeup_deploy_action()
    generate_feedmeup_gitignore()

    # Step 5: Validate (MUST PASS or script aborts with exit code 1)
    validate_temp_dist()

    logging.info("")
    logging.info("🎉 Distribution package ready at temp_dist/")
    logging.info("   Next: GitHub Action will push temp_dist/ → paddedzero/feedmeup")


if __name__ == "__main__":
    main()
