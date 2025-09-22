"""Snooze - Reddit AI Agent Discussion Analyzer."""

from .crawler import RedditCrawler, RedditPost
from .storage import DataStorage
from .summarizer import DiscussionSummary, LLMSummarizer, PostSummary
from .visualizer import SnoozeVisualizer, create_app

__version__ = "0.1.0"
__all__ = [
    "RedditCrawler",
    "RedditPost",
    "LLMSummarizer",
    "PostSummary",
    "DiscussionSummary",
    "SnoozeVisualizer",
    "create_app",
    "DataStorage",
]


def hello() -> str:
    return "Hello from snooze!"
