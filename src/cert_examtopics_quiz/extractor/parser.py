"""HTML parser using LangChain structured output for data extraction."""

import logging
import time
from datetime import datetime

from bs4 import BeautifulSoup
from langchain_google_vertexai import ChatVertexAI

from ..config.settings import get_settings
from ..models.extraction import Comment, Discussion
from ..models.question import Choice, Question, QuestionMetadata, VotingData
from ..utils.auth import get_gcp_project_id
from ..utils.prompts import (
    get_discussion_extraction_prompt,
    get_question_extraction_prompt,
    get_voting_data_extraction_prompt,
)

logger = logging.getLogger(__name__)


class QuestionParser:
    """Parser for extracting structured data from ExamTopics HTML using LangChain."""

    def __init__(self, project_id: str | None = None, location: str = "us-central1"):
        """Initialize the parser with LangChain LLM.

        Args:
            project_id: GCP project ID (uses default if None)
            location: GCP region for Vertex AI
        """
        self.settings = get_settings()
        self.project_id = project_id or get_gcp_project_id()
        self.location = location

        # Initialize LLM with Vertex AI
        try:
            self.llm = ChatVertexAI(
                model_name=self.settings.llm.model,
                temperature=self.settings.llm.temperature,
                max_output_tokens=self.settings.llm.max_tokens,
                project=self.project_id,
                location=self.location,
            )
            logger.info(f"Initialized LLM with model {self.settings.llm.model}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            self.llm = None

        # Create structured output chains
        self._setup_extraction_chains()

        # Rate limiting for LLM calls
        self.last_llm_call = 0
        self.llm_rate_limit = (
            60 / self.settings.llm.rate_limit
        )  # Convert to seconds between calls

    def _setup_extraction_chains(self) -> None:
        """Setup LangChain extraction chains with structured output."""
        if not self.llm:
            return

        try:
            # Question extraction chain
            self.question_prompt = get_question_extraction_prompt()
            self.structured_question_llm = self.llm.with_structured_output(Question)

            # Discussion extraction chain
            self.discussion_prompt = get_discussion_extraction_prompt()
            self.structured_discussion_llm = self.llm.with_structured_output(Discussion)

            # Voting data extraction chain
            self.voting_prompt = get_voting_data_extraction_prompt()
            self.structured_voting_llm = self.llm.with_structured_output(VotingData)

            logger.info("Successfully setup LangChain extraction chains")

        except Exception as e:
            logger.error(f"Failed to setup extraction chains: {e}")
            self.llm = None

    def _wait_for_llm_rate_limit(self) -> None:
        """Implement rate limiting for LLM calls."""
        current_time = time.time()
        time_since_last = current_time - self.last_llm_call

        if time_since_last < self.llm_rate_limit:
            sleep_time = self.llm_rate_limit - time_since_last
            logger.debug(f"LLM rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_llm_call = time.time()

    def _extract_with_retry(self, chain, content: str, max_retries: int = 3):
        """Extract data with retry logic and error handling.

        Args:
            chain: LangChain extraction chain
            content: Content to extract from
            max_retries: Maximum number of retry attempts

        Returns:
            Extracted data or None if failed
        """
        if not self.llm:
            return None

        for attempt in range(max_retries):
            try:
                self._wait_for_llm_rate_limit()
                result = chain.invoke({"html_content": content})
                return result

            except Exception as e:
                logger.warning(f"LLM extraction failed (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"LLM extraction failed after {max_retries} attempts")
                    return None

                # Exponential backoff
                time.sleep(2**attempt)

        return None

    def parse_question_card(
        self, soup: BeautifulSoup, source_url: str = "", page_number: int = 1
    ) -> Question | None:
        """Extract question data using LangChain structured output.

        Args:
            soup: BeautifulSoup object of the question card
            source_url: Source URL of the question
            page_number: Page number in the exam

        Returns:
            Question object or None if extraction failed
        """
        try:
            html_content = str(soup)

            # Try LLM extraction first
            if self.settings.extraction.use_structured_output and self.llm:
                # Create the extraction chain
                extraction_chain = self.question_prompt | self.structured_question_llm
                question = self._extract_with_retry(extraction_chain, html_content)

                if question:
                    # Add metadata
                    question.metadata = QuestionMetadata(
                        extraction_timestamp=datetime.now(),
                        source_url=source_url,
                        page_number=page_number,
                    )

                    # Validate and fix the question
                    question = self._validate_and_fix_question(question, soup)
                    return question

            # Fallback to traditional parsing
            if self.settings.llm.fallback_to_traditional_parsing:
                logger.info("Falling back to traditional parsing")
                return self._parse_question_traditional(soup, source_url, page_number)

            return None

        except Exception as e:
            logger.error(f"Failed to parse question card: {e}")
            return None

    def _validate_and_fix_question(
        self, question: Question, soup: BeautifulSoup
    ) -> Question:
        """Validate and fix question data extracted by LLM.

        Args:
            question: Question object from LLM
            soup: Original BeautifulSoup object for validation

        Returns:
            Validated and fixed Question object
        """
        try:
            # Ensure question ID format
            if not question.id.startswith("question_"):
                question.id = f"question_{question.number}"

            # Validate choices
            if len(question.choices) < 2:
                logger.warning(f"Question {question.id} has fewer than 2 choices")

            # Ensure correct answer is marked in choices
            for choice in question.choices:
                choice.is_correct = choice.letter == question.correct_answer

            # Validate voting data
            if question.voting_data.total_votes == 0:
                # Try to extract voting data from soup
                voting_data = self._extract_voting_data_traditional(soup)
                if voting_data:
                    question.voting_data = voting_data

            return question

        except Exception as e:
            logger.error(f"Failed to validate question: {e}")
            return question

    def _parse_question_traditional(
        self, soup: BeautifulSoup, source_url: str, page_number: int
    ) -> Question | None:
        """Traditional parsing fallback method.

        Args:
            soup: BeautifulSoup object of the question card
            source_url: Source URL of the question
            page_number: Page number in the exam

        Returns:
            Question object or None if parsing failed
        """
        try:
            # Extract question number and ID
            question_number = self._extract_question_number(soup)
            if not question_number:
                return None

            question_id = f"question_{question_number}"

            # Extract question text
            question_text = self._extract_question_text(soup)
            if not question_text:
                return None

            # Extract choices
            choices = self._extract_choices(soup)
            if not choices:
                return None

            # Extract correct answer
            correct_answer = self._extract_correct_answer(soup)

            # Extract topic
            topic = self._extract_topic(soup) or "General"

            # Extract explanation
            explanation = self._extract_explanation(soup) or "" or ""

            # Extract voting data
            voting_data = self._extract_voting_data_traditional(soup)

            # Create metadata
            metadata = QuestionMetadata(
                extraction_timestamp=datetime.now(),
                source_url=source_url,
                page_number=page_number,
            )

            return Question(
                id=question_id,
                number=question_number,
                topic=topic,
                text=question_text,
                choices=choices,
                correct_answer=correct_answer,
                explanation=explanation,
                voting_data=voting_data,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Traditional parsing failed: {e}")
            return None

    def _extract_question_number(self, soup: BeautifulSoup) -> int | None:
        """Extract question number from HTML."""
        # Look for question number patterns
        patterns = [
            r"Question #(\d+)",
            r"Question (\d+)",
            r"Q(\d+)",
            r"#(\d+)",
        ]

        text = soup.get_text()
        import re

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))

        return None

    def _extract_question_text(self, soup: BeautifulSoup) -> str | None:
        """Extract question text from HTML."""
        # Common selectors for question text
        selectors = [
            ".question-text",
            ".question-body",
            ".question-content",
            "p.question",
            ".card-body p",
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)

        # Fallback: look for the longest paragraph
        paragraphs = soup.find_all("p")
        if paragraphs:
            longest = max(paragraphs, key=lambda p: len(p.get_text()))
            return longest.get_text(strip=True)

        return None

    def _extract_choices(self, soup: BeautifulSoup) -> list[Choice]:
        """Extract multiple choice options from HTML."""
        choices = []

        # Look for choice patterns
        choice_elements = soup.find_all(
            ["div", "li", "p"], class_=lambda x: x and "choice" in x.lower()
        )

        if not choice_elements:
            # Fallback: look for A., B., C., D. patterns
            text = soup.get_text()
            import re

            choice_pattern = r"([A-D])\.\s*([^\n]+)"
            matches = re.findall(choice_pattern, text)

            for letter, text in matches:
                choices.append(
                    Choice(
                        letter=letter,
                        text=text.strip(),
                        is_most_voted=False,
                        is_correct=False,
                    )
                )
        else:
            for elem in choice_elements:
                text = elem.get_text(strip=True)
                if text and len(text) > 2:
                    # Extract letter from text
                    letter = text[0] if text[0] in "ABCD" else "A"
                    choice_text = text[2:].strip() if len(text) > 2 else text

                    choices.append(
                        Choice(
                            letter=letter,
                            text=choice_text,
                            is_most_voted=False,
                            is_correct=False,
                        )
                    )

        return choices

    def _extract_correct_answer(self, soup: BeautifulSoup) -> str:
        """Extract correct answer from HTML."""
        # Look for correct answer indicators
        selectors = [
            ".correct-answer",
            ".answer",
            '[class*="correct"]',
            '[class*="answer"]',
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                if text and text[0] in "ABCD":
                    return text[0]

        return "A"  # Default fallback

    def _extract_topic(self, soup: BeautifulSoup) -> str:
        """Extract topic/section from HTML."""
        # Look for topic indicators
        selectors = [
            ".topic",
            ".section",
            ".category",
            "h3",
            "h4",
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                if text and len(text) < 100:  # Reasonable topic length
                    return text

        return ""

    def _extract_explanation(self, soup: BeautifulSoup) -> str:
        """Extract explanation from HTML."""
        # Look for explanation sections
        selectors = [
            ".explanation",
            ".answer-explanation",
            ".rationale",
            '[class*="explanation"]',
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)

        return ""

    def _extract_voting_data_traditional(self, soup: BeautifulSoup) -> VotingData:
        """Extract voting data using traditional parsing."""
        # Default voting data
        return VotingData(
            total_votes=0,
            vote_distribution={},
            most_voted_answer="A",
            confidence_score=0.0,
        )

    def parse_discussion(
        self, modal_soup: BeautifulSoup, question_id: str
    ) -> Discussion | None:
        """Extract discussion data using LangChain structured output.

        Args:
            modal_soup: BeautifulSoup object of the discussion modal
            question_id: Associated question ID

        Returns:
            Discussion object or None if extraction failed
        """
        if not modal_soup:
            return None

        try:
            html_content = str(modal_soup)

            # Try LLM extraction
            if self.settings.extraction.use_structured_output and self.llm:
                # Create the extraction chain
                extraction_chain = (
                    self.discussion_prompt | self.structured_discussion_llm
                )
                discussion = self._extract_with_retry(extraction_chain, html_content)

                if discussion:
                    discussion.question_id = question_id
                    discussion.extraction_timestamp = datetime.now()
                    return discussion

            # Fallback to traditional parsing
            return self._parse_discussion_traditional(modal_soup, question_id)

        except Exception as e:
            logger.error(f"Failed to parse discussion: {e}")
            return None

    def _parse_discussion_traditional(
        self, soup: BeautifulSoup, question_id: str
    ) -> Discussion:
        """Traditional discussion parsing fallback."""
        comments = []

        # Look for comment elements
        comment_elements = soup.find_all(
            ["div", "article"], class_=lambda x: x and "comment" in x.lower()
        )

        for i, elem in enumerate(comment_elements):
            comment = Comment(
                id=f"comment_{i + 1}",
                author="Anonymous",
                content=elem.get_text(strip=True)[:500],  # Limit content length
                upvotes=0,
                is_highly_voted=False,
                timestamp=datetime.now().isoformat(),
                replies=[],
            )
            comments.append(comment)

        return Discussion(
            question_id=question_id,
            total_comments=len(comments),
            comments=comments,
            extraction_timestamp=datetime.now(),
        )
