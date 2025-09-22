#!/usr/bin/env python3
"""Integration tests for the complete Snooze pipeline with storage."""

import os
import tempfile
import unittest
from datetime import datetime

import dotenv

from snooze.crawler import RedditCrawler, RedditPost
from snooze.storage import DataStorage
from snooze.summarizer import LLMSummarizer

dotenv.load_dotenv()


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete pipeline."""

    def setUp(self):
        """Set up test fixtures."""
        # Use temporary directory for storage
        self.temp_dir = tempfile.mkdtemp()
        self.storage = DataStorage(self.temp_dir)

        # Mock data
        self.mock_posts = [
            RedditPost(
                id="test1",
                title="GitHub Copilot vs Cursor comparison",
                body="I've been testing both GitHub Copilot and Cursor for coding assistance. Here's my experience...",
                author="dev_user1",
                score=45,
                num_comments=12,
                created_utc=datetime.now(),
                url="https://reddit.com/r/ChatGPTCoding/test1",
                subreddit="ChatGPTCoding",
                permalink="https://reddit.com/r/ChatGPTCoding/comments/test1/",
                comments=["Copilot is great for Python", "Cursor has better UI"],
            ),
            RedditPost(
                id="test2",
                title="Claude Code editor features",
                body="The new Claude Code editor has some amazing features for pair programming...",
                author="ai_enthusiast",
                score=38,
                num_comments=8,
                created_utc=datetime.now(),
                url="https://reddit.com/r/ClaudeCode/test2",
                subreddit="ClaudeCode",
                permalink="https://reddit.com/r/ClaudeCode/comments/test2/",
                comments=["Love the new interface", "How does it compare to VSCode?"],
            ),
        ]

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_storage_posts_roundtrip(self):
        """Test saving and loading posts."""
        cache_key = self.storage.generate_posts_cache_key(["ChatGPTCoding"], 20)

        # Save posts
        self.storage.save_posts(self.mock_posts, cache_key)

        # Load posts
        loaded_posts = self.storage.load_posts(cache_key)

        self.assertIsNotNone(loaded_posts)
        self.assertEqual(len(loaded_posts), 2)
        self.assertEqual(loaded_posts[0].id, "test1")
        self.assertEqual(loaded_posts[1].title, "Claude Code editor features")

    def test_cache_key_generation(self):
        """Test cache key generation is consistent."""
        key1 = self.storage.generate_posts_cache_key(
            ["ChatGPTCoding", "ClaudeCode"], 20
        )
        key2 = self.storage.generate_posts_cache_key(
            ["ClaudeCode", "ChatGPTCoding"], 20
        )

        # Should be the same regardless of order
        self.assertEqual(key1, key2)

        # Different parameters should give different keys
        key3 = self.storage.generate_posts_cache_key(["ChatGPTCoding"], 20)
        self.assertNotEqual(key1, key3)

    def test_cache_expiration(self):
        """Test that cache expiration works."""
        cache_key = "test_cache"

        # Save posts
        self.storage.save_posts(self.mock_posts, cache_key)

        # Should be valid immediately
        loaded = self.storage.load_posts(cache_key, max_age_hours=24)
        self.assertIsNotNone(loaded)

        # Should be invalid with very short expiration
        loaded = self.storage.load_posts(cache_key, max_age_hours=0)
        self.assertIsNone(loaded)

    def test_cache_stats(self):
        """Test cache statistics."""
        # Initially empty
        stats = self.storage.get_cache_stats()
        self.assertEqual(stats["posts"]["file_count"], 0)

        # Save some data
        self.storage.save_posts(self.mock_posts, "test_posts")

        # Check stats updated
        stats = self.storage.get_cache_stats()
        self.assertEqual(stats["posts"]["file_count"], 1)
        self.assertGreater(stats["posts"]["total_size_mb"], 0)

    def test_cache_clearing(self):
        """Test cache clearing functionality."""
        # Save some data
        self.storage.save_posts(self.mock_posts, "test_posts")

        # Check it exists
        stats = self.storage.get_cache_stats()
        self.assertEqual(stats["posts"]["file_count"], 1)

        # Clear cache
        deleted_count = self.storage.clear_cache(category="posts")
        self.assertEqual(deleted_count, 1)

        # Check it's gone
        stats = self.storage.get_cache_stats()
        self.assertEqual(stats["posts"]["file_count"], 0)

    @unittest.skipIf(
        not all([os.getenv("REDDIT_CLIENT_ID"), os.getenv("REDDIT_CLIENT_SECRET")]),
        "Reddit API credentials not available",
    )
    def test_crawler_coding_discussions(self):
        """Test the simplified crawler for coding discussions."""
        crawler = RedditCrawler.from_env()

        # Test with a smaller subreddit that's more likely to exist
        posts = list(
            crawler.get_coding_discussions(
                ["ChatGPTCoding"], limit_per_subreddit=5, include_comments=False
            )
        )

        # May be empty if subreddit doesn't exist or has no content
        self.assertIsInstance(posts, list)

        # If we got posts, verify they're properly formed
        for post in posts:
            self.assertIsInstance(post, RedditPost)
            self.assertIsInstance(post.id, str)
            self.assertIsInstance(post.title, str)
            self.assertEqual(post.subreddit.lower(), "chatgptcoding")

    @unittest.skipIf(
        not all(
            [
                os.getenv("AZURE_API_KEY"),
                os.getenv("AZURE_ENDPOINT"),
                os.getenv("AZURE_DEPLOYMENT"),
            ]
        ),
        "Azure OpenAI credentials not available",
    )
    def test_end_to_end_with_storage(self):
        """Test the complete pipeline with storage caching."""
        crawler = RedditCrawler.from_env()
        summarizer = LLMSummarizer.from_env()

        # Use mock posts to avoid Reddit API dependency
        posts = self.mock_posts

        # Test caching posts
        posts_cache_key = self.storage.generate_posts_cache_key(["ChatGPTCoding"], 20)
        self.storage.save_posts(posts, posts_cache_key)

        # Load from cache
        cached_posts = self.storage.load_posts(posts_cache_key)
        self.assertEqual(len(cached_posts), 2)

        # Test summarization (this will hit the actual API)
        summaries = summarizer.summarize_posts(cached_posts[:1])  # Just test one post

        if summaries:  # API call might fail
            # Test caching summaries
            summaries_cache_key = self.storage.generate_summaries_cache_key(
                cached_posts[:1]
            )
            self.storage.save_summaries(summaries, summaries_cache_key)

            # Load summaries from cache
            cached_summaries = self.storage.load_summaries(summaries_cache_key)
            self.assertEqual(len(cached_summaries), len(summaries))

            # Test discussion summary
            discussion = summarizer.create_discussion_summary(summaries)
            if discussion:
                # Test caching discussion
                discussion_cache_key = self.storage.generate_discussion_cache_key(
                    summaries
                )
                self.storage.save_discussion(discussion, discussion_cache_key)

                # Load discussion from cache
                cached_discussion = self.storage.load_discussion(discussion_cache_key)
                self.assertEqual(cached_discussion.topic, discussion.topic)

    def test_visualization_data_flow(self):
        """Test data flow in the visualization component."""
        from snooze.visualizer import SnoozeVisualizer

        # Create visualizer with our temp storage
        visualizer = SnoozeVisualizer()
        visualizer.storage = self.storage

        # Test serialization methods
        from snooze.summarizer import DiscussionSummary, PostSummary

        # Create mock summary
        mock_summary = PostSummary(
            original_post_id="test1",
            title="Test Summary",
            key_points=["Point 1", "Point 2"],
            sentiment="positive",
            topics=["coding", "ai"],
            summary="Test summary content",
            engagement_score=8,
            url="https://reddit.com/test",
            subreddit="ChatGPTCoding",
        )

        # Test serialization
        serialized = visualizer._serialize_post_summary(mock_summary)
        self.assertEqual(serialized["id"], "test1")
        self.assertEqual(serialized["sentiment"], "positive")

        # Test discussion serialization
        mock_discussion = DiscussionSummary(
            topic="AI Coding Tools",
            key_insights=["Insight 1"],
            common_themes=["Theme 1"],
            sentiment_overview="Positive",
            post_summaries=[mock_summary],
            total_engagement=50,
        )

        serialized_discussion = visualizer._serialize_discussion(mock_discussion)
        self.assertEqual(serialized_discussion["topic"], "AI Coding Tools")
        self.assertIn("analysis_time", serialized_discussion)

    def test_error_handling(self):
        """Test error handling in various components."""
        # Test loading non-existent cache
        result = self.storage.load_posts("nonexistent_key")
        self.assertIsNone(result)

        # Test with corrupted cache file
        corrupted_file = self.storage.posts_dir / "corrupted.json"
        with open(corrupted_file, "w") as f:
            f.write("invalid json {")

        result = self.storage.load_posts("corrupted")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
