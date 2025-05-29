"""Configuration management for the Certificate ExamTopics Quiz application."""

from .gcp import get_gcp_config
from .settings import Settings, get_settings

__all__ = ["Settings", "get_settings", "get_gcp_config"]
