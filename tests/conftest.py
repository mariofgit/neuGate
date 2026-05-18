import json
import shutil
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from neugate.main import create_app
from neugate.models.config import ProjectConfig
from neugate.models.policy import ConsumerPolicy
from neugate.services.config_loader import ConfigLoader
from neugate.settings import Settings, get_settings

TEST_BRAND_ID = "test-brand"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def test_brand_id() -> str:
    return TEST_BRAND_ID


@pytest.fixture
def project_config(test_brand_id: str) -> ProjectConfig:
    payload = json.loads((FIXTURES_DIR / "projects" / f"{test_brand_id}.json").read_text(encoding="utf-8"))
    return ProjectConfig.model_validate(payload)


@pytest.fixture
def consumer_policy(project_config: ProjectConfig) -> ConsumerPolicy:
    return ConsumerPolicy.from_project_config(project_config)


@pytest.fixture
def config_dir(tmp_path: Path, test_brand_id: str) -> Path:
    schema_dst = tmp_path / "schema" / "neugate-schema.json"
    schema_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / "config/schema/neugate-schema.json", schema_dst)

    projects = tmp_path / "projects"
    projects.mkdir()
    shutil.copyfile(
        FIXTURES_DIR / "projects" / f"{test_brand_id}.json",
        projects / f"{test_brand_id}.json",
    )
    return tmp_path


@pytest.fixture
def settings(config_dir: Path) -> Settings:
    return Settings.model_validate(
        {
            "OPENAI_API_KEY": "test-key",
            "NEUGATE_API_KEY": "",
            "config_dir": str(config_dir / "projects"),
            "schema_path": str(config_dir / "schema" / "neugate-schema.json"),
            "test_runner_max_cases": 100,
            "test_runner_concurrency": 5,
            "NEUGATE_AGENTIC_ENABLED": False,
        }
    )


@pytest.fixture(autouse=True)
def disable_production_api_key_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests run without NEUGATE_API_KEY unless a test opts into secured_app."""
    # Empty env var overrides values loaded from neuGate/.env during local dev.
    monkeypatch.setenv("NEUGATE_API_KEY", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def config_loader(settings: Settings) -> ConfigLoader:
    return ConfigLoader(settings=settings)


@pytest.fixture
def app():
    application = create_app()
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
async def api_client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(autouse=True)
def reset_service_singletons() -> None:
    import neugate.agentic.bootstrap as agentic_mod
    import neugate.services.evaluate as evaluate_mod
    import neugate.services.config_loader as config_mod
    import neugate.services.classifier as classifier_mod
    import neugate.services.test_runner as test_runner_mod

    agentic_mod.clear_agentic_gate()
    evaluate_mod._evaluate_service = None
    config_mod._config_loader = None
    classifier_mod._classifier = None
    test_runner_mod._batch_runner_service = None
    yield
    agentic_mod.clear_agentic_gate()
    evaluate_mod._evaluate_service = None
    config_mod._config_loader = None
    classifier_mod._classifier = None
    test_runner_mod._batch_runner_service = None
