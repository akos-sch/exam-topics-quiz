"""Utility modules for the Certificate ExamTopics Quiz application."""

from .auth import setup_authentication, validate_authentication
from .prompts import get_discussion_extraction_prompt, get_question_extraction_prompt

__all__ = [
    "setup_authentication",
    "validate_authentication",
    "get_question_extraction_prompt",
    "get_discussion_extraction_prompt",
]
