from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from neugate import __version__
from neugate.services.config_loader import ConfigLoader, get_config_loader
from neugate.services.readiness import ReadinessReport, check_readiness
from neugate.settings import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness — process is running (no dependency checks)."""
    return {"status": "ok", "service": "neugate", "version": __version__}


@router.get("/health/ready")
async def readiness(
    settings: Settings = Depends(get_settings),
    config_loader: ConfigLoader = Depends(get_config_loader),
) -> JSONResponse:
    """Readiness — can serve traffic (OpenAI key + at least one valid project config)."""
    report: ReadinessReport = check_readiness(settings=settings, config_loader=config_loader)
    body = {
        "status": "ready" if report.ready else "not_ready",
        "service": "neugate",
        "version": __version__,
        "checks": report.checks,
        "loadable_projects": report.loadable_projects,
        "details": report.details,
    }
    status_code = 200 if report.ready else 503
    return JSONResponse(status_code=status_code, content=body)
