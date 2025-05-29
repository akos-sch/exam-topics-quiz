"""Extraction-related data models."""

from datetime import datetime

from pydantic import BaseModel, Field


class Comment(BaseModel):
    """Discussion comment structure."""

    id: str = Field(description="Comment identifier")
    author: str = Field(description="Comment author username")
    content: str = Field(description="Comment text content")
    upvotes: int = Field(description="Number of upvotes")
    is_highly_voted: bool = Field(
        default=False, description="Whether comment is highly voted"
    )
    timestamp: str = Field(description="Comment timestamp")
    replies: list["Comment"] = Field(default_factory=list, description="Nested replies")

    class Config:
        # Enable forward references for self-referencing model
        arbitrary_types_allowed = True


class Discussion(BaseModel):
    """Discussion thread for a question."""

    question_id: str = Field(description="Associated question ID")
    total_comments: int = Field(description="Total number of comments")
    comments: list[Comment] = Field(description="List of discussion comments")
    extraction_timestamp: datetime = Field(description="When discussion was extracted")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ExamInfo(BaseModel):
    """Information about an exam."""

    name: str = Field(description="Exam name")
    vendor: str = Field(description="Exam vendor (e.g., Google, AWS)")
    code: str = Field(description="Exam code")
    total_questions: int = Field(description="Total number of questions available")
    url: str = Field(description="Source URL")
    last_updated: datetime = Field(description="Last extraction timestamp")


class ExtractionReport(BaseModel):
    """Report of extraction process."""

    exam_info: ExamInfo = Field(description="Exam information")
    questions_extracted: int = Field(description="Number of questions extracted")
    discussions_extracted: int = Field(description="Number of discussions extracted")
    extraction_errors: list[str] = Field(
        default_factory=list, description="Extraction errors"
    )
    start_time: datetime = Field(description="Extraction start time")
    end_time: datetime = Field(description="Extraction end time")
    success: bool = Field(description="Whether extraction was successful")


# Update forward references for self-referencing Comment model
Comment.model_rebuild()
