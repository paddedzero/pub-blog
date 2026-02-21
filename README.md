# pub-blog

A Jekyll-based automated news aggregator with TTS audio player — powered by [feedmeup](https://github.com/paddedzero/feedmeup).

## How It Works

1. **Weekly News Fetch** — The `deploy.yml` workflow runs on a schedule, fetches RSS feeds, filters by keywords, deduplicates stories, and generates a Jekyll Markdown post in `_posts/`.
2. **TTS Audio Generation** — In the same workflow, immediately after the news post is created, an inline Python script uses [edge-tts](https://github.com/rany2/edge-tts) (Microsoft neural voices, free, no API key) to synthesize the top headlines into an MP3.
3. **Mini Audio Player** — The script injects a self-contained, podcast-like HTML/CSS/JS player at the top of the post before GitHub Pages builds and deploys the site. No layout changes or Jekyll plugins required.

## Features

- ✅ Fully automated weekly pipeline
- ✅ TTS audio with Microsoft Edge neural voice (`en-US-AriaNeural`)
- ✅ Inline mini player: play/pause, seek bar, live time display
- ✅ Idempotent — re-running the workflow skips posts that already have a player
- ✅ Zero API keys required

## Audio Player Preview

The player appears at the top of every news brief post:

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

# Run the news fetch locally (outputs to _posts/)
python fetch_news.py

# Preview the Jekyll site
bundle exec jekyll serve
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
