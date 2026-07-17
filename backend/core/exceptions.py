"""App-wide exception hierarchy + FastAPI exception handlers.

Every handler returns the same envelope: {"error": <slug>, "message": <human text>, "request_id": <id>}
so API consumers can branch on `error` without parsing prose.
"""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.logging import get_logger, request_id_ctx

logger = get_logger(__name__)


class AppError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    error_code: str = "app_error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"


class ValidationFailedError(AppError):
    status_code = 422  # Starlette's named constant for this was renamed across versions
    error_code = "validation_failed"


class UnsupportedFormatError(AppError):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    error_code = "unsupported_format"


class FileTooLargeError(AppError):
    status_code = 413  # Starlette's named constant for this was renamed across versions
    error_code = "file_too_large"


class InvalidJobStateError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "invalid_job_state"


class StorageError(AppError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "storage_error"


class DetectorUnavailableError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "detector_unavailable"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "unauthorized"


def _envelope(error_code: str, message: str) -> dict:
    return {"error": error_code, "message": message, "request_id": request_id_ctx.get()}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("%s: %s", exc.error_code, exc.message)
        return JSONResponse(status_code=exc.status_code, content=_envelope(exc.error_code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_envelope("validation_failed", str(exc.errors())),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("internal_error", "An unexpected error occurred."),
        )
