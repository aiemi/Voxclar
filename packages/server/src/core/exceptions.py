from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code


class NotFound(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404)


class Unauthorized(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, 401)


class Forbidden(AppException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, 403)


class BadRequest(AppException):
    def __init__(self, message: str = "Bad request"):
        super().__init__(message, 400)


class InsufficientPoints(AppException):
    def __init__(self, message: str = "Insufficient points"):
        super().__init__(message, 402)


class Conflict(AppException):
    def __init__(self, message: str = "Conflict"):
        super().__init__(message, 409)


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message},
        )
