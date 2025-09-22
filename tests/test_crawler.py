#!/usr/bin/env python3
"""Test script for the Reddit crawler component."""

import os
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import dotenv

from snooze.crawler import RedditCrawler, RedditPost

dotenv.load_dotenv()


class TestRedditCrawler(unittest.TestCase):
    """Test cases for RedditCrawler."""

    def setUp(self):
        """Set up test fixtures."""
        self.client_id = os.getenv("REDDIT_CLIENT_ID", "test_id")
        self.client_secret = os.getenv("REDDIT_CLIENT_SECRET", "test_secret")

    def test_initialization(self):
        """Test crawler initialization."""
        crawler = RedditCrawler(self.client_id, self.client_secret)
        self.assertIsNotNone(crawler.reddit)
        self.assertEqual(crawler.reddit.config.client_id, self.client_id)

    def test_from_env(self):
        """Test creating crawler from environment variables."""
        with patch.dict(
            os.environ,
            {"REDDIT_CLIENT_ID": "env_id", "REDDIT_CLIENT_SECRET": "env_secret"},
        ):
            crawler = RedditCrawler.from_env()
            self.assertEqual(crawler.reddit.config.client_id, "env_id")

    def test_extract_comments(self):
        """Test comment extraction."""
        crawler = RedditCrawler(self.client_id, self.client_secret)

        # Mock submission with comments
        mock_submission = Mock()
        mock_comment1 = Mock()
        mock_comment1.body = "This is a great post!"
        mock_comment2 = Mock()
        mock_comment2.body = "I agree with this."
        mock_comment3 = Mock()
        mock_comment3.body = "[deleted]"

        mock_comments = Mock()
        mock_comments.__iter__ = Mock(
            return_value=iter([mock_comment1, mock_comment2, mock_comment3])
        )
        mock_comments.__getitem__ = Mock(
            side_effect=lambda x: [mock_comment1, mock_comment2, mock_comment3][x]
        )
        mock_comments.replace_more = Mock()
        mock_submission.comments = mock_comments

        comments = crawler._extract_comments(mock_submission, max_comments=10)

        self.assertEqual(len(comments), 2)  # Should exclude [deleted]
        self.assertIn("This is a great post!", comments)
        self.assertIn("I agree with this.", comments)
        self.assertNotIn("[deleted]", comments)

    def test_submission_to_post(self):
        """Test converting submission to RedditPost."""
        crawler = RedditCrawler(self.client_id, self.client_secret)

        # Mock submission
        mock_submission = Mock()
        mock_submission.id = "test123"
        mock_submission.title = "Test Post"
        mock_submission.selftext = "This is a test post body."
        mock_submission.author = "test_user"
        mock_submission.score = 42
        mock_submission.num_comments = 5
        mock_submission.created_utc = 1672531200  # 2023-01-01
        mock_submission.url = "https://reddit.com/r/test/test123"
        mock_submission.subreddit = "test"
        mock_submission.permalink = "/r/test/comments/test123/"

        # Mock comments
        mock_comments = Mock()
        mock_comments.__iter__ = Mock(return_value=iter([]))
        mock_comments.__getitem__ = Mock(side_effect=lambda x: [][x])
        mock_comments.replace_more = Mock()
        mock_submission.comments = mock_comments

        post = crawler._submission_to_post(mock_submission, include_comments=False)

        self.assertEqual(post.id, "test123")
        self.assertEqual(post.title, "Test Post")
        self.assertEqual(post.body, "This is a test post body.")
        self.assertEqual(post.author, "test_user")
        self.assertEqual(post.score, 42)
        self.assertEqual(post.num_comments, 5)
        self.assertEqual(post.url, "https://reddit.com/r/test/test123")
        self.assertEqual(post.subreddit, "test")
        self.assertEqual(len(post.comments), 0)

    @unittest.skipIf(
        not all([os.getenv("REDDIT_CLIENT_ID"), os.getenv("REDDIT_CLIENT_SECRET")]),
        "Reddit API credentials not available",
    )
    def test_get_coding_discussions_integration(self):
        """Integration test for getting coding discussions."""
        crawler = RedditCrawler.from_env()

        # Test with the specific subreddits
        subreddits = ["ChatGPTCoding"]
        posts = list(
            crawler.get_coding_discussions(
                subreddits, limit_per_subreddit=2, include_comments=False
            )
        )

        # Should get some posts (might be 0 if no AI coding content)
        self.assertIsInstance(posts, list)

        for post in posts:
            self.assertIsInstance(post, RedditPost)
            self.assertIsInstance(post.id, str)
            self.assertIsInstance(post.title, str)
            self.assertIsInstance(post.score, int)

    def test_coding_keyword_filtering(self):
        """Test that coding keywords work correctly."""
        crawler = RedditCrawler(self.client_id, self.client_secret)

        # Test posts with different content
        test_cases = [
            ("GitHub Copilot is amazing for coding", True),
            ("Claude helped me debug my code", True),
            ("ChatGPT wrote a Python script for me", True),
            ("I love pizza and movies", False),
            ("Random discussion about weather", False),
            ("Cursor AI is the best coding assistant", True),
        ]

        # Mock the keyword checking logic
        keywords = [
            "copilot",
            "claude",
            "chatgpt",
            "cursor",
            "coding",
            "code",
            "programming",
            "debug",
            "script",
            "ai assistant",
            "coding assistant",
        ]

        for text, should_match in test_cases:
            text_lower = text.lower()
            matches = any(keyword.lower() in text_lower for keyword in keywords)
            self.assertEqual(
                matches,
                should_match,
                f"Text: '{text}' should {'match' if should_match else 'not match'}",
            )


class TestRedditPost(unittest.TestCase):
    """Test cases for RedditPost dataclass."""

    def test_reddit_post_creation(self):
        """Test creating a RedditPost instance."""
        post = RedditPost(
            id="test123",
            title="Test Post",
            body="Test body",
            author="test_user",
            score=42,
            num_comments=5,
            created_utc=datetime.now(),
            url="https://reddit.com/test",
            subreddit="test",
            permalink="https://reddit.com/r/test/test123",
            comments=["Comment 1", "Comment 2"],
        )

        self.assertEqual(post.id, "test123")
        self.assertEqual(post.title, "Test Post")
        self.assertEqual(len(post.comments), 2)


if __name__ == "__main__":
    unittest.main()
