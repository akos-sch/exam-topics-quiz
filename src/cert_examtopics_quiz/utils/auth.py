"""Authentication utilities for GCP and other services."""

import logging
import os

logger = logging.getLogger(__name__)


def setup_authentication() -> bool:
    """Setup authentication for all required services.

    Returns:
        True if authentication is successful, False otherwise.
    """
    try:
        # Setup Google Cloud authentication
        return setup_gcp_authentication()
    except Exception as e:
        logger.error(f"Failed to setup authentication: {e}")
        return False


def setup_gcp_authentication() -> bool:
    """Setup Google Cloud Platform authentication.

    Returns:
        True if GCP authentication is successful, False otherwise.
    """
    try:
        import google.auth
        from google.auth.exceptions import DefaultCredentialsError

        # Try to get default credentials
        credentials, project = google.auth.default()

        if credentials:
            logger.info("Google Cloud authentication successful")
            if project:
                logger.info(f"Using GCP project: {project}")
                # Set project environment variable if not already set
                if not os.getenv("GOOGLE_CLOUD_PROJECT"):
                    os.environ["GOOGLE_CLOUD_PROJECT"] = project
            return True
        else:
            logger.warning("Google Cloud credentials not found")
            return False

    except DefaultCredentialsError:
        logger.error(
            "Google Cloud credentials not found. Please run 'gcloud auth application-default login' "
            "or set GOOGLE_APPLICATION_CREDENTIALS environment variable."
        )
        return False
    except ImportError:
        logger.error("Google Cloud libraries not installed")
        return False
    except Exception as e:
        logger.error(f"Failed to setup GCP authentication: {e}")
        return False


def validate_authentication() -> tuple[bool, str | None]:
    """Validate that all required authentication is in place.

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Validate GCP authentication
        gcp_valid, gcp_error = validate_gcp_authentication()
        if not gcp_valid:
            return False, gcp_error

        return True, None

    except Exception as e:
        return False, f"Authentication validation failed: {e}"


def validate_gcp_authentication() -> tuple[bool, str | None]:
    """Validate Google Cloud Platform authentication.

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        import google.auth
        from google.auth.exceptions import DefaultCredentialsError

        credentials, project = google.auth.default()

        if not credentials:
            return False, "Google Cloud credentials not found"

        # Try to validate credentials by making a simple API call
        try:
            # This will validate that the credentials work
            credentials.refresh(google.auth.transport.requests.Request())
        except Exception as e:
            return False, f"Google Cloud credentials are invalid: {e}"

        return True, None

    except DefaultCredentialsError:
        return False, (
            "Google Cloud credentials not configured. "
            "Please run 'gcloud auth application-default login' or set GOOGLE_APPLICATION_CREDENTIALS."
        )
    except ImportError:
        return False, "Google Cloud libraries not installed"
    except Exception as e:
        return False, f"GCP authentication validation failed: {e}"


def get_gcp_project_id() -> str | None:
    """Get the current GCP project ID.

    Returns:
        Project ID if available, None otherwise.
    """
    try:
        import google.auth

        credentials, project = google.auth.default()
        return project
    except Exception:
        return os.getenv("GOOGLE_CLOUD_PROJECT")
