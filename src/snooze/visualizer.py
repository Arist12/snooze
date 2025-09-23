import asyncio
import os
from datetime import datetime
from typing import Optional
import json

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit

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
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        self.crawler = None
        self.summarizer = None
        self.storage = DataStorage()
        self._setup_routes()
        self._setup_socketio_events()

    def _get_templates_path(self) -> str:
        """Get the path to the templates directory."""
        return os.path.join(os.path.dirname(__file__), "templates")

    def _get_static_path(self) -> str:
        """Get the path to the static files directory."""
        return os.path.join(os.path.dirname(__file__), "static")

    def _setup_socketio_events(self):
        """Setup SocketIO event handlers."""

        @self.socketio.on('connect')
        def handle_connect():
            print(f"Client connected")
            emit('connected', {'status': 'Connected to Snooze server'})

        @self.socketio.on('disconnect')
        def handle_disconnect():
            print('Client disconnected')

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route("/")
        def index():
            """Main dashboard page."""
            return render_template("index.html")

        @self.app.route("/api/analyze", methods=["POST"])
        def analyze():
            """API endpoint to analyze Reddit discussions (legacy, synchronous)."""
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

                # Use post-level caching for efficient summary retrieval
                cached_summaries = self.storage.load_summaries_with_post_cache(posts, max_age_hours=144)
                posts_needing_analysis = self.storage.get_posts_needing_analysis(posts, max_age_hours=144)

                print(f"Found {len(cached_summaries)} cached summaries, {len(posts_needing_analysis)} posts need analysis")

                # Analyze only posts that don't have cached summaries
                new_summaries = []
                if posts_needing_analysis:
                    print(f"Analyzing {len(posts_needing_analysis)} new posts...")
                    new_summaries = self.summarizer.summarize_posts(posts_needing_analysis)

                    # Cache each new summary individually
                    for summary in new_summaries:
                        if summary:  # Only cache valid summaries
                            self.storage.save_post_summary(summary)

                # Combine cached and new summaries
                summaries = cached_summaries + new_summaries

                # Also save the combined summaries for backward compatibility
                if summaries:
                    summaries_cache_key = self.storage.generate_summaries_cache_key(posts)
                    self.storage.save_summaries(summaries, summaries_cache_key)

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
                    discussion_cache_key, max_age_hours=144
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
                        "cached_summary_count": len(cached_summaries),
                        "new_summary_count": len(new_summaries),
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

        @self.app.route("/api/analyze-async", methods=["POST"])
        def analyze_async():
            """API endpoint to start async analysis with real-time updates."""
            try:
                data = request.get_json()
                limit = data.get("limit", 20)
                subreddits = data.get(
                    "subreddits",
                    ["ClaudeCode", "codex", "GithubCopilot", "ChatGPTCoding"],
                )

                # Start async analysis in background
                self.socketio.start_background_task(
                    self._run_async_analysis, subreddits, limit
                )

                return jsonify({"success": True, "message": "Analysis started"})

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

    def _run_async_analysis(self, subreddits, limit):
        """Run async analysis with real-time updates via WebSocket."""
        try:
            # Use asyncio.run() for proper event loop management
            asyncio.run(self._async_analysis_process(subreddits, limit))
        except Exception as e:
            self.socketio.emit('error', {'message': str(e)})

    async def _async_analysis_process(self, subreddits, limit):
        """The actual async analysis process."""
        try:
            # Initialize components if not already done
            if not self.crawler:
                self.crawler = RedditCrawler.from_env()
            if not self.summarizer:
                self.summarizer = LLMSummarizer.from_env()

            self.socketio.emit('progress', {'stage': 'crawling', 'message': 'Crawling Reddit posts...'})

            # Generate cache keys
            posts_cache_key = self.storage.generate_posts_cache_key(subreddits, limit)

            # Try to load cached posts first
            posts = self.storage.load_posts(posts_cache_key, max_age_hours=6)
            if not posts:
                if self.crawler.use_async:
                    posts = await self.crawler.get_all_coding_discussions_async(limit=limit)
                else:
                    posts = self.crawler.get_all_coding_discussions(limit=limit)
                if posts:
                    self.storage.save_posts(posts, posts_cache_key)

            if not posts:
                self.socketio.emit('error', {'message': 'No posts found to analyze'})
                return

            self.socketio.emit('progress', {
                'stage': 'posts_ready',
                'message': f'Found {len(posts)} posts. Starting relevance analysis and summarization...',
                'post_count': len(posts)
            })

            # Use post-level caching for efficient summary retrieval
            cached_summaries = self.storage.load_summaries_with_post_cache(posts, max_age_hours=144)
            posts_needing_analysis = self.storage.get_posts_needing_analysis(posts, max_age_hours=144)

            self.socketio.emit('progress', {
                'stage': 'cache_check',
                'message': f'Found {len(cached_summaries)} cached summaries, {len(posts_needing_analysis)} posts need analysis'
            })

            # Immediately emit cached summaries for live rendering
            for cached_summary in cached_summaries:
                self.socketio.emit('post_summary_ready', {
                    'summary': self._serialize_post_summary(cached_summary),
                    'cached': True,
                    'progress': len(cached_summaries),
                    'total': len(posts),
                    'message': f'Loaded cached summary for: {cached_summary.title[:50]}...'
                })

            # Track all summaries for real-time updates
            all_summaries = cached_summaries.copy()

            # Analyze only posts that don't have cached summaries
            if posts_needing_analysis:
                async def progress_callback(summary):
                    # Save each summary as it's completed
                    if summary:
                        self.storage.save_post_summary(summary)
                        all_summaries.append(summary)

                        # Emit real-time update for new analysis
                        self.socketio.emit('post_summary_ready', {
                            'summary': self._serialize_post_summary(summary),
                            'cached': False,
                            'progress': len(all_summaries),
                            'total': len(posts),
                            'message': f'Analyzed: {summary.title[:50]}...'
                        })

                new_summaries = await self.summarizer.summarize_posts_async(
                    posts_needing_analysis,
                    callback=progress_callback
                )
            else:
                new_summaries = []

            # Final summary list
            summaries = all_summaries

            # Emit completion status
            filtered_count = len(posts) - len(summaries)
            self.socketio.emit('progress', {
                'stage': 'analysis_complete',
                'message': f'Analysis complete: {len(summaries)} relevant posts, {filtered_count} filtered out',
                'relevant_count': len(summaries),
                'filtered_count': filtered_count,
                'cached_count': len(cached_summaries),
                'new_count': len(new_summaries)
            })

            # Save combined summaries for backward compatibility
            if summaries:
                summaries_cache_key = self.storage.generate_summaries_cache_key(posts)
                self.storage.save_summaries(summaries, summaries_cache_key)

            if not summaries:
                self.socketio.emit('error', {'message': 'Failed to generate summaries'})
                return

            self.socketio.emit('progress', {'stage': 'creating_discussion', 'message': 'Creating discussion summary...'})

            # Generate cache key for discussion
            discussion_cache_key = self.storage.generate_discussion_cache_key(summaries)
            discussion = self.storage.load_discussion(discussion_cache_key, max_age_hours=144)

            if not discussion:
                if self.summarizer.use_async:
                    discussion = await self.summarizer._create_discussion_summary_async(summaries)
                else:
                    discussion = self.summarizer.create_discussion_summary(summaries)
                if discussion:
                    self.storage.save_discussion(discussion, discussion_cache_key)

            if discussion:
                self.socketio.emit('analysis_complete', {
                    'success': True,
                    'discussion': self._serialize_discussion(discussion),
                    'post_count': len(posts),
                    'summary_count': len(summaries)
                })
            else:
                self.socketio.emit('error', {'message': 'Failed to create discussion summary'})

        except Exception as e:
            print(f"Error in async analysis: {e}")
            self.socketio.emit('error', {'message': f'Analysis failed: {str(e)}'})

    def _serialize_discussion(self, discussion: DiscussionSummary) -> dict:
        """Convert DiscussionSummary to JSON-serializable dict."""
        return {
            "topic": discussion.topic,
            "key_insights": discussion.key_insights,
            "common_themes": discussion.common_themes,
            "sentiment_overview": discussion.sentiment_overview,
            "total_engagement": discussion.total_engagement,
            "total_posts_analyzed": discussion.total_posts_analyzed,
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
            "score": post_summary.score,
            "num_comments": post_summary.num_comments,
            "is_relevant": post_summary.is_relevant,
            "relevance_reason": post_summary.relevance_reason,
            "created_utc": post_summary.created_utc.isoformat() if post_summary.created_utc else None,
        }

    def run(self, host: str = "127.0.0.1", port: int = 8080, debug: bool = True):
        """Run the Flask-SocketIO development server."""
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
            self.socketio.run(self.app, host=host, port=port, debug=debug)
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
