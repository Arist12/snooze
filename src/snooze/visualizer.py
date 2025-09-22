import os
from datetime import datetime
from typing import Optional

from flask import Flask, jsonify, render_template, request

from .crawler import RedditCrawler
from .storage import DataStorage
from .summarizer import DiscussionSummary, LLMSummarizer, PostSummary


class SnoozeVisualizer:
    """Web visualizer for Reddit AI agent discussions."""

    def __init__(
        self, template_folder: Optional[str] = None, static_folder: Optional[str] = None
    ):
        """Initialize the Flask app for visualization."""
        self.app = Flask(
            __name__,
            template_folder=template_folder or self._get_templates_path(),
            static_folder=static_folder or self._get_static_path(),
        )
        self.crawler = None
        self.summarizer = None
        self.storage = DataStorage()
        self._setup_routes()

    def _get_templates_path(self) -> str:
        """Get the path to the templates directory."""
        return os.path.join(os.path.dirname(__file__), "templates")

    def _get_static_path(self) -> str:
        """Get the path to the static files directory."""
        return os.path.join(os.path.dirname(__file__), "static")

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route("/")
        def index():
            """Main dashboard page."""
            return render_template("index.html")

        @self.app.route("/api/analyze", methods=["POST"])
        def analyze():
            """API endpoint to analyze Reddit discussions."""
            try:
                data = request.get_json()
                limit = data.get("limit", 20)
                subreddits = data.get(
                    "subreddits",
                    ["ClaudeCode", "codex", "GithubCopilot", "ChatGPTCoding"],
                )

                # Initialize components if not already done
                if not self.crawler:
                    self.crawler = RedditCrawler.from_env()
                if not self.summarizer:
                    self.summarizer = LLMSummarizer.from_env()

                # Generate cache keys
                posts_cache_key = self.storage.generate_posts_cache_key(
                    subreddits, limit
                )

                # Try to load cached posts first
                posts = self.storage.load_posts(posts_cache_key, max_age_hours=6)
                if not posts:
                    print("Crawling new posts from Reddit...")
                    # Crawl posts
                    posts = self.crawler.get_all_coding_discussions(limit=limit)
                    if posts:
                        self.storage.save_posts(posts, posts_cache_key)
                else:
                    print(f"Using cached posts ({len(posts)} posts)")

                if not posts:
                    return jsonify(
                        {"success": False, "error": "No posts found to analyze"}
                    ), 404

                # Generate cache key for summaries
                summaries_cache_key = self.storage.generate_summaries_cache_key(posts)

                # Try to load cached summaries
                summaries = self.storage.load_summaries(
                    summaries_cache_key, max_age_hours=24
                )
                if not summaries:
                    print("Generating new summaries with LLM...")
                    # Summarize posts
                    summaries = self.summarizer.summarize_posts(posts)
                    if summaries:
                        self.storage.save_summaries(summaries, summaries_cache_key)
                else:
                    print(f"Using cached summaries ({len(summaries)} summaries)")

                if not summaries:
                    return jsonify(
                        {"success": False, "error": "Failed to generate summaries"}
                    ), 500

                # Generate cache key for discussion
                discussion_cache_key = self.storage.generate_discussion_cache_key(
                    summaries
                )

                # Try to load cached discussion
                discussion = self.storage.load_discussion(
                    discussion_cache_key, max_age_hours=24
                )
                if not discussion:
                    print("Creating new discussion summary...")
                    # Create discussion summary
                    discussion = self.summarizer.create_discussion_summary(summaries)
                    if discussion:
                        self.storage.save_discussion(discussion, discussion_cache_key)
                else:
                    print("Using cached discussion summary")

                return jsonify(
                    {
                        "success": True,
                        "discussion": self._serialize_discussion(discussion)
                        if discussion
                        else None,
                        "post_count": len(posts),
                        "summary_count": len(summaries),
                        "cached": {
                            "posts": posts_cache_key
                            in [f for f in self.storage.list_cached_files()["posts"]],
                            "summaries": summaries_cache_key
                            in [
                                f for f in self.storage.list_cached_files()["summaries"]
                            ],
                            "discussion": discussion_cache_key
                            in [
                                f
                                for f in self.storage.list_cached_files()["discussions"]
                            ],
                        },
                    }
                )

            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/posts")
        def get_posts():
            """Get latest analyzed posts."""
            # This would typically load from a database or cache
            # For now, return mock data
            return jsonify(
                {
                    "posts": [],
                    "message": "No posts analyzed yet. Use the analyze endpoint first.",
                }
            )

        @self.app.route("/api/trends")
        def get_trends():
            """Get trending topics and themes."""
            # This would analyze historical data
            return jsonify(
                {
                    "trends": {
                        "top_themes": [],
                        "sentiment_distribution": {},
                        "message": "No trend data available yet.",
                    }
                }
            )

        @self.app.route("/api/cache/stats")
        def get_cache_stats():
            """Get cache statistics."""
            stats = self.storage.get_cache_stats()
            return jsonify({"success": True, "stats": stats})

        @self.app.route("/api/cache/clear", methods=["POST"])
        def clear_cache():
            """Clear cache files."""
            data = request.get_json() or {}
            category = data.get("category")  # None, "posts", "summaries", "discussions"
            max_age_days = data.get("max_age_days")

            deleted_count = self.storage.clear_cache(category, max_age_days)
            return jsonify(
                {
                    "success": True,
                    "deleted_count": deleted_count,
                    "message": f"Deleted {deleted_count} cached files",
                }
            )

    def _serialize_discussion(self, discussion: DiscussionSummary) -> dict:
        """Convert DiscussionSummary to JSON-serializable dict."""
        return {
            "topic": discussion.topic,
            "key_insights": discussion.key_insights,
            "common_themes": discussion.common_themes,
            "sentiment_overview": discussion.sentiment_overview,
            "total_engagement": discussion.total_engagement,
            "post_summaries": [
                self._serialize_post_summary(ps) for ps in discussion.post_summaries
            ],
            "analysis_time": datetime.now().isoformat(),
        }

    def _serialize_post_summary(self, post_summary: PostSummary) -> dict:
        """Convert PostSummary to JSON-serializable dict."""
        return {
            "id": post_summary.original_post_id,
            "title": post_summary.title,
            "key_points": post_summary.key_points,
            "sentiment": post_summary.sentiment,
            "topics": post_summary.topics,
            "summary": post_summary.summary,
            "engagement_score": post_summary.engagement_score,
            "url": post_summary.url,
            "subreddit": post_summary.subreddit,
        }

    def run(self, host: str = "127.0.0.1", port: int = 8080, debug: bool = True):
        """Run the Flask development server."""
        import socket

        # Check if port is available
        def is_port_available(host, port):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((host, port))
                    return True
            except OSError:
                return False

        # Find an available port if the default is taken
        original_port = port
        while not is_port_available(host, port) and port < original_port + 100:
            port += 1

        if port != original_port:
            print(f"Port {original_port} is in use, using port {port} instead")

        if not is_port_available(host, port):
            print(
                f"Error: Could not find an available port starting from {original_port}"
            )
            print("Try specifying a different port with --port <port_number>")
            return

        print(f"Starting Snooze visualizer at http://{host}:{port}")
        try:
            self.app.run(host=host, port=port, debug=debug)
        except OSError as e:
            if "Address already in use" in str(e):
                print(
                    f"Error: Port {port} is still in use. Try a different port with --port <port_number>"
                )
                print(
                    "On macOS, you may need to disable AirPlay Receiver in System Preferences > General > AirDrop & Handoff"
                )
            else:
                print(f"Error starting server: {e}")


def create_app() -> Flask:
    """Factory function to create Flask app."""
    visualizer = SnoozeVisualizer()
    return visualizer.app


if __name__ == "__main__":
    visualizer = SnoozeVisualizer()
    visualizer.run()
