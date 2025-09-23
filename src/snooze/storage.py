#!/usr/bin/env python3
"""Local storage utilities for caching Reddit data and LLM summaries."""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .crawler import RedditPost
from .summarizer import DiscussionSummary, PostSummary


class DataStorage:
    """Handles local storage and caching of Reddit posts and LLM summaries."""

    def __init__(self, data_dir: str = "data"):
        """Initialize storage with data directory."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Create subdirectories
        self.posts_dir = self.data_dir / "posts"
        self.summaries_dir = self.data_dir / "summaries"
        self.discussions_dir = self.data_dir / "discussions"
        self.post_summaries_dir = self.data_dir / "post_summaries"  # Individual post summaries

        for directory in [self.posts_dir, self.summaries_dir, self.discussions_dir, self.post_summaries_dir]:
            directory.mkdir(exist_ok=True)

    def _generate_cache_key(self, data: str) -> str:
        """Generate a cache key from data string."""
        return hashlib.md5(data.encode()).hexdigest()

    def _is_cache_valid(self, filepath: Path, max_age_hours: int = 24) -> bool:
        """Check if cached file is still valid based on age."""
        if not filepath.exists():
            return False

        file_time = datetime.fromtimestamp(filepath.stat().st_mtime)
        return datetime.now() - file_time < timedelta(hours=max_age_hours)

    def save_posts(self, posts: List[RedditPost], cache_key: str) -> None:
        """Save Reddit posts to local storage."""
        filepath = self.posts_dir / f"{cache_key}.json"

        posts_data = {
            "timestamp": datetime.now().isoformat(),
            "posts": [
                {
                    "id": post.id,
                    "title": post.title,
                    "body": post.body,
                    "author": post.author,
                    "score": post.score,
                    "num_comments": post.num_comments,
                    "created_utc": post.created_utc.isoformat(),
                    "url": post.url,
                    "subreddit": post.subreddit,
                    "permalink": post.permalink,
                    "comments": post.comments,
                }
                for post in posts
            ],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(posts_data, f, indent=2, ensure_ascii=False)

    def load_posts(
        self, cache_key: str, max_age_hours: int = 24
    ) -> Optional[List[RedditPost]]:
        """Load Reddit posts from local storage if cache is valid."""
        filepath = self.posts_dir / f"{cache_key}.json"

        if not self._is_cache_valid(filepath, max_age_hours):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            posts = []
            for post_data in data["posts"]:
                post = RedditPost(
                    id=post_data["id"],
                    title=post_data["title"],
                    body=post_data["body"],
                    author=post_data["author"],
                    score=post_data["score"],
                    num_comments=post_data["num_comments"],
                    created_utc=datetime.fromisoformat(post_data["created_utc"]),
                    url=post_data["url"],
                    subreddit=post_data["subreddit"],
                    permalink=post_data["permalink"],
                    comments=post_data["comments"],
                )
                posts.append(post)

            return posts

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error loading cached posts: {e}")
            return None

    def save_summaries(self, summaries: List[PostSummary], cache_key: str) -> None:
        """Save post summaries to local storage."""
        filepath = self.summaries_dir / f"{cache_key}.json"

        summaries_data = {
            "timestamp": datetime.now().isoformat(),
            "summaries": [
                {
                    "original_post_id": summary.original_post_id,
                    "title": summary.title,
                    "key_points": summary.key_points,
                    "sentiment": summary.sentiment,
                    "topics": summary.topics,
                    "summary": summary.summary,
                    "engagement_score": summary.engagement_score,
                    "url": summary.url,
                    "subreddit": summary.subreddit,
                }
                for summary in summaries
            ],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(summaries_data, f, indent=2, ensure_ascii=False)

    def load_summaries(
        self, cache_key: str, max_age_hours: int = 24
    ) -> Optional[List[PostSummary]]:
        """Load post summaries from local storage if cache is valid."""
        filepath = self.summaries_dir / f"{cache_key}.json"

        if not self._is_cache_valid(filepath, max_age_hours):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            summaries = []
            for summary_data in data["summaries"]:
                summary = PostSummary(
                    original_post_id=summary_data["original_post_id"],
                    title=summary_data["title"],
                    key_points=summary_data["key_points"],
                    sentiment=summary_data["sentiment"],
                    topics=summary_data["topics"],
                    summary=summary_data["summary"],
                    engagement_score=summary_data["engagement_score"],
                    url=summary_data["url"],
                    subreddit=summary_data["subreddit"],
                )
                summaries.append(summary)

            return summaries

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error loading cached summaries: {e}")
            return None

    def save_discussion(self, discussion: DiscussionSummary, cache_key: str) -> None:
        """Save discussion summary to local storage."""
        filepath = self.discussions_dir / f"{cache_key}.json"

        discussion_data = {
            "timestamp": datetime.now().isoformat(),
            "discussion": {
                "topic": discussion.topic,
                "key_insights": discussion.key_insights,
                "common_themes": discussion.common_themes,
                "sentiment_overview": discussion.sentiment_overview,
                "total_engagement": discussion.total_engagement,
                "post_summaries": [
                    {
                        "original_post_id": ps.original_post_id,
                        "title": ps.title,
                        "key_points": ps.key_points,
                        "sentiment": ps.sentiment,
                        "topics": ps.topics,
                        "summary": ps.summary,
                        "engagement_score": ps.engagement_score,
                        "url": ps.url,
                        "subreddit": ps.subreddit,
                    }
                    for ps in discussion.post_summaries
                ],
            },
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(discussion_data, f, indent=2, ensure_ascii=False)

    def load_discussion(
        self, cache_key: str, max_age_hours: int = 24
    ) -> Optional[DiscussionSummary]:
        """Load discussion summary from local storage if cache is valid."""
        filepath = self.discussions_dir / f"{cache_key}.json"

        if not self._is_cache_valid(filepath, max_age_hours):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            discussion_data = data["discussion"]

            # Reconstruct post summaries
            post_summaries = []
            for ps_data in discussion_data["post_summaries"]:
                post_summary = PostSummary(
                    original_post_id=ps_data["original_post_id"],
                    title=ps_data["title"],
                    key_points=ps_data["key_points"],
                    sentiment=ps_data["sentiment"],
                    topics=ps_data["topics"],
                    summary=ps_data["summary"],
                    engagement_score=ps_data["engagement_score"],
                    url=ps_data["url"],
                    subreddit=ps_data["subreddit"],
                )
                post_summaries.append(post_summary)

            discussion = DiscussionSummary(
                topic=discussion_data["topic"],
                key_insights=discussion_data["key_insights"],
                common_themes=discussion_data["common_themes"],
                sentiment_overview=discussion_data["sentiment_overview"],
                post_summaries=post_summaries,
                total_engagement=discussion_data["total_engagement"],
            )

            return discussion

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error loading cached discussion: {e}")
            return None

    def generate_posts_cache_key(self, subreddits: List[str], limit: int) -> str:
        """Generate cache key for posts based on subreddits and limit."""
        cache_string = f"posts_{'_'.join(sorted(subreddits))}_{limit}"
        return self._generate_cache_key(cache_string)

    def generate_summaries_cache_key(self, posts: List[RedditPost]) -> str:
        """Generate cache key for summaries based on post IDs."""
        post_ids = sorted([post.id for post in posts])
        cache_string = f"summaries_{'_'.join(post_ids)}"
        return self._generate_cache_key(cache_string)

    def generate_discussion_cache_key(self, summaries: List[PostSummary]) -> str:
        """Generate cache key for discussion based on summary IDs."""
        summary_ids = sorted([summary.original_post_id for summary in summaries])
        cache_string = f"discussion_{'_'.join(summary_ids)}"
        return self._generate_cache_key(cache_string)

    def list_cached_files(self) -> Dict[str, List[str]]:
        """List all cached files by category."""
        return {
            "posts": [f.stem for f in self.posts_dir.glob("*.json")],
            "summaries": [f.stem for f in self.summaries_dir.glob("*.json")],
            "discussions": [f.stem for f in self.discussions_dir.glob("*.json")],
            "post_summaries": [f.stem for f in self.post_summaries_dir.glob("*.json")],
        }

    def clear_cache(
        self, category: Optional[str] = None, max_age_days: Optional[int] = None
    ) -> int:
        """Clear cached files. Returns number of files deleted."""
        deleted_count = 0

        directories = []
        if category is None:
            directories = [self.posts_dir, self.summaries_dir, self.discussions_dir, self.post_summaries_dir]
        elif category == "posts":
            directories = [self.posts_dir]
        elif category == "summaries":
            directories = [self.summaries_dir]
        elif category == "discussions":
            directories = [self.discussions_dir]
        elif category == "post_summaries":
            directories = [self.post_summaries_dir]

        for directory in directories:
            for filepath in directory.glob("*.json"):
                should_delete = False

                if max_age_days is None:
                    should_delete = True
                else:
                    file_time = datetime.fromtimestamp(filepath.stat().st_mtime)
                    if datetime.now() - file_time > timedelta(days=max_age_days):
                        should_delete = True

                if should_delete:
                    filepath.unlink()
                    deleted_count += 1

        return deleted_count

    def save_post_summary(self, post_summary: PostSummary) -> None:
        """Save individual post summary to enable post-level caching."""
        filepath = self.post_summaries_dir / f"{post_summary.original_post_id}.json"

        summary_data = {
            "timestamp": datetime.now().isoformat(),
            "original_post_id": post_summary.original_post_id,
            "title": post_summary.title,
            "key_points": post_summary.key_points,
            "sentiment": post_summary.sentiment,
            "topics": post_summary.topics,
            "summary": post_summary.summary,
            "engagement_score": post_summary.engagement_score,
            "url": post_summary.url,
            "subreddit": post_summary.subreddit,
            "score": post_summary.score,
            "num_comments": post_summary.num_comments,
            "is_relevant": post_summary.is_relevant,
            "relevance_reason": post_summary.relevance_reason,
            "created_utc": post_summary.created_utc.isoformat() if post_summary.created_utc else None,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)

    def load_post_summary(self, post_id: str, max_age_hours: int = 144) -> Optional[PostSummary]:
        """Load individual post summary if cache is valid."""
        filepath = self.post_summaries_dir / f"{post_id}.json"

        if not self._is_cache_valid(filepath, max_age_hours):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            created_utc = None
            if data.get("created_utc"):
                created_utc = datetime.fromisoformat(data["created_utc"])

            return PostSummary(
                original_post_id=data["original_post_id"],
                title=data["title"],
                key_points=data["key_points"],
                sentiment=data["sentiment"],
                topics=data["topics"],
                summary=data["summary"],
                engagement_score=data["engagement_score"],
                url=data["url"],
                subreddit=data["subreddit"],
                score=data.get("score", 0),
                num_comments=data.get("num_comments", 0),
                is_relevant=data.get("is_relevant", True),
                relevance_reason=data.get("relevance_reason", ""),
                created_utc=created_utc,
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error loading cached post summary for {post_id}: {e}")
            return None

    def load_summaries_with_post_cache(self, posts: List[RedditPost], max_age_hours: int = 144) -> List[PostSummary]:
        """Load summaries using post-level caching. Returns cached summaries and list of posts that need analysis."""
        cached_summaries = []

        for post in posts:
            cached_summary = self.load_post_summary(post.id, max_age_hours)
            if cached_summary:
                cached_summaries.append(cached_summary)

        return cached_summaries

    def get_posts_needing_analysis(self, posts: List[RedditPost], max_age_hours: int = 144) -> List[RedditPost]:
        """Get list of posts that don't have valid cached summaries."""
        posts_needing_analysis = []

        for post in posts:
            if not self.load_post_summary(post.id, max_age_hours):
                posts_needing_analysis.append(post)

        return posts_needing_analysis

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about cached data."""
        stats = {}

        for category, directory in [
            ("posts", self.posts_dir),
            ("summaries", self.summaries_dir),
            ("discussions", self.discussions_dir),
            ("post_summaries", self.post_summaries_dir),
        ]:
            files = list(directory.glob("*.json"))
            total_size = sum(f.stat().st_size for f in files)

            stats[category] = {
                "file_count": len(files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "files": [
                    {
                        "name": f.stem,
                        "size_kb": round(f.stat().st_size / 1024, 2),
                        "modified": datetime.fromtimestamp(
                            f.stat().st_mtime
                        ).isoformat(),
                    }
                    for f in files
                ],
            }

        return stats
