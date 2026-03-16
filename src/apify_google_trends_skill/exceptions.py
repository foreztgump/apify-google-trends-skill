# src/apify_google_trends_skill/exceptions.py
"""Custom exception hierarchy for Apify API errors."""


class ApifyError(Exception):
    """Base exception for all Apify-related errors."""


class ApifyAuthError(ApifyError):
    """Raised when the API token is missing or invalid (401/403)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ApifyAPIError(ApifyError):
    """Raised for non-2xx API responses not covered by other exceptions."""

    def __init__(self, message: str, status_code: int, response_body: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ApifyTimeoutError(ApifyError):
    """Raised when both sync and async polling are exhausted."""


class ApifyActorError(ApifyError):
    """Raised when the actor run reaches a terminal failure status."""

    def __init__(self, message: str, run_status: str, run_id: str = "") -> None:
        super().__init__(message)
        self.run_status = run_status
        self.run_id = run_id
