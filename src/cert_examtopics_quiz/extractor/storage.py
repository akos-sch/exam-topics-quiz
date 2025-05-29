"""Storage manager for organizing and persisting extracted data."""

import json
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path

from ..config.settings import get_settings
from ..models.extraction import Discussion, ExamInfo, ExtractionReport
from ..models.question import Question

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages storage and organization of extracted exam data."""

    def __init__(self, base_path: str | None = None):
        """Initialize the storage manager.

        Args:
            base_path: Base directory for data storage (uses config default if None)
        """
        self.settings = get_settings()
        self.base_path = Path(base_path or self.settings.storage.base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Create directory structure
        self.exams_dir = self.base_path / "exams"
        self.cache_dir = self.base_path / "cache"
        self.backup_dir = self.base_path / "backups"

        for directory in [self.exams_dir, self.cache_dir, self.backup_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize a string for safe use as a filename.

        Args:
            filename: Original filename string

        Returns:
            Sanitized filename safe for filesystem use
        """
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
        # Remove path separators
        sanitized = sanitized.replace("/", "_").replace("\\", "_")
        # Limit length
        if len(sanitized) > 200:
            sanitized = sanitized[:200]
        # Ensure it's not empty
        if not sanitized:
            sanitized = "unknown"
        return sanitized

    def create_exam_directory(self, exam_name: str) -> Path:
        """Create directory structure for an exam.

        Args:
            exam_name: Name of the exam

        Returns:
            Path to the exam directory
        """
        exam_dir = self.exams_dir / exam_name
        exam_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        questions_dir = exam_dir / "questions"
        discussions_dir = exam_dir / "discussions"

        questions_dir.mkdir(exist_ok=True)
        discussions_dir.mkdir(exist_ok=True)

        logger.info(f"Created exam directory structure: {exam_dir}")
        return exam_dir

    def save_question(self, question: Question, exam_name: str) -> bool:
        """Save a question to storage.

        Args:
            question: Question object to save
            exam_name: Name of the exam

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            exam_dir = self.create_exam_directory(exam_name)
            questions_dir = exam_dir / "questions"

            # Create filename
            filename = f"question_{question.number:03d}.json"
            file_path = questions_dir / filename

            # Convert to dict and save
            question_data = question.model_dump(mode="json")

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(question_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved question {question.id} to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save question {question.id}: {e}")
            return False

    def save_discussion(self, discussion: Discussion, exam_name: str) -> bool:
        """Save a discussion to storage.

        Args:
            discussion: Discussion object to save
            exam_name: Name of the exam

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            exam_dir = self.create_exam_directory(exam_name)
            discussions_dir = exam_dir / "discussions"

            # Create filename based on question ID (sanitized for filesystem safety)
            sanitized_question_id = self._sanitize_filename(discussion.question_id)
            filename = f"{sanitized_question_id}_discussion.json"
            file_path = discussions_dir / filename

            # Convert to dict and save
            discussion_data = discussion.model_dump(mode="json")

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(discussion_data, f, indent=2, ensure_ascii=False)

            logger.debug(
                f"Saved discussion for {discussion.question_id} to {file_path}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to save discussion for {discussion.question_id}: {e}")
            return False

    def save_exam_metadata(self, exam_info: ExamInfo, exam_name: str) -> bool:
        """Save exam metadata.

        Args:
            exam_info: Exam information to save
            exam_name: Name of the exam

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            exam_dir = self.create_exam_directory(exam_name)
            metadata_path = exam_dir / "metadata.json"

            # Convert to dict and save
            metadata = exam_info.model_dump(mode="json")

            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved exam metadata to {metadata_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save exam metadata: {e}")
            return False

    def save_extraction_report(self, report: ExtractionReport, exam_name: str) -> bool:
        """Save extraction report.

        Args:
            report: Extraction report to save
            exam_name: Name of the exam

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            exam_dir = self.create_exam_directory(exam_name)
            report_path = exam_dir / "extraction_report.json"

            # Convert to dict and save
            report_data = report.model_dump(mode="json")

            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved extraction report to {report_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save extraction report: {e}")
            return False

    def load_question(self, question_id: str, exam_name: str) -> Question | None:
        """Load a question from storage.

        Args:
            question_id: Question identifier
            exam_name: Name of the exam

        Returns:
            Question object or None if not found
        """
        try:
            exam_dir = self.exams_dir / exam_name
            questions_dir = exam_dir / "questions"

            # Try to find the question file
            question_files = list(questions_dir.glob(f"*{question_id}*.json"))
            if not question_files:
                return None

            file_path = question_files[0]

            with open(file_path, encoding="utf-8") as f:
                question_data = json.load(f)

            return Question.model_validate(question_data)

        except Exception as e:
            logger.error(f"Failed to load question {question_id}: {e}")
            return None

    def load_all_questions(self, exam_name: str) -> list[Question]:
        """Load all questions for an exam.

        Args:
            exam_name: Name of the exam

        Returns:
            List of Question objects
        """
        questions = []

        try:
            exam_dir = self.exams_dir / exam_name
            questions_dir = exam_dir / "questions"

            if not questions_dir.exists():
                return questions

            # Load all question files
            for file_path in sorted(questions_dir.glob("question_*.json")):
                try:
                    with open(file_path, encoding="utf-8") as f:
                        question_data = json.load(f)

                    question = Question.model_validate(question_data)
                    questions.append(question)

                except Exception as e:
                    logger.error(f"Failed to load question from {file_path}: {e}")

            logger.info(f"Loaded {len(questions)} questions for exam {exam_name}")
            return questions

        except Exception as e:
            logger.error(f"Failed to load questions for exam {exam_name}: {e}")
            return questions

    def load_discussion(self, question_id: str, exam_name: str) -> Discussion | None:
        """Load a discussion from storage.

        Args:
            question_id: Question identifier
            exam_name: Name of the exam

        Returns:
            Discussion object or None if not found
        """
        try:
            exam_dir = self.exams_dir / exam_name
            discussions_dir = exam_dir / "discussions"

            # Try sanitized filename first
            sanitized_question_id = self._sanitize_filename(question_id)
            file_path = discussions_dir / f"{sanitized_question_id}_discussion.json"

            # Fallback to original filename format for backward compatibility
            if not file_path.exists():
                file_path = discussions_dir / f"{question_id}_discussion.json"

            if not file_path.exists():
                return None

            with open(file_path, encoding="utf-8") as f:
                discussion_data = json.load(f)

            return Discussion.model_validate(discussion_data)

        except Exception as e:
            logger.error(f"Failed to load discussion for {question_id}: {e}")
            return None

    def load_exam_metadata(self, exam_name: str) -> ExamInfo | None:
        """Load exam metadata.

        Args:
            exam_name: Name of the exam

        Returns:
            ExamInfo object or None if not found
        """
        try:
            exam_dir = self.exams_dir / exam_name
            metadata_path = exam_dir / "metadata.json"

            if not metadata_path.exists():
                return None

            with open(metadata_path, encoding="utf-8") as f:
                metadata = json.load(f)

            return ExamInfo.model_validate(metadata)

        except Exception as e:
            logger.error(f"Failed to load exam metadata for {exam_name}: {e}")
            return None

    def list_available_exams(self) -> list[str]:
        """List all available exams in storage.

        Returns:
            List of exam names
        """
        try:
            if not self.exams_dir.exists():
                return []

            exams = []
            for exam_dir in self.exams_dir.iterdir():
                if exam_dir.is_dir():
                    exams.append(exam_dir.name)

            return sorted(exams)

        except Exception as e:
            logger.error(f"Failed to list available exams: {e}")
            return []

    def get_exam_stats(self, exam_name: str) -> dict[str, int]:
        """Get statistics for an exam.

        Args:
            exam_name: Name of the exam

        Returns:
            Dictionary with exam statistics
        """
        try:
            exam_dir = self.exams_dir / exam_name

            if not exam_dir.exists():
                return {"questions": 0, "discussions": 0}

            questions_dir = exam_dir / "questions"
            discussions_dir = exam_dir / "discussions"

            question_count = (
                len(list(questions_dir.glob("question_*.json")))
                if questions_dir.exists()
                else 0
            )
            discussion_count = (
                len(list(discussions_dir.glob("*_discussion.json")))
                if discussions_dir.exists()
                else 0
            )

            return {"questions": question_count, "discussions": discussion_count}

        except Exception as e:
            logger.error(f"Failed to get exam stats for {exam_name}: {e}")
            return {"questions": 0, "discussions": 0}

    def backup_exam(self, exam_name: str) -> bool:
        """Create a backup of an exam.

        Args:
            exam_name: Name of the exam to backup

        Returns:
            True if backup was successful, False otherwise
        """
        if not self.settings.storage.backup_enabled:
            return True

        try:
            exam_dir = self.exams_dir / exam_name

            if not exam_dir.exists():
                logger.warning(f"Exam directory {exam_name} does not exist")
                return False

            # Create backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{exam_name}_backup_{timestamp}"
            backup_path = self.backup_dir / backup_name

            # Copy the entire exam directory
            shutil.copytree(exam_dir, backup_path)

            logger.info(f"Created backup: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to backup exam {exam_name}: {e}")
            return False

    def validate_data_integrity(self, exam_name: str) -> dict[str, list[str]]:
        """Validate data integrity for an exam.

        Args:
            exam_name: Name of the exam to validate

        Returns:
            Dictionary with validation results
        """
        results = {
            "valid_questions": [],
            "invalid_questions": [],
            "valid_discussions": [],
            "invalid_discussions": [],
            "errors": [],
        }

        try:
            exam_dir = self.exams_dir / exam_name

            if not exam_dir.exists():
                results["errors"].append(f"Exam directory {exam_name} does not exist")
                return results

            # Validate questions
            questions_dir = exam_dir / "questions"
            if questions_dir.exists():
                for file_path in questions_dir.glob("question_*.json"):
                    try:
                        with open(file_path, encoding="utf-8") as f:
                            question_data = json.load(f)

                        Question.model_validate(question_data)
                        results["valid_questions"].append(file_path.name)

                    except Exception as e:
                        results["invalid_questions"].append(f"{file_path.name}: {e}")

            # Validate discussions
            discussions_dir = exam_dir / "discussions"
            if discussions_dir.exists():
                for file_path in discussions_dir.glob("*_discussion.json"):
                    try:
                        with open(file_path, encoding="utf-8") as f:
                            discussion_data = json.load(f)

                        Discussion.model_validate(discussion_data)
                        results["valid_discussions"].append(file_path.name)

                    except Exception as e:
                        results["invalid_discussions"].append(f"{file_path.name}: {e}")

            logger.info(
                f"Validation complete for {exam_name}: "
                f"{len(results['valid_questions'])} valid questions, "
                f"{len(results['invalid_questions'])} invalid questions"
            )

            return results

        except Exception as e:
            logger.error(f"Failed to validate data integrity for {exam_name}: {e}")
            results["errors"].append(str(e))
            return results
