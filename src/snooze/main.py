#!/usr/bin/env python3
"""Main entry point for the Snooze application."""

import argparse
import os
import sys

import dotenv

from .crawler import RedditCrawler
from .summarizer import LLMSummarizer
from .visualizer import SnoozeVisualizer


def main():
    """Main entry point for the Snooze CLI."""
    dotenv.load_dotenv()

    parser = argparse.ArgumentParser(
        description="Snooze - Reddit AI Agent Discussion Analyzer"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Web server command
    web_parser = subparsers.add_parser("web", help="Start the web interface")
    web_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    web_parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    web_parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze Reddit discussions")
    analyze_parser.add_argument(
        "--subreddits",
        nargs="+",
        default=["artificial", "MachineLearning", "ChatGPT", "OpenAI"],
        help="Subreddits to analyze",
    )
    analyze_parser.add_argument(
        "--limit", type=int, default=20, help="Number of posts to analyze"
    )
    analyze_parser.add_argument(
        "--output", help="Output file to save results (JSON format)"
    )

    # Crawl command
    crawl_parser = subparsers.add_parser(
        "crawl", help="Crawl Reddit posts without analysis"
    )
    crawl_parser.add_argument(
        "--subreddits",
        nargs="+",
        default=["artificial", "MachineLearning", "ChatGPT"],
        help="Subreddits to crawl",
    )
    crawl_parser.add_argument(
        "--limit", type=int, default=50, help="Number of posts to crawl"
    )
    crawl_parser.add_argument("--search", help="Search query for posts")

    # Check ports command
    ports_parser = subparsers.add_parser("check-ports", help="Check available ports")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Check environment variables
    required_env_vars = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"]
    if args.command in ["analyze", "web"]:
        required_env_vars.extend(
            ["AZURE_API_KEY", "AZURE_ENDPOINT", "AZURE_DEPLOYMENT"]
        )

    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(
            f"Error: Missing required environment variables: {', '.join(missing_vars)}"
        )
        print("Please set these in your .env file or environment.")
        sys.exit(1)

    try:
        if args.command == "web":
            run_web_interface(args)
        elif args.command == "analyze":
            run_analysis(args)
        elif args.command == "crawl":
            run_crawl(args)
        elif args.command == "check-ports":
            run_check_ports()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def run_web_interface(args):
    """Run the web interface."""
    print(f"Starting Snooze web interface at http://{args.host}:{args.port}")
    visualizer = SnoozeVisualizer()
    visualizer.run(host=args.host, port=args.port, debug=args.debug)


def run_analysis(args):
    """Run analysis of Reddit discussions."""
    print("Initializing Reddit crawler and LLM summarizer...")

    crawler = RedditCrawler.from_env()
    summarizer = LLMSummarizer.from_env()

    print(f"Crawling posts from subreddits: {', '.join(args.subreddits)}")
    posts = crawler.get_all_coding_discussions(limit=args.limit)
    print(f"Found {len(posts)} relevant posts")

    if not posts:
        print("No posts found. Try different subreddits or increase the limit.")
        return

    print("Analyzing posts with LLM...")
    summaries = summarizer.summarize_posts(posts)
    print(f"Successfully analyzed {len(summaries)} posts")

    if summaries:
        print("Creating discussion summary...")
        discussion = summarizer.create_discussion_summary(summaries)

        if discussion:
            print("\n" + "=" * 80)
            print("ANALYSIS RESULTS")
            print("=" * 80)
            print(f"Topic: {discussion.topic}")
            print(f"Total Engagement: {discussion.total_engagement}")
            print("\nSentiment Overview:")
            print(f"  {discussion.sentiment_overview}")
            print("\nKey Insights:")
            for i, insight in enumerate(discussion.key_insights, 1):
                print(f"  {i}. {insight}")
            print("\nCommon Themes:")
            for theme in discussion.common_themes:
                print(f"  • {theme}")

            if args.output:
                save_results_to_file(discussion, args.output)
                print(f"\nResults saved to {args.output}")

    print("\nAnalysis complete!")


def run_crawl(args):
    """Run crawling of Reddit posts."""
    print("Initializing Reddit crawler...")
    crawler = RedditCrawler.from_env()

    posts = []
    for subreddit in args.subreddits:
        print(f"Crawling r/{subreddit}...")
        if args.search:
            subreddit_posts = list(
                crawler.search_subreddit(
                    subreddit, args.search, limit=args.limit // len(args.subreddits)
                )
            )
        else:
            subreddit_posts = list(
                crawler.get_coding_discussions(
                    [subreddit], limit_per_subreddit=args.limit // len(args.subreddits)
                )
            )
        posts.extend(subreddit_posts)
        print(f"  Found {len(subreddit_posts)} posts")

    print(f"\nCrawl complete! Total posts: {len(posts)}")
    for post in posts[:5]:  # Show first 5 posts
        print(f"  • {post.title} (r/{post.subreddit}, score: {post.score})")


def save_results_to_file(discussion, filename):
    """Save analysis results to a JSON file."""
    import json

    # Convert discussion to dict
    result = {
        "topic": discussion.topic,
        "key_insights": discussion.key_insights,
        "common_themes": discussion.common_themes,
        "sentiment_overview": discussion.sentiment_overview,
        "total_engagement": discussion.total_engagement,
        "post_summaries": [
            {
                "title": ps.title,
                "summary": ps.summary,
                "sentiment": ps.sentiment,
                "topics": ps.topics,
                "key_points": ps.key_points,
                "engagement_score": ps.engagement_score,
                "url": ps.url,
                "subreddit": ps.subreddit,
            }
            for ps in discussion.post_summaries
        ],
    }

    with open(filename, "w") as f:
        json.dump(result, f, indent=2)


def run_check_ports():
    """Check available ports for the web server."""
    import socket

    def check_port(host, port):
        """Check if a port is available."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, port))
                return True
        except OSError:
            return False

    host = "127.0.0.1"
    common_ports = [5000, 8080, 8000, 3000, 8888, 9000, 8081, 8082]

    print("🔍 Checking port availability:")
    print("=" * 40)

    available_ports = []
    for port in common_ports:
        status = "✅ Available" if check_port(host, port) else "❌ In use"
        print(f"Port {port:4d}: {status}")
        if check_port(host, port):
            available_ports.append(port)

    print("\n💡 Usage:")
    if available_ports:
        recommended_port = available_ports[0]
        print("   Default: uv run snooze web")
        print(f"   Custom:  uv run snooze web --port {recommended_port}")
        if 5000 not in available_ports:
            print("\n⚠️  Port 5000 is in use (likely macOS AirPlay Receiver)")
            print(
                "   You can disable it in: System Preferences > General > AirDrop & Handoff"
            )
    else:
        print(
            "   No common ports available. Try: uv run snooze web --port <custom_port>"
        )


if __name__ == "__main__":
    main()
