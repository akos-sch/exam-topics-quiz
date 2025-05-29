"""Google Cloud Platform configuration and authentication helpers."""

import os

from pydantic import BaseModel, Field


class GCPConfig(BaseModel):
    """Google Cloud Platform configuration."""

    project_id: str | None = Field(default=None, description="GCP project ID")
    location: str = Field(default="us-central1", description="GCP region")
    credentials_path: str | None = Field(
        default=None, description="Path to service account key"
    )

    @classmethod
    def from_environment(cls) -> "GCPConfig":
        """Create GCP config from environment variables."""
        return cls(
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_REGION", "us-central1"),
            credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        )


def get_gcp_config() -> GCPConfig:
    """Get GCP configuration from environment."""
    return GCPConfig.from_environment()


def setup_gcp_auth() -> None:
    """Setup Google Cloud authentication.

    This function ensures that Google Application Default Credentials are available.
    It will use the following authentication methods in order:
    1. GOOGLE_APPLICATION_CREDENTIALS environment variable
    2. gcloud auth application-default credentials
    3. Compute Engine/Cloud Run service account
    """
    config = get_gcp_config()

    if config.credentials_path and os.path.exists(config.credentials_path):
        # Service account key file is available
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.credentials_path
        return

    # Check if gcloud ADC is available
    try:
        import google.auth

        credentials, project = google.auth.default()
        if project and not config.project_id:
            os.environ["GOOGLE_CLOUD_PROJECT"] = project
    except Exception:
        # ADC not available, will rely on runtime environment
        pass


def validate_gcp_setup() -> bool:
    """Validate that GCP is properly configured for Vertex AI.

    Returns:
        True if GCP is properly configured, False otherwise.
    """
    try:
        import google.auth
        from google.auth.exceptions import DefaultCredentialsError

        credentials, project = google.auth.default()
        return credentials is not None
    except (ImportError, DefaultCredentialsError):
        return False
