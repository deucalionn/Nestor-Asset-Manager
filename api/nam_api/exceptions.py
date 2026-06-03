class AppError(Exception):
    """Base application error with HTTP mapping."""

    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class UnprocessableError(AppError):
    status_code = 422


class SetupRequiredError(NotFoundError):
    detail = "User profile not initialized — call POST /setup first"


class AlreadyInitializedError(ConflictError):
    detail = "User profile already initialized"


class InsufficientQuantityError(UnprocessableError):
    detail = "Insufficient quantity for SELL transaction"
