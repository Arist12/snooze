import os
from dataclasses import dataclass
from typing import List, Optional

from openai import AzureOpenAI

from .crawler import RedditPost


@dataclass
class PostSummary:
    """Represents a summarized Reddit post."""

    original_post_id: str
    title: str
    key_points: List[str]
    sentiment: str
    topics: List[str]
    summary: str
    engagement_score: int
    url: str
    subreddit: str


@dataclass
class DiscussionSummary:
    """Represents a summary of multiple related posts."""

    topic: str
    key_insights: List[str]
    common_themes: List[str]
    sentiment_overview: str
    post_summaries: List[PostSummary]
    total_engagement: int


class LLMSummarizer:
    """Uses Azure OpenAI to summarize Reddit discussions about AI agents."""

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        deployment: str,
        api_version: str = "2024-12-01-preview",
    ):
        """Initialize the LLM summarizer with Azure OpenAI credentials."""
        self.client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )
        self.deployment = deployment

    @classmethod
    def from_env(cls) -> "LLMSummarizer":
        """Create an LLMSummarizer instance using environment variables."""
        return cls(
            api_key=os.getenv("AZURE_API_KEY"),
            endpoint=os.getenv("AZURE_ENDPOINT"),
            deployment=os.getenv("AZURE_DEPLOYMENT"),
        )

    def _create_post_summary_prompt(self, post: RedditPost) -> str:
        """Create a prompt for summarizing a single Reddit post."""
        comments_text = (
            "\n".join(post.comments[:10]) if post.comments else "No comments"
        )

        return f"""
Analyze this Reddit post about AI agents and provide a structured summary.

POST DETAILS:
Title: {post.title}
Subreddit: r/{post.subreddit}
Score: {post.score}
Comments: {post.num_comments}

CONTENT:
{post.body}

TOP COMMENTS:
{comments_text}

Please provide a JSON response with the following structure:
{{
    "key_points": ["point1", "point2", "point3"],
    "sentiment": "positive|negative|neutral|mixed",
    "topics": ["topic1", "topic2", "topic3"],
    "summary": "2-3 sentence summary of the main discussion",
    "engagement_score": 1-10
}}

Focus on:
1. Key insights about AI agents, their capabilities, limitations, or use cases
2. User experiences and opinions
3. Technical discussions or concerns
4. Overall sentiment of the discussion
5. How engaging/valuable this discussion appears to be
"""

    def _create_discussion_summary_prompt(
        self, post_summaries: List[PostSummary]
    ) -> str:
        """Create a prompt for summarizing multiple related posts."""
        summaries_text = "\n\n".join(
            [
                f"POST: {summary.title}\n"
                f"Topics: {', '.join(summary.topics)}\n"
                f"Summary: {summary.summary}\n"
                f"Key Points: {', '.join(summary.key_points)}\n"
                f"Sentiment: {summary.sentiment}"
                for summary in post_summaries[:20]  # Limit to avoid token limits
            ]
        )

        return f"""
Analyze these Reddit post summaries about AI agents and create an overall discussion summary.

POST SUMMARIES:
{summaries_text}

Please provide a JSON response with the following structure:
{{
    "topic": "Main overarching topic",
    "key_insights": ["insight1", "insight2", "insight3"],
    "common_themes": ["theme1", "theme2", "theme3"],
    "sentiment_overview": "Description of overall sentiment trends"
}}

Focus on:
1. Identifying the main topic or trend being discussed
2. Key insights about AI agents from across all posts
3. Common themes, concerns, or interests
4. Overall sentiment patterns
5. Notable trends or emerging topics
"""

    def summarize_post(self, post: RedditPost) -> Optional[PostSummary]:
        """Summarize a single Reddit post using LLM."""
        try:
            prompt = self._create_post_summary_prompt(post)

            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI expert analyzing Reddit discussions about AI agents. Always respond with valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=1000,
            )

            content = response.choices[0].message.content

            # Parse the JSON response
            import json

            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from the response if it's wrapped in other text
                import re

                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    return None

            return PostSummary(
                original_post_id=post.id,
                title=post.title,
                key_points=result.get("key_points", []),
                sentiment=result.get("sentiment", "neutral"),
                topics=result.get("topics", []),
                summary=result.get("summary", ""),
                engagement_score=result.get("engagement_score", post.score // 10),
                url=post.permalink,
                subreddit=post.subreddit,
            )

        except Exception as e:
            print(f"Error summarizing post {post.id}: {e}")
            return None

    def summarize_posts(self, posts: List[RedditPost]) -> List[PostSummary]:
        """Summarize multiple Reddit posts."""
        summaries = []

        for i, post in enumerate(posts):
            print(f"Summarizing post {i + 1}/{len(posts)}: {post.title[:50]}...")
            summary = self.summarize_post(post)
            if summary:
                summaries.append(summary)

        return summaries

    def create_discussion_summary(
        self, post_summaries: List[PostSummary]
    ) -> Optional[DiscussionSummary]:
        """Create an overall summary of multiple post summaries."""
        if not post_summaries:
            return None

        try:
            prompt = self._create_discussion_summary_prompt(post_summaries)

            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI expert analyzing Reddit discussions about AI agents. Always respond with valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=1500,
            )

            content = response.choices[0].message.content

            # Parse the JSON response
            import json

            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                import re

                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    return None

            total_engagement = sum(
                summary.engagement_score for summary in post_summaries
            )

            return DiscussionSummary(
                topic=result.get("topic", "AI Agent Discussions"),
                key_insights=result.get("key_insights", []),
                common_themes=result.get("common_themes", []),
                sentiment_overview=result.get("sentiment_overview", ""),
                post_summaries=post_summaries,
                total_engagement=total_engagement,
            )

        except Exception as e:
            print(f"Error creating discussion summary: {e}")
            return None

    def analyze_trends(self, discussion_summaries: List[DiscussionSummary]) -> dict:
        """Analyze trends across multiple discussion summaries."""
        if not discussion_summaries:
            return {}

        # Aggregate themes
        all_themes = []
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}

        for discussion in discussion_summaries:
            all_themes.extend(discussion.common_themes)

            # Count sentiments from individual posts
            for post_summary in discussion.post_summaries:
                sentiment = post_summary.sentiment.lower()
                if sentiment in sentiment_counts:
                    sentiment_counts[sentiment] += 1

        # Count theme frequency
        from collections import Counter

        theme_counts = Counter(all_themes)

        return {
            "top_themes": theme_counts.most_common(10),
            "sentiment_distribution": sentiment_counts,
            "total_discussions": len(discussion_summaries),
            "total_posts": sum(len(d.post_summaries) for d in discussion_summaries),
            "average_engagement": sum(d.total_engagement for d in discussion_summaries)
            / len(discussion_summaries)
            if discussion_summaries
            else 0,
        }
