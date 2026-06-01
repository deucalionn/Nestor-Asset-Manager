from fastapi import FastAPI

from nam_api.routers import health


def create_app() -> FastAPI:
    app = FastAPI(title="Nestor Asset Manager API")
    app.include_router(health.router)
    return app


app = create_app()
