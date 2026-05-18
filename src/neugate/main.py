import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from neugate import __version__
from neugate.agentic.bootstrap import clear_agentic_gate, warm_agentic_stack
from neugate.routes import evaluate_router, health_router, test_runner_router
from neugate.security import verify_api_key
from neugate.settings import Settings, get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    if settings.agentic_enabled:
        await asyncio.to_thread(warm_agentic_stack, settings)
    yield
    clear_agentic_gate()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="NeuGate",
        description="Semantic filter proxy — pre-backend safety and intent gate",
        version=__version__,
        lifespan=lifespan,
    )
    app.include_router(health_router)
    app.include_router(evaluate_router, dependencies=[Depends(verify_api_key)])
    app.include_router(test_runner_router, dependencies=[Depends(verify_api_key)])
    app.state.settings = settings
    return app


app = create_app()


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "neugate.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=False,
    )


if __name__ == "__main__":
    run()
