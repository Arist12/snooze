import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from openai import AsyncAzureOpenAI, AzureOpenAI

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
    score: int = 0  # Reddit post score (upvotes - downvotes)
    num_comments: int = 0  # Number of comments on the post
    is_relevant: bool = True  # Whether the post is relevant and worthwhile
    relevance_reason: str = ""  # Reason if not relevant
    created_utc: Optional[datetime] = None  # Post creation date


@dataclass
class DiscussionSummary:
    """Represents a summary of multiple related posts."""

    topic: str
    key_insights: List[str]
    common_themes: List[str]
    sentiment_overview: str
    post_summaries: List[PostSummary]
    total_engagement: int
    total_posts_analyzed: int = 0  # Total number of relevant posts included


class LLMSummarizer:
    """Uses Azure OpenAI to summarize Reddit discussions about AI agents."""

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        deployment: str,
        api_version: str = "2024-12-01-preview",
        use_async: bool = True,
    ):
        """Initialize the LLM summarizer with Azure OpenAI credentials."""
        self.use_async = use_async
        if use_async:
            self.async_client = AsyncAzureOpenAI(
                api_key=api_key,
                azure_endpoint=endpoint,
                api_version=api_version,
            )
        else:
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
Analyze this Reddit post and determine if it's a substantive discussion about AI coding agents/tools.

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
    "is_relevant": true|false,
    "relevance_reason": "Brief explanation if not relevant",
    "key_points": ["point1", "point2", "point3"],
    "sentiment": "positive|negative|neutral|mixed",
    "topics": ["topic1", "topic2", "topic3"],
    "summary": "2-3 sentence summary of the main discussion",
    "engagement_score": 1-10
}}

STRICT RELEVANCE CRITERIA - Set "is_relevant" to FALSE if the post is:
❌ Subreddit rules, guidelines, or meta announcements
❌ Moderator posts about community features or policies
❌ Off-topic discussions not about AI coding tools
❌ Empty posts, memes, or low-effort content
❌ General AI discussions without coding/development focus
❌ Posts about non-coding AI applications (art, writing, etc.)
❌ Technical support for non-AI tools
❌ Job postings or recruitment

✅ Set "is_relevant" to TRUE only if the post contains:
✅ Discussions about AI coding assistants (Claude Code, Copilot, Cursor, etc.)
✅ User experiences with AI development tools
✅ Technical comparisons of AI coding platforms
✅ Workflows, tips, or best practices for AI-assisted coding
✅ Problems, limitations, or improvements for coding AI
✅ Code generation, debugging, or refactoring with AI
✅ AI agent behavior in software development contexts

