#!/usr/bin/env python3
"""Test script to verify the complete Snooze pipeline."""

import os
from datetime import datetime

import dotenv

from snooze.crawler import RedditPost
from snooze.summarizer import LLMSummarizer

# Load environment variables
dotenv.load_dotenv()


def create_mock_post() -> RedditPost:
    """Create a mock Reddit post for testing."""
    return RedditPost(
        id="test123",
        title="New AI Agent Framework Revolutionizes Automation",
        body="I've been working with this new AI agent framework called AgentFlow, and it's incredible how it can automate complex workflows. The framework allows you to chain multiple LLMs together and create autonomous agents that can handle multi-step tasks. Has anyone else tried something similar?",
        author="tech_enthusiast",
        score=45,
        num_comments=12,
        created_utc=datetime.now(),
        url="https://reddit.com/r/artificial/test123",
        subreddit="artificial",
        permalink="https://reddit.com/r/artificial/comments/test123/",
        comments=[
            "This sounds amazing! I've been looking for something like this for my workflow automation.",
            "Can you share more details about the implementation? Is it open source?",
            "I tried building something similar but ran into issues with context management between agents.",
            "The multi-LLM chaining is exactly what I need for my project. Thanks for sharing!",
        ],
    )


def test_summarizer():
    """Test the LLM summarizer with a mock post."""
    print("Testing LLM Summarizer...")

    # Check if Azure credentials are available
    required_vars = ["AZURE_API_KEY", "AZURE_ENDPOINT", "AZURE_DEPLOYMENT"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"❌ Missing Azure credentials: {', '.join(missing_vars)}")
        print("Skipping LLM summarizer test.")
        return False

    try:
        summarizer = LLMSummarizer.from_env()
        mock_post = create_mock_post()

        print("📝 Summarizing mock post...")
        summary = summarizer.summarize_post(mock_post)

        if summary:
            print("✅ Post summarization successful!")
            print(f"   Title: {summary.title}")
            print(f"   Sentiment: {summary.sentiment}")
            print(f"   Topics: {', '.join(summary.topics)}")
            print(f"   Summary: {summary.summary}")
            print(f"   Key Points: {len(summary.key_points)}")
            return True
        else:
            print("❌ Post summarization failed - no summary returned")
            return False

    except Exception as e:
        print(f"❌ Error testing summarizer: {e}")
        return False


def test_reddit_crawler():
    """Test the Reddit crawler (basic functionality)."""
    print("Testing Reddit Crawler...")

    # Check if Reddit credentials are available
    required_vars = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"❌ Missing Reddit credentials: {', '.join(missing_vars)}")
        print("Skipping Reddit crawler test.")
        return False

    try:
        from snooze.crawler import RedditCrawler

        crawler = RedditCrawler.from_env()
        print("✅ Reddit crawler initialized successfully!")

        # Test basic Reddit connection (this should work with valid credentials)
        print("🔍 Testing Reddit API connection...")

        # Try to get a few posts from coding subreddits
        posts = list(
            crawler.get_coding_discussions(
                ["ChatGPTCoding"], limit_per_subreddit=2, include_comments=False
            )
        )

        if posts:
            print(f"✅ Successfully retrieved {len(posts)} posts!")
            for post in posts[:2]:
                print(f"   • {post.title[:60]}... (r/{post.subreddit})")
            return True
        else:
            print("⚠️  No posts retrieved (this might be normal)")
            return True

    except Exception as e:
        print(f"❌ Error testing Reddit crawler: {e}")
        return False


def main():
    """Run all pipeline tests."""
    print("🚀 Testing Snooze Pipeline")
    print("=" * 50)

    # Test basic imports
    print("📦 Testing imports...")
    try:
        from snooze import SnoozeVisualizer

        print("✅ All imports successful!")
    except Exception as e:
        print(f"❌ Import error: {e}")
        return

    print()

    # Test individual components
    reddit_ok = test_reddit_crawler()
    print()

    summarizer_ok = test_summarizer()
    print()

    # Test web visualizer
    print("Testing Web Visualizer...")
    try:
        from snooze.visualizer import SnoozeVisualizer

        visualizer = SnoozeVisualizer()
        print("✅ Web visualizer initialized successfully!")
        web_ok = True
    except Exception as e:
        print(f"❌ Error testing web visualizer: {e}")
        web_ok = False

    print()
    print("=" * 50)
    print("📊 Test Results Summary:")
    print(f"   Reddit Crawler: {'✅ PASS' if reddit_ok else '❌ FAIL'}")
    print(f"   LLM Summarizer: {'✅ PASS' if summarizer_ok else '❌ FAIL'}")
    print(f"   Web Visualizer: {'✅ PASS' if web_ok else '❌ FAIL'}")

    if all([reddit_ok, summarizer_ok, web_ok]):
        print("\n🎉 All tests passed! Snooze pipeline is ready to use.")
        print("\nTo get started:")
        print("   1. Make sure your .env file has the required API keys")
        print("   2. Run: uv run snooze web")
        print("   3. Open http://localhost:8080 in your browser")
    else:
        print("\n⚠️  Some tests failed. Check your configuration and API keys.")


if __name__ == "__main__":
    main()
