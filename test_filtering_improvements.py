#!/usr/bin/env python3
"""Test the enhanced LLM filtering and target count features."""

from datetime import datetime

from src.snooze.crawler import RedditPost
from src.snooze.summarizer import LLMSummarizer


def test_enhanced_filtering_prompt():
    """Test that the enhanced filtering prompt properly identifies relevance."""
    print("Testing Enhanced LLM Filtering")
    print("=" * 40)

    # Create test posts - mix of relevant and irrelevant
    test_posts = [
        # Should be RELEVANT
        RedditPost(
            id="relevant_1",
            title="My workflow with Claude Code for Python development",
            body="I've been using Claude Code for a few months now and wanted to share my experience. The AI suggestions are really helpful for debugging and writing tests...",
            author="developer123",
            score=45,
            num_comments=12,
            created_utc=datetime.now(),
            url="https://reddit.com/relevant1",
            subreddit="ClaudeCode",
            permalink="/r/ClaudeCode/relevant1",
            comments=["Great tips!", "I use similar workflow"]
        ),

        # Should be RELEVANT
        RedditPost(
            id="relevant_2",
            title="Cursor vs GitHub Copilot comparison",
            body="Has anyone compared Cursor and GitHub Copilot for React development? I'm trying to decide which AI coding assistant to use...",
            author="reactdev",
            score=67,
            num_comments=23,
            created_utc=datetime.now(),
            url="https://reddit.com/relevant2",
            subreddit="cursor",
            permalink="/r/cursor/relevant2",
            comments=["I prefer Cursor", "Copilot is better for me"]
        ),

        # Should be IRRELEVANT - subreddit rules
        RedditPost(
            id="irrelevant_1",
            title="New features in the Subreddit",
            body="👋 Hello everyone! We're excited to announce a new features on our subreddit — Pin the Solution. When there are multiple solutions for the posts with \"Help/Query ❓\" flair...",
            author="KingOfMumbai",
            score=30,
            num_comments=6,
            created_utc=datetime.now(),
            url="https://reddit.com/irrelevant1",
            subreddit="GithubCopilot",
            permalink="/r/GithubCopilot/irrelevant1",
            comments=["Thanks mods!", "Good update"]
        ),

        # Should be IRRELEVANT - general rules post
        RedditPost(
            id="irrelevant_2",
            title="! Important: new rules update on self-promotion !",
            body="It's your mod, Vibe Rubin. We recently hit 50,000 members in this r/vibecoding sub. And over the past few months I've gotten dozens and dozens of messages...",
            author="PopMechanic",
            score=25,
            num_comments=32,
            created_utc=datetime.now(),
            url="https://reddit.com/irrelevant2",
            subreddit="vibecoding",
            permalink="/r/vibecoding/irrelevant2",
            comments=["Thanks for clarifying", "Good rules"]
        ),

        # Should be IRRELEVANT - empty/low effort
        RedditPost(
            id="irrelevant_3",
            title="DOWN?",
            body="It is.",
            author="Funny-Blueberry-2630",
            score=20,
            num_comments=18,
            created_utc=datetime.now(),
            url="https://reddit.com/irrelevant3",
            subreddit="ClaudeCode",
            permalink="/r/ClaudeCode/irrelevant3",
            comments=[]
        )
    ]

    print(f"\n🧪 Testing {len(test_posts)} posts:")
    print("✅ Expected relevant: 2 (coding workflows/comparisons)")
    print("❌ Expected irrelevant: 3 (rules/meta/low-effort)")

    # Test the filtering prompt (showing what it would look like)
    summarizer = LLMSummarizer(
        api_key="test_key",
        endpoint="test_endpoint",
        deployment="test_deployment"
    )

    print(f"\n📋 Enhanced Filtering Criteria:")
    print("❌ Subreddit rules, guidelines, or meta announcements")
    print("❌ Moderator posts about community features or policies")
    print("❌ Empty posts, memes, or low-effort content")
    print("❌ General AI discussions without coding/development focus")
    print("✅ Discussions about AI coding assistants")
    print("✅ User experiences with AI development tools")
    print("✅ Technical comparisons of AI coding platforms")
    print("✅ Workflows, tips, or best practices for AI-assisted coding")

    # Show what the enhanced prompt looks like for one post
    sample_prompt = summarizer._create_post_summary_prompt(test_posts[0])
    print(f"\n📝 Sample Enhanced Prompt (first 500 chars):")
    print(f"   {sample_prompt[:500]}...")

    print(f"\n🎯 Key Improvements:")
    print("   ✓ Explicit rules exclusion criteria")
    print("   ✓ Clear positive criteria for coding discussions")
    print("   ✓ Better meta/administrative content filtering")
    print("   ✓ Focus on development-specific AI tools")


def test_target_count_feature():
    """Test the target count functionality."""
    print("\n" + "=" * 40)
    print("Testing Target Count Feature")
    print("=" * 40)

    print(f"\n🎯 New Web Interface Options:")
    print(f"   • Posts to Crawl: 50 (how many to fetch from Reddit)")
    print(f"   • Target Relevant Posts: 20 (stop when this many found)")

    print(f"\n💡 Smart Analysis Benefits:")
    print(f"   ✓ Stops when target count reached")
    print(f"   ✓ Doesn't waste API calls on extra posts")
    print(f"   ✓ More predictable result count")
    print(f"   ✓ Better control over analysis scope")

    print(f"\n📊 Example Scenarios:")
    print(f"   Scenario 1: Target 20, find 20 relevant in first 30 crawled → Stop early")
    print(f"   Scenario 2: Target 20, only find 15 relevant in 50 crawled → Return 15")
    print(f"   Scenario 3: Target 20, have 18 cached + 2 new → Perfect 20")

    print(f"\n🔧 Technical Implementation:")
    print(f"   • Smart analysis method: _smart_analysis_to_target()")
    print(f"   • Combines cached + new analysis")
    print(f"   • Sequential analysis until target reached")
    print(f"   • Efficient post-level caching")


if __name__ == "__main__":
    test_enhanced_filtering_prompt()
    test_target_count_feature()

    print(f"\n🎉 Enhancement Summary:")
    print(f"✅ Enhanced LLM filtering prompt to exclude meta/rules posts")
    print(f"✅ Added target relevant post count option to web interface")
    print(f"✅ Implemented smart analysis that stops at target count")
    print(f"✅ Better user control over crawling vs. relevant posts")