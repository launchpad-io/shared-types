"""
Custom exceptions for the application
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class BaseCustomException(HTTPException):
    """Base exception class for custom exceptions"""
    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class NotFoundException(BaseCustomException):
    """Exception raised when a resource is not found"""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class UnauthorizedException(BaseCustomException):
    """Exception raised for unauthorized access"""
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenException(BaseCustomException):
    """Exception raised when access is forbidden"""
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class BadRequestException(BaseCustomException):
    """Exception raised for bad requests"""
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ValidationException(BaseCustomException):
    """Exception raised for validation errors"""
    def __init__(self, detail: Any = "Validation error"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class ConflictException(BaseCustomException):
    """Exception raised for conflicts (e.g., duplicate resources)"""
    def __init__(self, detail: str = "Conflict"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class BusinessLogicException(BaseCustomException):
    """Exception raised for business logic errors"""
    def __init__(self, detail: str = "Business logic error"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class RateLimitException(BaseCustomException):
    """Exception raised when rate limit is exceeded"""
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)


class InternalServerException(BaseCustomException):
    """Exception raised for internal server errors"""
    def __init__(self, detail: str = "Internal server error"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class ServiceUnavailableException(BaseCustomException):
    """Exception raised when a service is unavailable"""
    def __init__(self, detail: str = "Service unavailable"):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


class InsufficientPermissionsException(ForbiddenException):
    """Exception raised when user has insufficient permissions"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(detail=detail)


class InvalidTokenException(UnauthorizedException):
    """Exception raised for invalid tokens"""
    def __init__(self, detail: str = "Invalid token"):
        super().__init__(detail=detail)


class ExpiredTokenException(UnauthorizedException):
    """Exception raised for expired tokens"""
    def __init__(self, detail: str = "Token has expired"):
        super().__init__(detail=detail)


# Alias for backward compatibility
DuplicateException = ConflictException
InvalidRequestException = BadRequestException


__all__ = [
    "BaseCustomException",
    "NotFoundException",
    "UnauthorizedException",
    "ForbiddenException",
    "BadRequestException",
    "ValidationException",
    "ConflictException",
    "BusinessLogicException",
    "RateLimitException",
    "InternalServerException",
    "ServiceUnavailableException",
    "InsufficientPermissionsException",
    "InvalidTokenException",
    "ExpiredTokenException",
    "DuplicateException",
    "InvalidRequestException",
]