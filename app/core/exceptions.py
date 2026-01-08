from typing import Any, Dict, Optional

from fastapi import HTTPException, status


class BusinessException(HTTPException):
    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": code,
                "message": message,
                "details": details,
            },
        )


class NotFoundException(HTTPException):
    def __init__(self, message: str = "Data tidak ditemukan"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": message},
        )


class ForbiddenException(HTTPException):
    def __init__(self, message: str = "Kamu tidak punya izin untuk aksi ini"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": message},
        )


class UnauthorizedException(HTTPException):
    def __init__(self, message: str = "Silakan login terlebih dahulu"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": message},
            headers={"WWW-Authenticate": "Bearer"},
        )


class RateLimitException(HTTPException):
    def __init__(self, message: str = "Terlalu banyak permintaan. Coba lagi nanti."):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMIT_EXCEEDED", "message": message},
        )


class ValidationException(HTTPException):
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "VALIDATION_ERROR",
                "message": message,
                "field": field,
                "details": details,
            },
        )
