#!/usr/bin/env python3
"""Test script for the LLM summarizer component."""

import json
import os
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import dotenv

from snooze.crawler import RedditPost
from snooze.summarizer import DiscussionSummary, LLMSummarizer, PostSummary

dotenv.load_dotenv()


class TestLLMSummarizer(unittest.TestCase):
    """Test cases for LLMSummarizer."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_key = os.getenv("AZURE_API_KEY", "test_key")
        self.endpoint = os.getenv("AZURE_ENDPOINT", "https://test.openai.azure.com")
        self.deployment = os.getenv("AZURE_DEPLOYMENT", "test_deployment")

    def test_initialization(self):
        """Test summarizer initialization."""
        summarizer = LLMSummarizer(self.api_key, self.endpoint, self.deployment)
        self.assertIsNotNone(summarizer.client)
        self.assertEqual(summarizer.deployment, self.deployment)

    def test_from_env(self):
        """Test creating summarizer from environment variables."""
        with patch.dict(
            os.environ,
            {
                "AZURE_API_KEY": "env_key",
                "AZURE_ENDPOINT": "https://env.openai.azure.com",
                "AZURE_DEPLOYMENT": "env_deployment",
            },
        ):
            summarizer = LLMSummarizer.from_env()
            self.assertEqual(summarizer.deployment, "env_deployment")

    def test_create_post_summary_prompt(self):
        """Test prompt creation for post summarization."""
        summarizer = LLMSummarizer(self.api_key, self.endpoint, self.deployment)

        post = RedditPost(
            id="test123",
            title="GitHub Copilot vs Cursor",
            body="I've been comparing GitHub Copilot and Cursor for coding assistance.",
            author="test_user",
            score=25,
            num_comments=10,
            created_utc=datetime.now(),
            url="https://reddit.com/test",
            subreddit="ChatGPTCoding",
            permalink="https://reddit.com/r/ChatGPTCoding/test123",
            comments=["Copilot is better", "I prefer Cursor for its features"],
        )

        prompt = summarizer._create_post_summary_prompt(post)

        self.assertIn("GitHub Copilot vs Cursor", prompt)
        self.assertIn("ChatGPTCoding", prompt)
        self.assertIn("Copilot is better", prompt)
        self.assertIn("JSON", prompt)

    def test_create_discussion_summary_prompt(self):
        """Test prompt creation for discussion summarization."""
        summarizer = LLMSummarizer(self.api_key, self.endpoint, self.deployment)

        summaries = [
            PostSummary(
                original_post_id="1",
                title="Copilot Review",
                key_points=["Easy to use", "Good suggestions"],
                sentiment="positive",
                topics=["coding assistant", "productivity"],
                summary="Positive review of Copilot",
                engagement_score=8,
                url="https://reddit.com/1",
                subreddit="ChatGPTCoding",
            ),
            PostSummary(
                original_post_id="2",
                title="Cursor Features",
                key_points=["AI pair programming", "Great UI"],
                sentiment="positive",
                topics=["coding assistant", "interface"],
                summary="Discussion of Cursor features",
                engagement_score=7,
                url="https://reddit.com/2",
                subreddit="ChatGPTCoding",
            ),
        ]

        prompt = summarizer._create_discussion_summary_prompt(summaries)

        self.assertIn("Copilot Review", prompt)
        self.assertIn("Cursor Features", prompt)
        self.assertIn("coding assistant", prompt)
        self.assertIn("JSON", prompt)

    @patch.object(LLMSummarizer, "client", create=True)
    def test_summarize_post_success(self, mock_client):
        """Test successful post summarization."""
        # Mock the API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "key_points": ["Point 1", "Point 2"],
                "sentiment": "positive",
                "topics": ["topic1", "topic2"],
                "summary": "Test summary",
                "engagement_score": 8,
            }
        )

        mock_client.chat.completions.create.return_value = mock_response

        summarizer = LLMSummarizer(self.api_key, self.endpoint, self.deployment)
        summarizer.client = mock_client

        post = self._create_test_post()
        result = summarizer.summarize_post(post)

        self.assertIsInstance(result, PostSummary)
        self.assertEqual(result.original_post_id, "test123")
        self.assertEqual(result.sentiment, "positive")
        self.assertEqual(len(result.key_points), 2)
        self.assertEqual(len(result.topics), 2)

    @patch.object(LLMSummarizer, "client", create=True)
    def test_summarize_post_invalid_json(self, mock_client):
        """Test post summarization with invalid JSON response."""
        # Mock the API response with invalid JSON
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Invalid JSON response"

        mock_client.chat.completions.create.return_value = mock_response

        summarizer = LLMSummarizer(self.api_key, self.endpoint, self.deployment)
        summarizer.client = mock_client

        post = self._create_test_post()
        result = summarizer.summarize_post(post)

        self.assertIsNone(result)

    @patch.object(LLMSummarizer, "client", create=True)
    def test_summarize_post_with_wrapped_json(self, mock_client):
        """Test post summarization with JSON wrapped in other text."""
        # Mock response with JSON wrapped in text
        json_content = {
            "key_points": ["Point 1"],
            "sentiment": "neutral",
            "topics": ["topic1"],
            "summary": "Test summary",
            "engagement_score": 5,
        }
        wrapped_response = (
            f"Here's the analysis:\n{json.dumps(json_content)}\nThat's it!"
        )

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = wrapped_response

        mock_client.chat.completions.create.return_value = mock_response

        summarizer = LLMSummarizer(self.api_key, self.endpoint, self.deployment)
        summarizer.client = mock_client

        post = self._create_test_post()
        result = summarizer.summarize_post(post)

        self.assertIsInstance(result, PostSummary)
        self.assertEqual(result.sentiment, "neutral")

    @patch.object(LLMSummarizer, "client", create=True)
    def test_create_discussion_summary_success(self, mock_client):
        """Test successful discussion summary creation."""
        # Mock the API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "topic": "AI Coding Tools Comparison",
                "key_insights": ["Insight 1", "Insight 2"],
                "common_themes": ["Theme 1", "Theme 2"],
                "sentiment_overview": "Generally positive sentiment",
            }
        )

        mock_client.chat.completions.create.return_value = mock_response

        summarizer = LLMSummarizer(self.api_key, self.endpoint, self.deployment)
        summarizer.client = mock_client

        summaries = [self._create_test_summary()]
        result = summarizer.create_discussion_summary(summaries)

        self.assertIsInstance(result, DiscussionSummary)
        self.assertEqual(result.topic, "AI Coding Tools Comparison")
        self.assertEqual(len(result.key_insights), 2)
        self.assertEqual(len(result.common_themes), 2)
        self.assertEqual(len(result.post_summaries), 1)

    def test_summarize_posts(self):
        """Test summarizing multiple posts."""
        summarizer = LLMSummarizer(self.api_key, self.endpoint, self.deployment)

        posts = [self._create_test_post()]

        with patch.object(summarizer, "summarize_post") as mock_summarize:
            mock_summarize.return_value = self._create_test_summary()

            results = summarizer.summarize_posts(posts)

            self.assertEqual(len(results), 1)
            self.assertIsInstance(results[0], PostSummary)
            mock_summarize.assert_called_once()

    def test_analyze_trends(self):
        """Test trend analysis across discussions."""
        summarizer = LLMSummarizer(self.api_key, self.endpoint, self.deployment)

        discussions = [
            DiscussionSummary(
                topic="AI Tools",
                key_insights=["Insight 1"],
                common_themes=["coding", "productivity"],
                sentiment_overview="Positive",
                post_summaries=[self._create_test_summary()],
                total_engagement=50,
            ),
            DiscussionSummary(
                topic="Code Assistants",
                key_insights=["Insight 2"],
                common_themes=["coding", "efficiency"],
                sentiment_overview="Mixed",
                post_summaries=[self._create_test_summary()],
                total_engagement=30,
            ),
        ]

        trends = summarizer.analyze_trends(discussions)

        self.assertIn("top_themes", trends)
        self.assertIn("sentiment_distribution", trends)
        self.assertIn("total_discussions", trends)
        self.assertEqual(trends["total_discussions"], 2)
        self.assertGreater(trends["average_engagement"], 0)

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
    def test_summarize_post_integration(self):
        """Integration test for post summarization with real API."""
        summarizer = LLMSummarizer.from_env()
        post = self._create_test_post()

        result = summarizer.summarize_post(post)

        if result:  # API call might fail for various reasons
            self.assertIsInstance(result, PostSummary)
            self.assertEqual(result.original_post_id, "test123")
            self.assertIsInstance(result.sentiment, str)
            self.assertIsInstance(result.topics, list)
            self.assertIsInstance(result.key_points, list)

    def _create_test_post(self) -> RedditPost:
        """Create a test RedditPost."""
        return RedditPost(
            id="test123",
            title="Testing GitHub Copilot with Python",
            body="I've been using GitHub Copilot for Python development and it's quite helpful for generating boilerplate code.",
            author="test_user",
            score=15,
            num_comments=5,
            created_utc=datetime.now(),
            url="https://reddit.com/test",
            subreddit="ChatGPTCoding",
            permalink="https://reddit.com/r/ChatGPTCoding/test123",
            comments=["Copilot saves me time", "I prefer writing code myself"],
        )

    def _create_test_summary(self) -> PostSummary:
        """Create a test PostSummary."""
        return PostSummary(
            original_post_id="test123",
            title="Test Summary",
            key_points=["Point 1", "Point 2"],
            sentiment="positive",
            topics=["coding", "productivity"],
            summary="Test summary content",
            engagement_score=7,
            url="https://reddit.com/test",
            subreddit="ChatGPTCoding",
        )


if __name__ == "__main__":
    unittest.main()
