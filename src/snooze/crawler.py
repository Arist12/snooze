import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import asyncpraw


@dataclass
class RedditPost:
    """Represents a Reddit post with relevant metadata."""

    id: str
    title: str
    body: str
    author: str
    score: int
    num_comments: int
    created_utc: datetime
    url: str
    subreddit: str
    permalink: str
    comments: List[str]


class RedditCrawler:
    """Crawls Reddit for AI agent-related discussions."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_agent: str = "Snooze/0.1.0 by Arist12",
    ):
        """Initialize the Reddit crawler with AsyncPRAW credentials."""
        self.async_reddit = asyncpraw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )

    @classmethod
    def from_env(cls) -> "RedditCrawler":
        """Create a RedditCrawler instance using environment variables."""
        return cls(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        )

    async def _extract_comments_async(
        self, submission, max_comments: int = 50
    ) -> List[str]:
        """Extract top-level comments from an async submission."""
        comments = []
        try:
            # Check if submission has comments attribute and it's not None
            if not hasattr(submission, "comments") or submission.comments is None:
                return comments

            await submission.comments.replace_more(limit=None)

            # Process comments with proper iteration and counting
            comment_count = 0
            async for comment in submission.comments:
                if comment_count >= max_comments:
                    break

                if (
                    hasattr(comment, "body")
                    and comment.body
                    and comment.body != "[deleted]"
                    and comment.body is not None
                ):
                    comments.append(comment.body)
                    comment_count += 1

        except (AttributeError, TypeError):
            # print(f"Error extracting comments (submission issue): {e}")
            pass
        except Exception:
            # print(f"Error extracting comments: {e}")
            pass
        return comments

    async def _submission_to_post_async(
        self, submission, include_comments: bool = True
    ) -> RedditPost:
        """Convert an AsyncPRAW submission to a RedditPost."""
        comments = (
            await self._extract_comments_async(submission) if include_comments else []
        )

        return RedditPost(
            id=submission.id,
            title=submission.title,
            body=submission.selftext or "",
            author=str(submission.author) if submission.author else "[deleted]",
            score=submission.score,
            num_comments=submission.num_comments,
            created_utc=datetime.fromtimestamp(submission.created_utc),
            url=submission.url,
            subreddit=str(submission.subreddit),
            permalink=f"https://reddit.com{submission.permalink}",
            comments=comments,
        )

    async def get_coding_discussions_async(
        self,
        subreddit_names: Optional[List[str]] = None,
        limit_per_subreddit: int = 25,
        include_comments: bool = True,
        coding_keywords: Optional[List[str]] = None,
    ) -> List[RedditPost]:
        """Get coding-related posts from specified subreddits asynchronously."""

        if subreddit_names is None:
            subreddit_names = [
                "vibecoding",
                "ClaudeCode",
                "codex",
                "GithubCopilot",
                "ChatGPTCoding",
                "cursor",
            ]

        if coding_keywords is None:
            coding_keywords = [
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
                "github copilot",
                "claude code",
                "chatgpt coding",
                "cursor ai",
                "autocomplete",
                "intellisense",
                "pair programming",
                "code generation",
            ]

        all_posts = []

        for subreddit_name in subreddit_names:
            try:
                subreddit = await self.async_reddit.subreddit(subreddit_name)
                post_count = 0

                async for submission in subreddit.hot(
                    limit=limit_per_subreddit * 2
                ):  # Get more to filter
                    if post_count >= limit_per_subreddit:
                        break

                    # Always include posts from these specific coding subreddits
                    # but also check for coding keywords to be more selective
                    text_to_check = f"{submission.title} {submission.selftext}".lower()

                    # For coding subreddits, be more inclusive but still filter out completely unrelated posts
                    is_coding_related = subreddit_name.lower() in [
                        "claudecode",
                        "codex",
                        "githubcopilot",
                        "chatgptcoding",
                        "cursor",
                    ] or any(
                        keyword.lower() in text_to_check for keyword in coding_keywords
                    )

                    if is_coding_related:
                        post = await self._submission_to_post_async(
                            submission, include_comments
                        )
                        all_posts.append(post)
                        post_count += 1

            except Exception as e:
                print(f"Error accessing r/{subreddit_name}: {e}")
                continue

        return all_posts

    async def get_all_coding_discussions_async(
        self,
        limit: int = 50,
        include_comments: bool = True,
    ) -> List[RedditPost]:
        """Get coding discussions from all target subreddits asynchronously."""
        target_subreddits = [
            "vibecoding",
            "ClaudeCode",
            "codex",
            "GithubCopilot",
            "ChatGPTCoding",
            "cursor",
        ]

        posts = await self.get_coding_discussions_async(
            target_subreddits,
            limit_per_subreddit=limit // len(target_subreddits) + 5,
            include_comments=include_comments,
        )

        # Sort by score and recency, prioritizing recent high-engagement posts
        posts.sort(key=lambda p: (p.score, p.created_utc), reverse=True)

        return posts[:limit]
