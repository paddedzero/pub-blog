# GitHub Actions Workflows

This directory contains automated workflows for the pub-blog project.

## Workflows

### 1. Deploy to GitHub Pages (`deploy.yml`)
**Trigger:** Push to main branch or manual dispatch  
**Purpose:** Builds and deploys the Astro site to GitHub Pages

**Steps:**
1. Checkout repository
2. Install Node.js dependencies
3. Build Astro site
4. Deploy to GitHub Pages

### 2. Fetch and Publish News (`news-aggregation.yml`)
**Trigger:** 
- Scheduled: Every Monday at 8 AM UTC
- Manual: Via workflow_dispatch

**Purpose:** Automated news aggregation from 40+ RSS feeds

**Steps:**
1. Checkout repository
2. Set up Python 3.11 with pip caching
3. Install Python dependencies (feedparser, requests, google-genai, etc.)
4. Run `fetch_news.py` script with Gemini API key
5. Commit generated posts to `src/content/posts/`
6. Push changes (triggers deployment workflow automatically)

**Environment Variables Required:**
- `GEMINI_API_KEY`: Set as repository secret for AI summarization

## Setting Up Secrets

To enable news aggregation with AI features:

1. Go to repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `GEMINI_API_KEY`
4. Value: Your Google Gemini API key
5. Click "Add secret"

## Manual Workflow Triggers

You can manually trigger workflows from the Actions tab:

1. Go to Actions tab
2. Select the workflow (e.g., "Fetch and Publish News")
3. Click "Run workflow"
4. Select branch (usually `main`)
5. Click "Run workflow" button

## Workflow Interaction

The workflows are designed to work together:

```
News Aggregation → Generates posts → Commits to main → Triggers Deployment → Updates live site
```

This ensures that whenever new posts are created, the site is automatically rebuilt and deployed.

## Monitoring

Check the Actions tab to monitor workflow runs:
- **Green checkmark:** Successful run
- **Red X:** Failed run (click for logs)
- **Yellow circle:** Running

## Troubleshooting

### News aggregation fails
- Check if `GEMINI_API_KEY` is set correctly
- Verify Python dependencies in `requirements.txt`
- Review workflow logs for specific errors

### Deployment fails
- Check build logs for syntax errors
- Verify `astro.config.mjs` settings
- Ensure GitHub Pages is enabled (Settings → Pages → Source: GitHub Actions)

### No new posts generated
- This is normal if no articles match keyword filters
- Check `src/content/errors/` for feed fetch errors
- Verify RSS feed URLs in `scripts/config.yaml`
