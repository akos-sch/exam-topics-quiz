"""ExamTopics website authentication and session management."""

import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ExamTopicsAuth:
    """Handles authentication and session management for ExamTopics website."""

    def __init__(self, session: requests.Session):
        """Initialize with an existing requests session.

        Args:
            session: Requests session to use for authentication
        """
        self.session = session
        self.is_authenticated = False
        self.login_url = "https://www.examtopics.com/login"
        self.csrf_token = None

    def get_csrf_token(self) -> str | None:
        """Extract CSRF token from login page.

        Returns:
            CSRF token if found, None otherwise
        """
        try:
            response = self.session.get(self.login_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Look for CSRF token in meta tags
            csrf_meta = soup.find("meta", {"name": "csrf-token"})
            if csrf_meta:
                self.csrf_token = csrf_meta.get("content")
                return self.csrf_token

            # Look for CSRF token in hidden form fields
            csrf_input = soup.find("input", {"name": "authenticity_token"})
            if csrf_input:
                self.csrf_token = csrf_input.get("value")
                return self.csrf_token

            logger.warning("CSRF token not found on login page")
            return None

        except Exception as e:
            logger.error(f"Failed to get CSRF token: {e}")
            return None

    def login(self, username: str, password: str) -> tuple[bool, str]:
        """Attempt to login to ExamTopics.

        Args:
            username: ExamTopics username/email
            password: ExamTopics password

        Returns:
            Tuple of (success, message)
        """
        try:
            # Get CSRF token first
            logger.debug(f"Attempting to get CSRF token from {self.login_url}")
            if not self.get_csrf_token():
                logger.warning("Failed to get CSRF token, continuing without it")

            # Prepare login data
            login_data = {
                "user[email]": username,
                "user[password]": password,
                "user[remember_me]": "1",
                "commit": "Log in",
            }

            if self.csrf_token:
                login_data["authenticity_token"] = self.csrf_token
                logger.debug(f"Using CSRF token: {self.csrf_token[:10]}...")

            logger.debug(
                f"Submitting login form with data keys: {list(login_data.keys())}"
            )

            # Submit login form
            response = self.session.post(
                self.login_url, data=login_data, allow_redirects=True
            )

            logger.debug(
                f"Login POST response: {response.status_code}, URL: {response.url}"
            )

            # Check if login was successful
            auth_status = self.check_authentication_status()
            logger.debug(f"Authentication status check result: {auth_status}")

            if auth_status:
                self.is_authenticated = True
                logger.info("Successfully logged in to ExamTopics")
                return True, "Login successful"
            else:
                # Check for specific error messages
                soup = BeautifulSoup(response.content, "html.parser")

                # Look for various error message patterns
                error_selectors = [
                    "div.alert-danger",
                    "div.error",
                    "div.alert.alert-danger",
                    ".flash-error",
                    ".error-message",
                    '[class*="error"]',
                ]

                error_msg = "Login failed"
                for selector in error_selectors:
                    error_elem = soup.select_one(selector)
                    if error_elem:
                        error_msg = error_elem.get_text(strip=True)
                        logger.debug(
                            f"Found error message with selector '{selector}': {error_msg}"
                        )
                        break

                # Also check if we're still on login page
                if "login" in response.url.lower():
                    error_msg += " (redirected back to login page)"

                # Log response content for debugging (first 500 chars)
                logger.debug(
                    f"Login response content preview: {response.text[:500]}..."
                )

                logger.warning(f"Login failed: {error_msg}")
                return False, error_msg

        except Exception as e:
            logger.error(f"Login attempt failed: {e}")
            return False, f"Login error: {e}"

    def check_authentication_status(self) -> bool:
        """Check if currently authenticated by testing access to a protected page.

        Returns:
            True if authenticated, False otherwise
        """
        try:
            # Try to access a page that requires authentication
            test_url = "https://www.examtopics.com/exams/"
            logger.debug(f"Checking authentication status by accessing: {test_url}")
            response = self.session.get(test_url)

            logger.debug(
                f"Auth check response: {response.status_code}, URL: {response.url}"
            )

            # Check if we're redirected to login page
            if "login" in response.url.lower():
                logger.debug("Redirected to login page - not authenticated")
                return False

            # Check for authentication indicators in the page
            soup = BeautifulSoup(response.content, "html.parser")

            # Look for user menu or logout link
            user_indicators = [
                ('a[href="/logout"]', soup.find("a", href="/logout")),
                (
                    'a[href*="logout"]',
                    soup.find("a", href=lambda x: x and "logout" in x),
                ),
                ('a:contains("Logout")', soup.find("a", string="Logout")),
                ("div.user-menu", soup.find("div", class_="user-menu")),
                ("span.username", soup.find("span", class_="username")),
                (".user-profile", soup.select_one(".user-profile")),
                (".user-info", soup.select_one(".user-info")),
                ('[class*="user"]', soup.select_one('[class*="user"]')),
            ]

            found_indicators = []
            for indicator_name, indicator_elem in user_indicators:
                if indicator_elem:
                    found_indicators.append(indicator_name)
                    logger.debug(f"Found authentication indicator: {indicator_name}")

            if found_indicators:
                logger.debug(
                    f"Authentication confirmed by indicators: {found_indicators}"
                )
                return True
            else:
                logger.debug("No authentication indicators found")
                # Log some page content for debugging
                page_text = soup.get_text()[:200] if soup else "No content"
                logger.debug(f"Page content preview: {page_text}...")

                # Check for specific text that might indicate authentication
                auth_text_indicators = [
                    "dashboard",
                    "profile",
                    "account",
                    "premium",
                    "subscription",
                ]
                found_text = [
                    text for text in auth_text_indicators if text in page_text.lower()
                ]
                if found_text:
                    logger.debug(f"Found potential auth text indicators: {found_text}")

                return False

        except Exception as e:
            logger.error(f"Failed to check authentication status: {e}")
            return False

    def handle_captcha_page(self, response: requests.Response) -> tuple[bool, str]:
        """Handle captcha challenge if present.

        Args:
            response: Response that may contain captcha

        Returns:
            Tuple of (captcha_solved, message)
        """
        soup = BeautifulSoup(response.content, "html.parser")

        # Check if captcha is present
        captcha_elements = [
            soup.find("div", class_="captcha-container"),
            soup.find("div", id="captcha"),
            soup.find("iframe", src=lambda x: x and "recaptcha" in x),
        ]

        if any(captcha_elements):
            logger.warning("Captcha detected on page")
            return False, (
                "Captcha detected. Please solve the captcha manually in a browser "
                "and then retry the extraction, or consider using a premium ExamTopics account."
            )

        return True, "No captcha detected"

    def get_session_info(self) -> dict[str, str]:
        """Get information about the current session.

        Returns:
            Dictionary with session information
        """
        info = {
            "authenticated": str(self.is_authenticated),
            "csrf_token": self.csrf_token or "None",
            "cookies": str(len(self.session.cookies)),
        }

        if self.is_authenticated:
            try:
                # Try to get user info from profile page
                profile_response = self.session.get(
                    "https://www.examtopics.com/profile"
                )
                if profile_response.status_code == 200:
                    soup = BeautifulSoup(profile_response.content, "html.parser")
                    username_elem = soup.find("span", class_="username") or soup.find(
                        "h1"
                    )
                    if username_elem:
                        info["username"] = username_elem.get_text(strip=True)
            except Exception:
                pass

        return info

    def logout(self) -> bool:
        """Logout from ExamTopics.

        Returns:
            True if logout successful, False otherwise
        """
        try:
            logout_url = "https://www.examtopics.com/logout"
            response = self.session.post(logout_url)

            self.is_authenticated = False
            self.csrf_token = None

            logger.info("Logged out from ExamTopics")
            return True

        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False
