import pytest

from neugate.services.config_loader import ConfigLoader
from neugate.services.readiness import check_readiness
from neugate.settings import Settings

pytestmark = pytest.mark.unit


def test_check_readiness_all_green(config_loader: ConfigLoader, settings: Settings) -> None:
    report = check_readiness(settings=settings, config_loader=config_loader)
    assert report.ready is True
    assert "test-brand" in report.loadable_projects


def test_check_readiness_missing_openai_key(config_loader: ConfigLoader, settings: Settings) -> None:
    settings = settings.model_copy(update={"openai_api_key": ""})
    report = check_readiness(settings=settings, config_loader=config_loader)
    assert report.ready is False
    assert report.checks["openai_api_key"] is False
