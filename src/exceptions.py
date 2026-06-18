class BaseException(Exception):
    """This is the base class for all ARCIP errors"""

    pass


class UnprocessableEntity(BaseException):
    """
    Raised when the request is well-formed but contains semantic errors
    that prevent processing.

    Examples:
    - Competitor already exists for this user
    - Feedback already submitted for this report
    - Invalid schedule state transition

    Use this for general 422 errors when more specific exceptions don't apply.
    """

    def __init__(
        self,
        message: str = "The request could not be processed due to validation errors",
        err_code: str = "unprocessable_entity",
    ):
        self.message = message
        self.err_code = err_code
        super().__init__(self.message)


class InsufficientPermission(BaseException):
    """
    Raised when a resource does not belong to the current user,
    or an admin-only endpoint is accessed by a non-admin.
    """

    def __init__(
        self,
        message: str = "You do not have sufficient permissions to perform this action",
    ):
        self.message = message
        super().__init__(self.message)


class NotFound(BaseException):
    """
    Generic not found exception — used for competitor, report, alert,
    and schedule lookups that fail or don't belong to the current user.
    """

    def __init__(self, message: str = "Resource not found"):
        self.message = message
        super().__init__(self.message)


# Auth errors — raised during Google OAuth verification or JWT decoding

class AuthError(BaseException):
    """
    Raised when a request's JWT is missing, invalid, or expired.

    Response: 401 to frontend with "Please log in again" message.
    """
    def __init__(self, message: str = "Authentication failed. Please log in again."):
        self.message = message
        super().__init__(message)


# Rate limiting — on-demand research job limit

class RateLimitExceeded(BaseException):
    """
    Raised when a user exceeds the on-demand research trigger limit
    (10 jobs per user per day — enforced via Redis counter).
    """
    def __init__(
        self,
        message: str = "You've reached today's limit of 10 on-demand research jobs.",
    ):
        self.message = message
        super().__init__(message)


# External service errors — raised when Tavily, Serper, Apify, or Resend fail

class ServiceError(BaseException):
    """
    Raised when an external API call (Tavily, Serper, Apify, Resend)
    fails after all retries.

    When a specific data source fails, the data_fetcher node continues
    with whatever other sources it has rather than failing the whole job.
    """
    def __init__(self, message: str = "A backend service is unavailable"):
        self.message = message
        super().__init__(message)


# Agent errors — raised when the LangGraph research pipeline fails

class AgentError(BaseException):
    """
    Raised when both the primary synthesis model (Claude Sonnet) AND the
    fallback model (DeepSeek V3) fail.

    Response: 503 to frontend with "Research agent is currently unavailable" message.
    """
    def __init__(self, message: str = "Research agent is currently unavailable"):
        self.message = message
        super().__init__(message)


# Research job errors — raised when a Celery job fails after all retries

class ResearchJobError(BaseException):
    """
    Raised when a Celery research job fails after all retries are exhausted.
    The job's status is updated to "failed" in PostgreSQL before this is raised.
    """
    def __init__(self, message: str = "The research job failed. Please try again."):
        self.message = message
        super().__init__(message)


# Guardrail errors — raised when scraped content or generated reports fail safety checks

class GuardrailError(BaseException):
    """
    Base class for both input and output guardrail failures.
    Handled internally inside the agent pipeline — not normally surfaced
    as an HTTP error to the end user.
    """
    def __init__(self, message: str = "Content failed safety check"):
        self.message = message
        super().__init__(message)


class PromptInjectionError(GuardrailError):
    """
    Raised when scraped competitor content contains instruction-like text
    that could hijack the synthesis LLM — e.g. "Ignore previous instructions."

    Inherits from GuardrailError → also caught by `except GuardrailError`.
    We strip the content and log the event rather than failing the job.
    """
    def __init__(self, message: str = "Potential prompt injection detected in scraped content"):
        self.message = message
        super().__init__(message)


class OutputGuardrailError(GuardrailError):
    """
    Raised when a generated report fails an output check:
    - Under 500 words
    - Zero source citations
    - Missing required sections (SWOT, trends, executive summary)

    Triggers a retry in the synthesiser node. After max retries, the report
    is delivered with a visible confidence warning instead of being blocked.
    """
    def __init__(self, message: str = "Generated report did not pass quality checks"):
        self.message = message
        super().__init__(message)
        
class NotAuthenticated(BaseException):
    """User is not authenticated"""
    def __init__(self, message: str = "Not Authenticated"):
            self.message = message
            super().__init__(message)


class InvalidToken(BaseException):
    """User has provided an invalid or expired token"""

    def __init__(self, message: str = "Invalid token or token expired"):
        self.message = message
        super().__init__(message)

class AccessTokenRequired(BaseException):
    """User has provided a refresh token when an access token is needed"""

    def __init__(self, message: str = "Access token required"):
        self.message = message
        super().__init__(message)


class RefreshTokenRequired(BaseException):
    """User has provided an access token when a refresh token is needed"""

    def __init__(self, message: str = "Refresh token required"):
        self.message = message
        super().__init__(message)