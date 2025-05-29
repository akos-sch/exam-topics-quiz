"""Quiz engine for managing quiz sessions, scoring, and progress tracking."""

import logging
import random
import time
import uuid
from datetime import datetime

from ..models.question import Question
from ..models.session import QuizResult, QuizSession, QuizSettings, UserAnswer

logger = logging.getLogger(__name__)


class QuizEngine:
    """Manages quiz sessions, scoring, and progress tracking."""

    def __init__(self):
        """Initialize the quiz engine."""
        self.current_session: QuizSession | None = None
        self.current_question_index = 0
        self.question_start_time = 0.0

    def create_session(
        self, exam_name: str, questions: list[Question], settings: QuizSettings
    ) -> QuizSession:
        """Create a new quiz session.

        Args:
            exam_name: Name of the exam
            questions: List of questions for the quiz
            settings: Quiz configuration settings

        Returns:
            New QuizSession object
        """
        # Limit questions to the requested count
        if len(questions) > settings.question_count:
            if settings.randomize_questions:
                questions = random.sample(questions, settings.question_count)
            else:
                questions = questions[: settings.question_count]

        # Randomize question order if requested
        if settings.randomize_questions:
            random.shuffle(questions)

        # Randomize choice order if requested
        if settings.randomize_choices:
            for question in questions:
                choices = question.choices.copy()
                random.shuffle(choices)
                question.choices = choices

        session = QuizSession(
            session_id=str(uuid.uuid4()),
            exam_name=exam_name,
            settings=settings,
            questions=questions,
            start_time=datetime.now(),
        )

        self.current_session = session
        self.current_question_index = 0
        self.question_start_time = time.time()

        logger.info(
            f"Created quiz session {session.session_id} with {len(questions)} questions"
        )
        return session

    def get_current_question(self) -> Question | None:
        """Get the current question in the quiz.

        Returns:
            Current Question object or None if quiz is complete
        """
        if not self.current_session:
            return None

        if self.current_question_index >= len(self.current_session.questions):
            return None

        return self.current_session.questions[self.current_question_index]

    def get_progress(self) -> dict:
        """Get current quiz progress.

        Returns:
            Dictionary with progress information
        """
        if not self.current_session:
            return {}

        total_questions = len(self.current_session.questions)
        answered_questions = len(self.current_session.user_answers)

        return {
            "current_question": self.current_question_index + 1,
            "total_questions": total_questions,
            "answered_questions": answered_questions,
            "remaining_questions": total_questions - answered_questions,
            "progress_percentage": (answered_questions / total_questions) * 100
            if total_questions > 0
            else 0,
            "elapsed_time": (
                datetime.now() - self.current_session.start_time
            ).total_seconds(),
        }

    def submit_answer(self, selected_choice: str) -> bool:
        """Submit an answer for the current question.

        Args:
            selected_choice: The selected choice letter (A, B, C, D)

        Returns:
            True if answer was submitted successfully, False otherwise
        """
        if not self.current_session:
            logger.error("No active quiz session")
            return False

        current_question = self.get_current_question()
        if not current_question:
            logger.error("No current question available")
            return False

        # Validate choice
        if selected_choice not in ["A", "B", "C", "D"]:
            logger.error(f"Invalid choice: {selected_choice}")
            return False

        # Check if choice exists for this question
        valid_choices = [choice.letter for choice in current_question.choices]
        if selected_choice not in valid_choices:
            logger.error(f"Choice {selected_choice} not available for this question")
            return False

        # Calculate time taken
        time_taken = time.time() - self.question_start_time

        # Check if answer is correct
        is_correct = selected_choice == current_question.correct_answer

        # Create user answer
        user_answer = UserAnswer(
            question_id=current_question.id,
            selected_choice=selected_choice,
            is_correct=is_correct,
            time_taken=time_taken,
            timestamp=datetime.now(),
        )

        # Add to session
        self.current_session.user_answers.append(user_answer)

        # Move to next question
        self.current_question_index += 1
        self.question_start_time = time.time()

        logger.debug(
            f"Answer submitted: {selected_choice} ({'correct' if is_correct else 'incorrect'})"
        )
        return True

    def skip_question(self) -> bool:
        """Skip the current question.

        Returns:
            True if question was skipped successfully, False otherwise
        """
        if not self.current_session:
            return False

        current_question = self.get_current_question()
        if not current_question:
            return False

        # Submit a placeholder answer
        time_taken = time.time() - self.question_start_time

        user_answer = UserAnswer(
            question_id=current_question.id,
            selected_choice="",  # Empty choice indicates skipped
            is_correct=False,
            time_taken=time_taken,
            timestamp=datetime.now(),
        )

        self.current_session.user_answers.append(user_answer)

        # Move to next question
        self.current_question_index += 1
        self.question_start_time = time.time()

        logger.debug(f"Question {current_question.id} skipped")
        return True

    def is_quiz_complete(self) -> bool:
        """Check if the quiz is complete.

        Returns:
            True if quiz is complete, False otherwise
        """
        if not self.current_session:
            return False

        return self.current_question_index >= len(self.current_session.questions)

    def finish_quiz(self) -> QuizResult | None:
        """Finish the current quiz and calculate results.

        Returns:
            QuizResult object or None if no active session
        """
        if not self.current_session:
            return None

        # Set end time
        self.current_session.end_time = datetime.now()

        # Calculate results
        total_questions = len(self.current_session.questions)
        correct_answers = sum(
            1 for answer in self.current_session.user_answers if answer.is_correct
        )
        score_percentage = (
            (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        )

        total_time = (
            self.current_session.end_time - self.current_session.start_time
        ).total_seconds()
        average_time = total_time / total_questions if total_questions > 0 else 0

        result = QuizResult(
            total_questions=total_questions,
            correct_answers=correct_answers,
            score_percentage=score_percentage,
            total_time=total_time,
            average_time_per_question=average_time,
        )

        self.current_session.result = result

        logger.info(
            f"Quiz completed: {correct_answers}/{total_questions} ({score_percentage:.1f}%)"
        )
        return result

    def get_question_result(self, question_index: int) -> dict | None:
        """Get result for a specific question.

        Args:
            question_index: Index of the question (0-based)

        Returns:
            Dictionary with question result or None if not found
        """
        if not self.current_session:
            return None

        if question_index >= len(self.current_session.questions):
            return None

        if question_index >= len(self.current_session.user_answers):
            return None

        question = self.current_session.questions[question_index]
        user_answer = self.current_session.user_answers[question_index]

        return {
            "question": question,
            "user_answer": user_answer,
            "correct_answer": question.correct_answer,
            "is_correct": user_answer.is_correct,
            "explanation": question.explanation,
            "time_taken": user_answer.time_taken,
        }

    def get_detailed_results(self) -> dict | None:
        """Get detailed quiz results with question-by-question breakdown.

        Returns:
            Dictionary with detailed results or None if no session
        """
        if not self.current_session or not self.current_session.result:
            return None

        question_results = []
        for i in range(len(self.current_session.questions)):
            result = self.get_question_result(i)
            if result:
                question_results.append(result)

        # Calculate additional statistics
        correct_by_topic = {}
        total_by_topic = {}
        time_by_question = []

        for result in question_results:
            question = result["question"]
            topic = question.topic or "General"

            if topic not in total_by_topic:
                total_by_topic[topic] = 0
                correct_by_topic[topic] = 0

            total_by_topic[topic] += 1
            if result["is_correct"]:
                correct_by_topic[topic] += 1

            time_by_question.append(result["time_taken"])

        # Calculate topic performance
        topic_performance = {}
        for topic in total_by_topic:
            topic_performance[topic] = {
                "correct": correct_by_topic[topic],
                "total": total_by_topic[topic],
                "percentage": (correct_by_topic[topic] / total_by_topic[topic]) * 100,
            }

        return {
            "session": self.current_session,
            "result": self.current_session.result,
            "question_results": question_results,
            "topic_performance": topic_performance,
            "time_statistics": {
                "fastest_question": min(time_by_question) if time_by_question else 0,
                "slowest_question": max(time_by_question) if time_by_question else 0,
                "median_time": sorted(time_by_question)[len(time_by_question) // 2]
                if time_by_question
                else 0,
            },
        }

    def reset_session(self) -> None:
        """Reset the current quiz session."""
        self.current_session = None
        self.current_question_index = 0
        self.question_start_time = 0.0
        logger.debug("Quiz session reset")

    def get_time_remaining(self) -> float | None:
        """Get remaining time for the quiz.

        Returns:
            Remaining time in seconds or None if no time limit
        """
        if not self.current_session or not self.current_session.settings.time_limit:
            return None

        elapsed = (datetime.now() - self.current_session.start_time).total_seconds()
        remaining = self.current_session.settings.time_limit - elapsed

        return max(0, remaining)

    def is_time_expired(self) -> bool:
        """Check if the quiz time has expired.

        Returns:
            True if time has expired, False otherwise
        """
        remaining = self.get_time_remaining()
        return remaining is not None and remaining <= 0
