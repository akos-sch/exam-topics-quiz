"""Data loader for loading and filtering questions from storage."""

import logging
import random

from ..extractor.storage import StorageManager
from ..models.question import Question

logger = logging.getLogger(__name__)


class DataLoader:
    """Loads and filters questions from storage for quiz sessions."""

    def __init__(self, storage_manager: StorageManager | None = None):
        """Initialize the data loader.

        Args:
            storage_manager: Storage manager instance (creates new if None)
        """
        self.storage = storage_manager or StorageManager()
        self._question_cache: dict[str, list[Question]] = {}

    def get_available_exams(self) -> list[str]:
        """Get list of available exams.

        Returns:
            List of exam names
        """
        return self.storage.list_available_exams()

    def get_exam_stats(self, exam_name: str) -> dict[str, int]:
        """Get statistics for an exam.

        Args:
            exam_name: Name of the exam

        Returns:
            Dictionary with exam statistics
        """
        return self.storage.get_exam_stats(exam_name)

    def load_questions(self, exam_name: str, use_cache: bool = True) -> list[Question]:
        """Load all questions for an exam.

        Args:
            exam_name: Name of the exam
            use_cache: Whether to use cached questions

        Returns:
            List of Question objects
        """
        if use_cache and exam_name in self._question_cache:
            logger.debug(f"Using cached questions for {exam_name}")
            return self._question_cache[exam_name]

        logger.info(f"Loading questions for exam: {exam_name}")
        questions = self.storage.load_all_questions(exam_name)

        if use_cache:
            self._question_cache[exam_name] = questions

        return questions

    def filter_questions(
        self,
        questions: list[Question],
        topic: str | None = None,
        difficulty: str | None = None,
        min_votes: int | None = None,
        confidence_threshold: float | None = None,
    ) -> list[Question]:
        """Filter questions based on criteria.

        Args:
            questions: List of questions to filter
            topic: Filter by topic/section
            difficulty: Filter by difficulty level
            min_votes: Minimum number of votes required
            confidence_threshold: Minimum confidence score required

        Returns:
            Filtered list of questions
        """
        filtered = questions.copy()

        if topic:
            filtered = [q for q in filtered if topic.lower() in q.topic.lower()]
            logger.debug(f"Filtered by topic '{topic}': {len(filtered)} questions")

        if difficulty:
            filtered = [
                q
                for q in filtered
                if q.metadata.difficulty_level
                and difficulty.lower() in q.metadata.difficulty_level.lower()
            ]
            logger.debug(
                f"Filtered by difficulty '{difficulty}': {len(filtered)} questions"
            )

        if min_votes is not None:
            filtered = [q for q in filtered if q.voting_data.total_votes >= min_votes]
            logger.debug(
                f"Filtered by min votes {min_votes}: {len(filtered)} questions"
            )

        if confidence_threshold is not None:
            filtered = [
                q
                for q in filtered
                if q.voting_data.confidence_score >= confidence_threshold
            ]
            logger.debug(
                f"Filtered by confidence {confidence_threshold}: {len(filtered)} questions"
            )

        return filtered

    def select_questions(
        self,
        questions: list[Question],
        count: int,
        randomize: bool = True,
        seed: int | None = None,
    ) -> list[Question]:
        """Select a subset of questions for a quiz.

        Args:
            questions: List of questions to select from
            count: Number of questions to select
            randomize: Whether to randomize selection
            seed: Random seed for reproducible selection

        Returns:
            Selected list of questions
        """
        if not questions:
            logger.warning("No questions available for selection")
            return []

        # Don't select more questions than available
        count = min(count, len(questions))

        if randomize:
            if seed is not None:
                random.seed(seed)
            selected = random.sample(questions, count)
            logger.debug(f"Randomly selected {count} questions from {len(questions)}")
        else:
            # Select first N questions (they should be sorted by number)
            selected = sorted(questions, key=lambda q: q.number)[:count]
            logger.debug(f"Selected first {count} questions from {len(questions)}")

        return selected

    def get_questions_by_topic(self, exam_name: str) -> dict[str, list[Question]]:
        """Group questions by topic.

        Args:
            exam_name: Name of the exam

        Returns:
            Dictionary mapping topics to lists of questions
        """
        questions = self.load_questions(exam_name)
        topics: dict[str, list[Question]] = {}

        for question in questions:
            topic = question.topic or "General"
            if topic not in topics:
                topics[topic] = []
            topics[topic].append(question)

        # Sort questions within each topic
        for topic in topics:
            topics[topic].sort(key=lambda q: q.number)

        logger.debug(f"Grouped {len(questions)} questions into {len(topics)} topics")
        return topics

    def get_question_difficulties(self, questions: list[Question]) -> dict[str, int]:
        """Get distribution of question difficulties.

        Args:
            questions: List of questions to analyze

        Returns:
            Dictionary mapping difficulty levels to counts
        """
        difficulties: dict[str, int] = {}

        for question in questions:
            difficulty = question.metadata.difficulty_level or "Unknown"
            difficulties[difficulty] = difficulties.get(difficulty, 0) + 1

        return difficulties

    def get_voting_statistics(self, questions: list[Question]) -> dict[str, float]:
        """Get voting statistics for questions.

        Args:
            questions: List of questions to analyze

        Returns:
            Dictionary with voting statistics
        """
        if not questions:
            return {}

        total_votes = sum(q.voting_data.total_votes for q in questions)
        confidence_scores = [q.voting_data.confidence_score for q in questions]

        return {
            "total_questions": len(questions),
            "total_votes": total_votes,
            "average_votes_per_question": total_votes / len(questions),
            "average_confidence": sum(confidence_scores) / len(confidence_scores),
            "high_confidence_questions": len(
                [q for q in questions if q.voting_data.confidence_score >= 0.8]
            ),
            "low_confidence_questions": len(
                [q for q in questions if q.voting_data.confidence_score < 0.5]
            ),
        }

    def search_questions(
        self,
        exam_name: str,
        query: str,
        search_in_choices: bool = True,
        search_in_explanations: bool = True,
    ) -> list[Question]:
        """Search questions by text content.

        Args:
            exam_name: Name of the exam
            query: Search query
            search_in_choices: Whether to search in choice text
            search_in_explanations: Whether to search in explanations

        Returns:
            List of matching questions
        """
        questions = self.load_questions(exam_name)
        query_lower = query.lower()
        matching = []

        for question in questions:
            # Search in question text
            if query_lower in question.text.lower():
                matching.append(question)
                continue

            # Search in choices
            if search_in_choices:
                for choice in question.choices:
                    if query_lower in choice.text.lower():
                        matching.append(question)
                        break
                else:
                    # Search in explanation if no choice match
                    if search_in_explanations and question.explanation:
                        if query_lower in question.explanation.lower():
                            matching.append(question)
            elif search_in_explanations and question.explanation:
                if query_lower in question.explanation.lower():
                    matching.append(question)

        logger.debug(f"Search for '{query}' found {len(matching)} questions")
        return matching

    def clear_cache(self, exam_name: str | None = None) -> None:
        """Clear question cache.

        Args:
            exam_name: Specific exam to clear (clears all if None)
        """
        if exam_name:
            self._question_cache.pop(exam_name, None)
            logger.debug(f"Cleared cache for exam: {exam_name}")
        else:
            self._question_cache.clear()
            logger.debug("Cleared all question cache")

    def validate_exam_data(self, exam_name: str) -> dict[str, list[str]]:
        """Validate exam data integrity.

        Args:
            exam_name: Name of the exam to validate

        Returns:
            Dictionary with validation results
        """
        return self.storage.validate_data_integrity(exam_name)
