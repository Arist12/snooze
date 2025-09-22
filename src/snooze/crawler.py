import os
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, List, Optional

import praw
from praw.models import Comment, Submission


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
        """Initialize the Reddit crawler with PRAW credentials."""
        self.reddit = praw.Reddit(
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

    def _extract_comments(
        self, submission: Submission, max_comments: int = 50
    ) -> List[str]:
        """Extract top-level comments from a submission."""
        comments = []
        submission.comments.replace_more(limit=0)

        for comment in submission.comments[:max_comments]:
            if (
                isinstance(comment, Comment)
                and comment.body
                and comment.body != "[deleted]"
            ):
                comments.append(comment.body)

        return comments

    def _submission_to_post(
        self, submission: Submission, include_comments: bool = True
    ) -> RedditPost:
        """Convert a PRAW submission to a RedditPost."""
        comments = self._extract_comments(submission) if include_comments else []

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

    def search_subreddit(
        self,
        subreddit_name: str,
        search_query: str = "AI agent",
        sort: str = "relevance",
        time_filter: str = "month",
        limit: int = 100,
        include_comments: bool = True,
    ) -> Iterator[RedditPost]:
        """Search for posts in a specific subreddit."""
        subreddit = self.reddit.subreddit(subreddit_name)

        submissions = subreddit.search(
            search_query, sort=sort, time_filter=time_filter, limit=limit
        )

        for submission in submissions:
            yield self._submission_to_post(submission, include_comments)

    def get_coding_discussions(
        self,
        subreddit_names: Optional[List[str]] = None,
        limit_per_subreddit: int = 25,
        include_comments: bool = True,
        coding_keywords: Optional[List[str]] = None,
    ) -> Iterator[RedditPost]:
        """Get coding-related posts from specified subreddits."""
        if subreddit_names is None:
            subreddit_names = ["ClaudeCode", "codex", "GithubCopilot", "ChatGPTCoding"]

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

        for subreddit_name in subreddit_names:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)

                for submission in subreddit.hot(limit=limit_per_subreddit):
                    # Always include posts from these specific coding subreddits
                    # but also check for coding keywords to be more selective
                    text_to_check = f"{submission.title} {submission.selftext}".lower()

                    # For coding subreddits, be more inclusive but still filter out completely unrelated posts
                    is_coding_related = subreddit_name.lower() in [
                        "claudecode",
                        "codex",
                        "githubcopilot",
                        "chatgptcoding",
                    ] or any(
                        keyword.lower() in text_to_check for keyword in coding_keywords
                    )

                    if is_coding_related:
                        yield self._submission_to_post(submission, include_comments)

            except Exception as e:
                print(f"Error accessing r/{subreddit_name}: {e}")
                continue

    def get_all_coding_discussions(
        self,
        limit: int = 50,
        include_comments: bool = True,
    ) -> List[RedditPost]:
        """Get coding discussions from all target subreddits."""
        target_subreddits = ["ClaudeCode", "codex", "GithubCopilot", "ChatGPTCoding"]

        posts = list(
            self.get_coding_discussions(
                target_subreddits,
                limit_per_subreddit=limit // len(target_subreddits) + 5,
                include_comments=include_comments,
            )
        )

        # Sort by score and recency, prioritizing recent high-engagement posts
        posts.sort(key=lambda p: (p.score, p.created_utc), reverse=True)

        return posts[:limit]
