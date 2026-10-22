"""Typed errors and HTTP status mapping."""

from __future__ import annotations

from typing import ClassVar


class ArbiterError(Exception):
    http_status: ClassVar[int] = 500
    error_type: ClassVar[str] = "InternalError"

    def __init__(self, message: str, *, recoverable: bool = False) -> None:
        self.message = message
        self.recoverable = recoverable
        super().__init__(message)

    @property
    def type(self) -> str:
        return self.error_type


class ConfigError(ArbiterError):
    http_status = 500
    error_type = "ConfigError"


class UpstreamTimeout(ArbiterError):
    http_status = 504
    error_type = "UpstreamTimeout"
    recoverable = True


class UpstreamError(ArbiterError):
    http_status = 502
    error_type = "UpstreamError"
    recoverable = True


class Unauthorized(ArbiterError):
    http_status = 401
    error_type = "Unauthorized"


class Forbidden(ArbiterError):
    http_status = 403
    error_type = "Forbidden"


class OfflineProvider(ArbiterError):
    http_status = 503
    error_type = "OfflineProvider"
    recoverable = True


class ParseFailure(ArbiterError):
    http_status = 422
    error_type = "ParseFailure"


class GuardBlocked(ArbiterError):
    http_status = 422
    error_type = "GuardBlocked"


class PolicyError(ArbiterError):
    http_status = 500
    error_type = "PolicyError"


class PolicyIneligible(ArbiterError):
    http_status = 422
    error_type = "PolicyIneligible"

    def __init__(self, message: str, *, reasons: list[str] | None = None, recoverable: bool = False) -> None:
        self.reasons = list(reasons or [])
        super().__init__(message, recoverable=recoverable)


class ContractInvalid(ArbiterError):
    http_status = 409
    error_type = "ContractInvalid"


class BudgetExceeded(ArbiterError):
    http_status = 429
    error_type = "BudgetExceeded"
    recoverable = True


class NotFound(ArbiterError):
    http_status = 404
    error_type = "NotFound"


class ValidationFailed(ArbiterError):
    http_status = 400
    error_type = "ValidationFailed"


class NotImplemented(ArbiterError):
    http_status = 501
    error_type = "NotImplemented"


def http_status_for(exc: BaseException) -> int:
    if isinstance(exc, ArbiterError):
        return exc.http_status
    return 500
