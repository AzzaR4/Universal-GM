"""Domain-level exceptions."""
from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain errors."""

    status_code: int = 400


class NotFoundError(DomainError):
    status_code = 404


class ValidationError(DomainError):
    status_code = 422


class RuleViolationError(DomainError):
    """Raised when an action violates the ruleset (e.g. dead character acts)."""

    status_code = 409


class AIProviderError(DomainError):
    """Raised when the configured AI provider is missing or unreachable."""

    status_code = 503


class ImportError_(DomainError):
    status_code = 422
