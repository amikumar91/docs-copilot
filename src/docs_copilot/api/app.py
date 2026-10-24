from fastapi import FastAPI

from docs_copilot import __version__
from docs_copilot.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="docs-copilot", version=__version__)
    app.include_router(health_router)
    return app


app = create_app()
