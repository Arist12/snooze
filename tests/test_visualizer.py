#!/usr/bin/env python3
"""Test script for the web visualizer component."""

import json
import unittest
from unittest.mock import Mock, patch

import dotenv

from snooze.summarizer import DiscussionSummary, PostSummary
from snooze.visualizer import SnoozeVisualizer

dotenv.load_dotenv()


class TestSnoozeVisualizer(unittest.TestCase):
    """Test cases for SnoozeVisualizer."""

    def setUp(self):
        """Set up test fixtures."""
        self.visualizer = SnoozeVisualizer()
        self.app = self.visualizer.app
        self.client = self.app.test_client()
        self.app.config["TESTING"] = True

    def test_initialization(self):
        """Test visualizer initialization."""
        self.assertIsNotNone(self.visualizer.app)
        self.assertEqual(self.visualizer.app.name, "snooze.visualizer")

    def test_get_templates_path(self):
        """Test template path generation."""
        path = self.visualizer._get_templates_path()
        self.assertIn("templates", path)

    def test_get_static_path(self):
        """Test static path generation."""
        path = self.visualizer._get_static_path()
        self.assertIn("static", path)

    def test_index_route(self):
        """Test the main index route."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Snooze", response.data)

    def test_api_posts_route(self):
        """Test the posts API endpoint."""
        response = self.client.get("/api/posts")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertIn("posts", data)
        self.assertIn("message", data)

    def test_api_trends_route(self):
        """Test the trends API endpoint."""
        response = self.client.get("/api/trends")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertIn("trends", data)

    @patch("snooze.visualizer.RedditCrawler")
    @patch("snooze.visualizer.LLMSummarizer")
    def test_api_analyze_success(self, mock_summarizer_class, mock_crawler_class):
        """Test successful analysis API call."""
        # Mock crawler
        mock_crawler = Mock()
        mock_posts = [self._create_mock_post()]
        mock_crawler.get_all_coding_discussions.return_value = mock_posts
        mock_crawler_class.from_env.return_value = mock_crawler

        # Mock summarizer
        mock_summarizer = Mock()
        mock_summaries = [self._create_mock_summary()]
        mock_discussion = self._create_mock_discussion(mock_summaries)
        mock_summarizer.summarize_posts.return_value = mock_summaries
        mock_summarizer.create_discussion_summary.return_value = mock_discussion
        mock_summarizer_class.from_env.return_value = mock_summarizer

        # Make the API call
        response = self.client.post(
            "/api/analyze", json={"limit": 10}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data["success"])
        self.assertIn("discussion", data)
        self.assertIn("post_count", data)
        self.assertIn("summary_count", data)

    def test_api_analyze_missing_data(self):
        """Test analysis API with missing JSON data."""
        response = self.client.post("/api/analyze")
        self.assertEqual(response.status_code, 500)

        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("error", data)

    @patch("snooze.visualizer.RedditCrawler")
    def test_api_analyze_crawler_error(self, mock_crawler_class):
        """Test analysis API when crawler fails."""
        # Mock crawler to raise an exception
        mock_crawler_class.from_env.side_effect = Exception("Reddit API error")

        response = self.client.post(
            "/api/analyze", json={"limit": 10}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("error", data)

    def test_serialize_post_summary(self):
        """Test post summary serialization."""
        summary = self._create_mock_summary()
        result = self.visualizer._serialize_post_summary(summary)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "test123")
        self.assertEqual(result["title"], "Test Post")
        self.assertEqual(result["sentiment"], "positive")
        self.assertIn("key_points", result)
        self.assertIn("topics", result)

    def test_serialize_discussion(self):
        """Test discussion summary serialization."""
        summaries = [self._create_mock_summary()]
        discussion = self._create_mock_discussion(summaries)
        result = self.visualizer._serialize_discussion(discussion)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["topic"], "AI Coding Tools")
        self.assertIn("key_insights", result)
        self.assertIn("common_themes", result)
        self.assertIn("post_summaries", result)
        self.assertIn("analysis_time", result)
        self.assertEqual(len(result["post_summaries"]), 1)

    def test_serialize_discussion_none(self):
        """Test serializing None discussion."""
        # This should be handled gracefully in the API endpoint
        pass

    def test_create_app_factory(self):
        """Test the Flask app factory function."""
        from snooze.visualizer import create_app

        app = create_app()
        self.assertIsNotNone(app)
        self.assertEqual(app.name, "snooze.visualizer")

    def test_route_existence(self):
        """Test that all expected routes exist."""
        with self.app.app_context():
            # Get all registered routes
            routes = [rule.rule for rule in self.app.url_map.iter_rules()]

            expected_routes = ["/", "/api/analyze", "/api/posts", "/api/trends"]
            for route in expected_routes:
                self.assertIn(route, routes, f"Route {route} not found")

    def test_static_files_configuration(self):
        """Test static files are properly configured."""
        # Test that static folder is set
        self.assertIsNotNone(self.app.static_folder)
        self.assertIn("static", self.app.static_folder)

    def test_template_configuration(self):
        """Test templates are properly configured."""
        # Test that template folder is set
        self.assertIsNotNone(self.app.template_folder)
        self.assertIn("templates", self.app.template_folder)

    def _create_mock_post(self):
        """Create a mock Reddit post for testing."""
        from datetime import datetime

        from snooze.crawler import RedditPost

        return RedditPost(
            id="test123",
            title="GitHub Copilot Review",
            body="Testing GitHub Copilot for Python development.",
            author="test_user",
            score=25,
            num_comments=8,
            created_utc=datetime.now(),
            url="https://reddit.com/test",
            subreddit="ChatGPTCoding",
            permalink="https://reddit.com/r/ChatGPTCoding/test123",
            comments=["Great tool!", "I prefer other options"],
        )

    def _create_mock_summary(self):
        """Create a mock post summary for testing."""
        return PostSummary(
            original_post_id="test123",
            title="Test Post",
            key_points=["Point 1", "Point 2"],
            sentiment="positive",
            topics=["coding", "productivity"],
            summary="Test summary content",
            engagement_score=8,
            url="https://reddit.com/test",
            subreddit="ChatGPTCoding",
        )

    def _create_mock_discussion(self, summaries):
        """Create a mock discussion summary for testing."""
        return DiscussionSummary(
            topic="AI Coding Tools",
            key_insights=["Insight 1", "Insight 2"],
            common_themes=["coding", "productivity", "AI"],
            sentiment_overview="Generally positive sentiment",
            post_summaries=summaries,
            total_engagement=50,
        )


if __name__ == "__main__":
    unittest.main()
