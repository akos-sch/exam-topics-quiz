"""Web scraper for ExamTopics website."""

import logging
import random
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ..config.settings import get_settings
from .auth import ExamTopicsAuth

logger = logging.getLogger(__name__)


class ExamTopicsScraper:
    """Web scraper for ExamTopics website with rate limiting and session management."""

    def __init__(self, base_url: str, rate_limit: float | None = None):
        """Initialize the scraper.

        Args:
            base_url: Base URL for the exam
            rate_limit: Seconds between requests (uses config default if None)
        """
        self.base_url = base_url
        self.settings = get_settings()
        self.rate_limit = rate_limit or self.settings.scraping.rate_limit
        self.last_request_time = 0

        # Setup session with proper headers
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.settings.scraping.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

        # Initialize authentication handler
        self.auth = ExamTopicsAuth(self.session)

    def login(self, username: str, password: str) -> tuple[bool, str]:
        """Login to ExamTopics with credentials.

        Args:
            username: ExamTopics username/email
            password: ExamTopics password

        Returns:
            Tuple of (success, message)
        """
        return self.auth.login(username, password)

    def is_authenticated(self) -> bool:
        """Check if currently authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        return self.auth.is_authenticated

    def get_auth_status(self) -> dict[str, str]:
        """Get authentication status information.

        Returns:
            Dictionary with authentication information
        """
        return self.auth.get_session_info()

    def _wait_for_rate_limit(self) -> None:
        """Implement rate limiting with jitter."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.rate_limit:
            # Add random jitter to avoid thundering herd
            jitter = random.uniform(0.1, 0.3)
            sleep_time = self.rate_limit - time_since_last + jitter
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _make_request(self, url: str, **kwargs) -> requests.Response:
        """Make a rate-limited HTTP request with retry logic.

        Args:
            url: URL to request
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            requests.RequestException: If request fails after all retries
        """
        self._wait_for_rate_limit()

        for attempt in range(self.settings.scraping.max_retries):
            try:
                logger.debug(f"Making request to {url} (attempt {attempt + 1})")

                response = self.session.get(
                    url, timeout=self.settings.scraping.timeout, **kwargs
                )

                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response

            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == self.settings.scraping.max_retries - 1:
                    raise

                # Exponential backoff
                sleep_time = 2**attempt + random.uniform(0, 1)
                time.sleep(sleep_time)

        raise requests.RequestException(
            f"Failed to fetch {url} after {self.settings.scraping.max_retries} attempts"
        )

    def get_page_content(self, url: str) -> BeautifulSoup:
        """Fetch and parse a single page.

        Args:
            url: URL to fetch

        Returns:
            BeautifulSoup object with parsed HTML
        """
        response = self._make_request(url)
        soup = BeautifulSoup(response.content, "html.parser")

        # Check for captcha or authentication issues
        captcha_solved, captcha_msg = self.auth.handle_captcha_page(response)
        if not captcha_solved:
            logger.warning(f"Captcha detected on {url}: {captcha_msg}")

        return soup

    def get_exam_pages(self, exam_url: str) -> list[str]:
        """Get all page URLs for an exam.

        Args:
            exam_url: Main exam URL

        Returns:
            List of page URLs
        """
        logger.info(f"Discovering pages for exam: {exam_url}")

        soup = self.get_page_content(exam_url)
        page_urls = [exam_url]  # Include the first page

        # Look for pagination links
        pagination = soup.find("div", class_="pagination") or soup.find(
            "nav", class_="pagination"
        )
        if pagination:
            page_links = pagination.find_all("a", href=True)
            for link in page_links:
                href = link["href"]
                if href and href not in ["#", "javascript:void(0)"]:
                    full_url = urljoin(exam_url, href)
                    if full_url not in page_urls:
                        page_urls.append(full_url)

        # Alternative: look for numbered page links
        if len(page_urls) == 1:
            page_links = soup.find_all("a", href=True)
            for link in page_links:
                href = link["href"]
                text = link.get_text(strip=True)

                # Look for numeric page links
                if text.isdigit() and href:
                    full_url = urljoin(exam_url, href)
                    if full_url not in page_urls:
                        page_urls.append(full_url)

        logger.info(f"Found {len(page_urls)} pages for exam")
        return sorted(set(page_urls))

    def get_question_cards(self, page_url: str) -> list[BeautifulSoup]:
        """Extract question cards from a page.

        Args:
            page_url: URL of the page to scrape

        Returns:
            List of BeautifulSoup objects for each question card (deduplicated)
        """
        logger.debug(f"Extracting question cards from {page_url}")

        soup = self.get_page_content(page_url)

        # More specific selectors for question cards on ExamTopics
        question_selectors = [
            "div.exam-question-card",  # Most specific for ExamTopics
            "div.card.exam-question-card",  # Alternative specific selector
            "div.question-card",
            "div.card.question",
            "div.exam-question",
            "article.question",
        ]

        question_cards = []
        for selector in question_selectors:
            cards = soup.select(selector)
            if cards:
                question_cards.extend(cards)
                break

        # Fallback: look for cards with question numbers - be more specific
        if not question_cards:
            all_divs = soup.find_all("div")
            for div in all_divs:
                text = div.get_text(strip=True)
                # Check for question patterns - be more specific
                if text.startswith("Question #") and (
                    "Topic" in text or "Question #" in text[:20]
                ):  # More specific pattern
                    question_cards.append(div)

        # Deduplicate question cards based on question numbers
        unique_cards = []
        seen_question_numbers = set()

        import re

        for card in question_cards:
            # Extract question number from the card
            card_text = card.get_text()
            question_number = None

            # Look for question number patterns
            patterns = [
                r"Question #(\d+)",
                r"Question (\d+)",
                r"Q(\d+)",
                r"#(\d+)",
            ]

            for pattern in patterns:
                match = re.search(pattern, card_text)
                if match:
                    question_number = int(match.group(1))
                    break

            # Only add if we haven't seen this question number before
            if question_number and question_number not in seen_question_numbers:
                seen_question_numbers.add(question_number)
                unique_cards.append(card)
            elif question_number is None:
                # If we can't extract a question number, include it anyway
                # (but this shouldn't happen with proper question cards)
                unique_cards.append(card)

        logger.debug(f"Found {len(unique_cards)} unique question cards")
        return unique_cards

    def get_question_details(self, question_id: str, question_url: str) -> dict | None:
        """Fetch detailed question data including discussions.

        Args:
            question_id: Question identifier
            question_url: URL for the detailed question page

        Returns:
            Dictionary with question details or None if failed
        """
        try:
            logger.debug(f"Fetching details for question {question_id}")

            soup = self.get_page_content(question_url)

            # Extract discussion modal or comments section
            discussion_content = None

            # Look for discussion/comments sections
            discussion_selectors = [
                "div.discussion",
                "div.comments",
                "div.modal-body",
                'div[id*="discussion"]',
                'div[id*="comments"]',
            ]

            for selector in discussion_selectors:
                discussion_elem = soup.select_one(selector)
                if discussion_elem:
                    discussion_content = discussion_elem
                    break

            return {
                "question_id": question_id,
                "page_content": soup,
                "discussion_content": discussion_content,
                "url": question_url,
            }

        except Exception as e:
            logger.error(f"Failed to fetch details for question {question_id}: {e}")
            return None

    def extract_voting_data(self, soup: BeautifulSoup) -> dict | None:
        """Extract voting data from page scripts or elements.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            Dictionary with voting data or None if not found
        """
        try:
            # Look for JSON data in script tags
            scripts = soup.find_all("script", type="application/json")
            for script in scripts:
                if "vote" in script.get_text().lower():
                    return {"json_content": script.get_text()}

            # Look for vote count elements
            vote_elements = soup.find_all(
                ["span", "div"], class_=lambda x: x and "vote" in x.lower()
            )
            if vote_elements:
                vote_data = {}
                for elem in vote_elements:
                    text = elem.get_text(strip=True)
                    if text and any(char.isdigit() for char in text):
                        vote_data[elem.get("class", ["unknown"])[0]] = text
                return vote_data

            return None

        except Exception as e:
            logger.error(f"Failed to extract voting data: {e}")
            return None

    def close(self) -> None:
        """Close the session and cleanup resources."""
        if self.session:
            self.session.close()
