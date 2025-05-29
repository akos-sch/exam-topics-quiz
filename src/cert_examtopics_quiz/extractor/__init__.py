"""Extractor module for web scraping and data extraction from ExamTopics."""

from .parser import QuestionParser
from .scraper import ExamTopicsScraper
from .storage import StorageManager

__all__ = ["ExamTopicsScraper", "QuestionParser", "StorageManager"]
