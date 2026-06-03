from fastapi import Request
from fastapi.responses import JSONResponse

from nam_api.exceptions import AppError


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
