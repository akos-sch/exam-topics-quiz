"""Application settings and configuration."""

from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ScrapingConfig(BaseModel):
    """Scraping configuration."""

    rate_limit: float = Field(default=1.0, description="Seconds between requests")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    user_agent: str = Field(
        default="ExamTopics Quiz Extractor 1.0", description="User agent string"
    )


class LLMConfig(BaseModel):
    """LLM configuration for extraction."""

    provider: str = Field(default="google_vertexai", description="LLM provider")
    model: str = Field(default="gemini-2.0-flash-001", description="Model name")
    project_id: str | None = Field(default=None, description="GCP project ID")
    location: str = Field(default="us-central1", description="GCP region")
    temperature: float = Field(default=0, description="Model temperature")
    max_tokens: int = Field(default=4000, description="Maximum tokens")
    rate_limit: int = Field(default=60, description="Requests per minute")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    fallback_to_traditional_parsing: bool = Field(
        default=True, description="Fallback to traditional parsing if LLM fails"
    )


class ExtractionConfig(BaseModel):
    """Extraction configuration."""

    use_structured_output: bool = Field(
        default=True, description="Use LLM structured output"
    )
    batch_size: int = Field(default=5, description="Questions to process in parallel")
    cache_llm_responses: bool = Field(default=True, description="Cache LLM responses")
    validate_with_traditional_parser: bool = Field(
        default=True, description="Validate LLM output with traditional parser"
    )
    few_shot_examples: bool = Field(default=True, description="Use few-shot examples")


class StorageConfig(BaseModel):
    """Storage configuration."""

    base_path: str = Field(default="./data", description="Base storage path")
    backup_enabled: bool = Field(default=True, description="Enable backups")
    compression: bool = Field(default=True, description="Enable compression")


class ExamConfig(BaseModel):
    """Individual exam configuration."""

    name: str = Field(description="Exam name")
    url: str = Field(description="Exam URL")
    total_questions: int = Field(description="Total number of questions")
    extract_discussions: bool = Field(default=True, description="Extract discussions")
    use_llm_extraction: bool = Field(default=True, description="Use LLM for extraction")


class QuizConfig(BaseModel):
    """Quiz configuration."""

    default_question_count: int = Field(
        default=10, description="Default number of questions"
    )
    time_limit: int = Field(default=1800, description="Default time limit in seconds")
    randomize_questions: bool = Field(
        default=True, description="Randomize questions by default"
    )
    randomize_choices: bool = Field(
        default=True, description="Randomize choices by default"
    )
    show_explanations: bool = Field(
        default=False, description="Show explanations by default"
    )
    show_immediate_feedback: bool = Field(
        default=False, description="Show immediate feedback by default"
    )
    show_community_votes: bool = Field(
        default=False, description="Show community votes by default"
    )


class DisplayConfig(BaseModel):
    """Display configuration."""

    show_progress: bool = Field(default=True, description="Show progress indicators")
    show_timer: bool = Field(default=True, description="Show timer")
    clear_screen: bool = Field(
        default=True, description="Clear screen between questions"
    )
    color_output: bool = Field(default=True, description="Use colored output")


class Settings(BaseSettings):
    """Application settings."""

    # Basic settings
    debug: bool = Field(default=False, description="Enable debug mode")
    verbose: bool = Field(default=False, description="Enable verbose output")
    data_dir: Path = Field(default=Path("./data"), description="Data directory")

    # Configuration sections
    scraping: ScrapingConfig = Field(default_factory=ScrapingConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    quiz: QuizConfig = Field(default_factory=QuizConfig)
    display: DisplayConfig = Field(default_factory=DisplayConfig)

    # Exam configurations
    exams: list[ExamConfig] = Field(default_factory=list)

    class Config:
        env_prefix = "CERT_QUIZ_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
