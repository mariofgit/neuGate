from __future__ import annotations

from dataclasses import dataclass, field

from neugate.agentic.bootstrap import get_agentic_gate
from neugate.services.config_loader import ConfigLoader, get_config_loader
from neugate.settings import Settings, get_settings


@dataclass
class ReadinessReport:
    ready: bool
    checks: dict[str, bool] = field(default_factory=dict)
    details: list[str] = field(default_factory=list)
    loadable_projects: list[str] = field(default_factory=list)


def check_readiness(
    settings: Settings | None = None,
    config_loader: ConfigLoader | None = None,
) -> ReadinessReport:
    settings = settings or get_settings()
    config_loader = config_loader or get_config_loader()

    checks: dict[str, bool] = {}
    details: list[str] = []

    checks["openai_api_key"] = bool(settings.openai_api_key.strip())
    if not checks["openai_api_key"]:
        details.append("OPENAI_API_KEY is not set")

    loadable: list[str] = []
    if config_loader.config_dir.is_dir() and config_loader.schema_path.is_file():
        loadable = config_loader.list_loadable_project_ids()
    checks["legacy_configs_present"] = len(loadable) > 0

    checks["agentic_enabled"] = settings.agentic_enabled
    if settings.agentic_enabled:
        gate = get_agentic_gate()
        index_loaded = gate is not None and gate.index.index.ntotal > 0
        checks["agentic_index_loaded"] = index_loaded
        if not index_loaded:
            if not settings.agentic_index_path.is_file():
                details.append(f"Agentic index missing: {settings.agentic_index_path}")
            else:
                details.append("Agentic enabled but index not loaded (run startup warm-up)")
    else:
        checks["agentic_index_loaded"] = True

    ready = checks["openai_api_key"] and checks["agentic_index_loaded"]

    return ReadinessReport(
        ready=ready,
        checks=checks,
        details=details,
        loadable_projects=loadable,
    )
