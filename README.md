# Snooze - Reddit AI Agent Discussion Analyzer

Snooze is a Python application that analyzes and visualizes Reddit discussions about AI coding tools.

It focuses on specific coding-related subreddits (r/ClaudeCode, r/codex, r/GithubCopilot, r/ChatGPTCoding), uses LLM to summarize discussions, and includes intelligent caching to avoid repeated API calls.

## Components

1. **Reddit Crawler** (`snooze.crawler`): Crawls Reddit posts using `praw`
2. **LLM Summarizer** (`snooze.summarizer`): Analyzes posts using GPT-5
3. **Web Visualizer** (`snooze.visualizer`): Flask-based web interface

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency management:

```bash
# Clone the repository
git clone https://github.com/Arist12/snooze.git
cd snooze

# Install dependencies
uv sync
```

## Configuration

Create a `.env` file in the project root with your API credentials:

```env
# Reddit API (required for crawling)
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret

# Azure OpenAI (required for analysis)
AZURE_API_KEY=your_azure_openai_key
AZURE_ENDPOINT=https://your-resource.openai.azure.com
AZURE_DEPLOYMENT=your_deployment_name
```

### Getting Reddit API Keys

**Reddit API:**
1. Go to https://www.reddit.com/prefs/apps
2. Create a new app (script type)
3. Use the client ID (at the bottom of your app's name) and secret

## Usage

### Web Interface (Recommended)

Start the web server:
```bash
uv run snooze web
```

Open http://localhost:8080 in your browser and use the interface to analyze discussions.

### Command Line

**Analyze discussions:**
```bash
uv run snooze analyze --subreddits artificial MachineLearning ChatGPT --limit 20
```

**Crawl posts without analysis:**
```bash
uv run snooze crawl --subreddits artificial --limit 50 --search "AI agent"
```

**Get help:**
```bash
uv run snooze --help
```

## Project Structure

```
snooze/
├── src/snooze/
│   ├── __init__.py           # Package initialization
│   ├── crawler.py            # Reddit crawling functionality
│   ├── summarizer.py         # LLM analysis and summarization
│   ├── visualizer.py         # Flask web application
│   ├── main.py              # CLI entry point
│   ├── templates/           # HTML templates
│   │   └── index.html
│   └── static/              # CSS and JavaScript
│       ├── css/style.css
│       └── js/app.js
├── example.py               # Example usage of APIs
├── test_pipeline.py         # Pipeline testing script
├── pyproject.toml          # Project configuration
└── README.md
```

## Attribution

We thank Reddit for providing the data and Claude Code for initiating the codebase.