Focus on CODING and DEVELOPMENT discussions only. Exclude all meta/administrative content.
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

    async def _summarize_post_async(
        self, post: RedditPost, semaphore: asyncio.Semaphore
    ) -> Optional[PostSummary]:
        """Asynchronously summarize a single Reddit post using LLM with rate limiting."""
        async with semaphore:
            try:
                prompt = self._create_post_summary_prompt(post)

                # Add retry logic for rate limits
                for attempt in range(3):
                    try:
                        response = await self.async_client.chat.completions.create(
                            model=self.deployment,
                            messages=[
                                {
                                    "role": "system",
                                    "content": "You are an AI expert analyzing Reddit discussions about AI agents. Always respond with valid JSON.",
                                },
                                {"role": "user", "content": prompt},
                            ],
                            max_completion_tokens=16384,
                        )
                        break
                    except Exception as e:
                        if "rate_limit" in str(e).lower() or "429" in str(e):
                            wait_time = 2**attempt  # Exponential backoff
                            print(
                                f"Rate limit hit for post {post.id}, waiting {wait_time}s..."
                            )
                            await asyncio.sleep(wait_time)
                            if attempt == 2:  # Last attempt
                                raise
                        else:
                            raise

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

                # Check relevance first
                is_relevant = result.get("is_relevant", True)
                if not is_relevant:
                    print(
                        f"Skipping irrelevant post {post.id}: {result.get('relevance_reason', 'Not relevant')}"
                    )
                    # Still create a PostSummary for caching, but mark as not relevant
                    return PostSummary(
                        original_post_id=post.id,
                        title=post.title,
                        key_points=[],
                        sentiment="neutral",
                        topics=[],
                        summary="",
                        engagement_score=0,
                        url=post.permalink,
                        subreddit=post.subreddit,
                        score=post.score,
                        num_comments=post.num_comments,
                        is_relevant=False,
                        relevance_reason=result.get("relevance_reason", "Not relevant"),
                        created_utc=post.created_utc,
                    )

                # Limit topics to top 3
                topics = result.get("topics", [])[:3]

                return PostSummary(
                    original_post_id=post.id,
                    title=post.title,
                    key_points=result.get("key_points", []),
                    sentiment=result.get("sentiment", "neutral"),
                    topics=topics,
                    summary=result.get("summary", ""),
                    engagement_score=result.get("engagement_score", post.score // 10),
                    url=post.permalink,
                    subreddit=post.subreddit,
                    score=post.score,
                    num_comments=post.num_comments,
                    is_relevant=is_relevant,
                    relevance_reason=result.get("relevance_reason", ""),
                    created_utc=post.created_utc,
                )

            except Exception as e:
                print(f"Error summarizing post {post.id}: {e}")
                return None

    def summarize_post(self, post: RedditPost) -> Optional[PostSummary]:
        """Summarize a single Reddit post using LLM."""
        if self.use_async:
            # Use asyncio.run() for proper event loop management
            return asyncio.run(self._run_single_post_async(post))

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
                max_completion_tokens=16384,
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

            # Check relevance first
            is_relevant = result.get("is_relevant", True)
            if not is_relevant:
                print(
                    f"Skipping irrelevant post {post.id}: {result.get('relevance_reason', 'Not relevant')}"
                )
                # Still create a PostSummary for caching, but mark as not relevant
                return PostSummary(
                    original_post_id=post.id,
                    title=post.title,
                    key_points=[],
                    sentiment="neutral",
                    topics=[],
                    summary="",
                    engagement_score=0,
                    url=post.permalink,
                    subreddit=post.subreddit,
                    score=post.score,
                    num_comments=post.num_comments,
                    is_relevant=False,
                    relevance_reason=result.get("relevance_reason", "Not relevant"),
                    created_utc=post.created_utc,
                )

            # Limit topics to top 3
            topics = result.get("topics", [])[:3]

            return PostSummary(
                original_post_id=post.id,
                title=post.title,
                key_points=result.get("key_points", []),
                sentiment=result.get("sentiment", "neutral"),
                topics=topics,
                summary=result.get("summary", ""),
                engagement_score=result.get("engagement_score", post.score // 10),
                url=post.permalink,
                subreddit=post.subreddit,
                score=post.score,
                num_comments=post.num_comments,
                is_relevant=is_relevant,
                relevance_reason=result.get("relevance_reason", ""),
                created_utc=post.created_utc,
            )

        except Exception as e:
            print(f"Error summarizing post {post.id}: {e}")
            return None

    async def summarize_posts_async(
        self, posts: List[RedditPost], max_concurrent: int = 5, callback=None
    ) -> List[PostSummary]:
        """Asynchronously summarize multiple Reddit posts with rate limiting."""
        if not self.use_async:
            raise ValueError(
                "Async client not initialized. Set use_async=True in constructor."
            )

        summaries = []
        semaphore = asyncio.Semaphore(max_concurrent)
        total_processed = 0
        relevant_count = 0

        async def process_post_with_callback(i, post):
            nonlocal total_processed, relevant_count
            print(f"Processing post {i + 1}/{len(posts)}: {post.title[:50]}...")
            summary = await self._summarize_post_async(post, semaphore)
            total_processed += 1

            if summary:
                summaries.append(summary)
                if summary.is_relevant:
                    relevant_count += 1
                    print(
                        f"✅ Relevant post {relevant_count} ({total_processed}/{len(posts)}): {post.title[:50]}"
                    )
                    if callback:
                        await callback(
                            summary
                        )  # Real-time callback for immediate rendering
                else:
                    print(
                        f"❌ Filtered out post {total_processed}/{len(posts)}: {post.title[:50]} (not relevant)"
                    )
            else:
                print(
                    f"❌ Error processing post {total_processed}/{len(posts)}: {post.title[:50]} (processing failed)"
                )

            return summary

        # Process all posts concurrently
        tasks = [process_post_with_callback(i, post) for i, post in enumerate(posts)]
        await asyncio.gather(*tasks, return_exceptions=True)

        print(
            f"\n📊 Processing complete: {relevant_count}/{total_processed} posts were relevant and included"
        )
        return summaries

    def summarize_posts(self, posts: List[RedditPost]) -> List[PostSummary]:
        """Summarize multiple Reddit posts."""
        if self.use_async:
            # Use asyncio.run() for proper event loop management
            return asyncio.run(self._run_posts_async(posts))

        summaries = []
        relevant_count = 0
        for i, post in enumerate(posts):
            print(f"Processing post {i + 1}/{len(posts)}: {post.title[:50]}...")
            summary = self.summarize_post(post)
            if summary:
                summaries.append(summary)
                if summary.is_relevant:
                    relevant_count += 1
                    print(f"✅ Relevant post {relevant_count}: {post.title[:50]}")
                else:
                    print(f"❌ Filtered out post: {post.title[:50]} (not relevant)")
            else:
                print(f"❌ Error processing post: {post.title[:50]} (processing failed)")

        print(
            f"\n📊 Processing complete: {relevant_count}/{len(posts)} posts were relevant and included"
        )
        return summaries

    async def _create_discussion_summary_async(
        self, post_summaries: List[PostSummary]
    ) -> Optional[DiscussionSummary]:
        """Asynchronously create an overall summary of multiple post summaries."""
        if not post_summaries:
            return None

        try:
            prompt = self._create_discussion_summary_prompt(post_summaries)

            response = await self.async_client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI expert analyzing Reddit discussions about AI agents. Always respond with valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=16384,
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
                total_posts_analyzed=len(post_summaries),
            )

        except Exception as e:
            print(f"Error creating discussion summary: {e}")
            return None

    def create_discussion_summary(
        self, post_summaries: List[PostSummary]
    ) -> Optional[DiscussionSummary]:
        """Create an overall summary of multiple post summaries."""
        if not post_summaries:
            return None

        if self.use_async:
            # Use asyncio.run() for proper event loop management
            return asyncio.run(self._run_discussion_async(post_summaries))

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
                max_completion_tokens=16384,
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
                total_posts_analyzed=len(post_summaries),
            )

        except Exception as e:
            print(f"Error creating discussion summary: {e}")
            return None

    async def _run_single_post_async(self, post: RedditPost) -> Optional[PostSummary]:
        """Helper method to run single post analysis with fresh client if needed."""
        self._ensure_async_client()
        semaphore = asyncio.Semaphore(5)
        return await self._summarize_post_async(post, semaphore)

    async def _run_posts_async(self, posts: List[RedditPost]) -> List[PostSummary]:
        """Helper method to run multiple posts analysis with fresh client if needed."""
        self._ensure_async_client()
        return await self.summarize_posts_async(posts)

    async def _run_discussion_async(self, post_summaries: List[PostSummary]) -> Optional[DiscussionSummary]:
        """Helper method to run discussion summary with fresh client if needed."""
        self._ensure_async_client()
        return await self._create_discussion_summary_async(post_summaries)

    def _ensure_async_client(self):
        """Ensure async client is available and valid."""
        if not hasattr(self, 'async_client') or self.async_client is None:
            import os
            from openai import AsyncAzureOpenAI

            self.async_client = AsyncAzureOpenAI(
                api_key=os.getenv("AZURE_API_KEY"),
                azure_endpoint=os.getenv("AZURE_ENDPOINT"),
                api_version="2024-12-01-preview",
            )

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
