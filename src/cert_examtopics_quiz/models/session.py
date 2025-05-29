"""Quiz session-related data models."""

from datetime import datetime

from pydantic import BaseModel, Field

from .question import Question


class QuizSettings(BaseModel):
    """Quiz configuration settings."""

    question_count: int = Field(description="Number of questions in quiz")
    time_limit: int | None = Field(default=None, description="Time limit in seconds")
    randomize_questions: bool = Field(
        default=True, description="Whether to randomize question order"
    )
    randomize_choices: bool = Field(
        default=True, description="Whether to randomize choice order"
    )
    show_explanations: bool = Field(
        default=False, description="Whether to show explanations"
    )
    show_immediate_feedback: bool = Field(
        default=False, description="Whether to show correct/incorrect immediately"
    )
    show_community_votes: bool = Field(
        default=False, description="Whether to show community voting data"
    )


class UserAnswer(BaseModel):
    """User's answer to a question."""

    question_id: str = Field(description="Question identifier")
    selected_choice: str = Field(description="Selected choice letter")
    is_correct: bool = Field(description="Whether the answer is correct")
    time_taken: float = Field(description="Time taken to answer in seconds")
    timestamp: datetime = Field(description="When the answer was submitted")


class QuizResult(BaseModel):
    """Quiz completion results."""

    total_questions: int = Field(description="Total number of questions")
    correct_answers: int = Field(description="Number of correct answers")
    score_percentage: float = Field(description="Score as percentage")
    total_time: float = Field(description="Total time taken in seconds")
    average_time_per_question: float = Field(description="Average time per question")


class QuizSession(BaseModel):
    """Complete quiz session data."""

    session_id: str = Field(description="Unique session identifier")
    exam_name: str = Field(description="Name of the exam")
    settings: QuizSettings = Field(description="Quiz configuration")
    questions: list[Question] = Field(description="Questions in the quiz")
    user_answers: list[UserAnswer] = Field(
        default_factory=list, description="User's answers"
    )
    start_time: datetime = Field(description="Quiz start time")
    end_time: datetime | None = Field(default=None, description="Quiz end time")
    result: QuizResult | None = Field(default=None, description="Quiz results")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
