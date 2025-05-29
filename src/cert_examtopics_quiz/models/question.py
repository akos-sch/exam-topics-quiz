"""Question-related data models."""

from datetime import datetime

from pydantic import BaseModel, Field


class Choice(BaseModel):
    """Represents a multiple choice option."""

    letter: str = Field(description="Choice letter (A, B, C, D)")
    text: str = Field(description="The full text of the choice")
    is_most_voted: bool = Field(
        default=False, description="Whether this is the most voted answer"
    )
    is_correct: bool = Field(
        default=False, description="Whether this is the correct answer"
    )


class VotingData(BaseModel):
    """Community voting statistics."""

    total_votes: int = Field(description="Total number of votes")
    vote_distribution: dict[str, int] = Field(
        description="Vote count per choice letter"
    )
    most_voted_answer: str = Field(description="The choice letter with most votes")
    confidence_score: float = Field(description="Confidence based on vote distribution")


class QuestionMetadata(BaseModel):
    """Additional question metadata."""

    extraction_timestamp: datetime = Field(
        description="When the question was extracted"
    )
    source_url: str = Field(description="Original URL of the question")
    page_number: int = Field(description="Page number in the exam")
    difficulty_level: str = Field(default="", description="Estimated difficulty")


class Question(BaseModel):
    """Complete question data structure."""

    id: str = Field(description="Unique question identifier")
    number: int = Field(description="Question number in the exam")
    topic: str = Field(description="Topic or section name")
    text: str = Field(description="The question text content")
    choices: list[Choice] = Field(description="List of multiple choice options")
    correct_answer: str = Field(description="The correct answer choice letter")
    explanation: str = Field(default="", description="Explanation of the answer")
    voting_data: VotingData = Field(description="Community voting statistics")
    metadata: QuestionMetadata = Field(description="Additional metadata")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
