from fastapi import FastAPI

from nam_api.error_handlers import app_error_handler
from nam_api.exceptions import AppError
from nam_api.routers import health, indices, portfolio, profile


def create_app() -> FastAPI:
    app = FastAPI(title="Nestor Asset Manager API")
    app.add_exception_handler(AppError, app_error_handler)
    routers = [
        health.router,
        profile.router,
        indices.router,
        portfolio.transactions_router,
        portfolio.positions_router,
    ]
    for router in routers:
        app.include_router(router)
    return app


app = create_app()
