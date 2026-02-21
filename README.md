# pub-blog

An automated An Astro-based automated news aggregator with TTS audio player — powered by [feedmeup](https://github.com/paddedzero/feedmeup).

## How It Works

1. **Weekly News Fetch** — The `news-aggregation.yml` workflow runs on a schedule, runs `scripts/fetch_news.py` to fetch RSS feeds, filter by keywords, deduplicate stories, and generate a Markdown post in `site/content/newsfeed/`.
2. **TTS Audio Generation** — The `deploy.yml` workflow, before building the Astro site, uses [edge-tts](https://github.com/rany2/edge-tts) (Microsoft neural voices, free, no API key) to synthesize the top trending stories into an MP3 saved to `site/public/assets/audio/`.
3. **Mini Audio Player** — The script injects a self-contained, podcast-like HTML/CSS/JS player at the top of the Markdown post before the Astro build runs. No layout changes or component changes required.

## Features

- ✅ Fully automated weekly pipeline
- ✅ TTS audio with Microsoft Edge neural voice (`en-US-AriaNeural`)
- ✅ Inline mini player: play/pause, seek bar, live time display, ARIA accessibility
- ✅ Idempotent — re-running the workflow skips posts that already have a player
- ✅ Zero API keys required

## Audio Player Preview

The player appears at the top of every weekly-scan post:

```
┌─────────────────────────────────────────────┐
│  ▶   🎙️ Listen to this brief                │
│      ───────────────────────  0:00 / 3:42   │
└─────────────────────────────────────────────┘
```

## Local Development

```bash
# Install Python deps
pip install -r requirements.txt

# Run the news fetch locally (outputs to site/content/newsfeed/) locally (outputs to _posts/)
python scripts/fetch_news.py

# Install Node deps and preview the Astro site
npm install
npm run dev
```

## Configuration

Edit `config.yaml` to change feed sources, keyword filters, and deduplication settings. Refer to [feedmeup](https://github.com/paddedzero/feedmeup) for full configuration documentation.

## Deployment

The `deploy.yml` workflow handles everything automatically on push to `main` or via manual dispatch (`workflow_dispatch`).

## Dependencies

| Package | Purpose |
|---------|---------|
| feedparser | RSS/Atom feed parsing |
| PyYAML | Config loading |
| requests | HTTP with retry |
| rapidfuzz | Fuzzy deduplication |
| beautifulsoup4 | HTML → plaintext |
| tzdata | Timezone support |
| edge-tts | Neural TTS synthesis |
