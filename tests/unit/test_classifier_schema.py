import pytest

from neugate.services.classifier import ClassifierService
from helpers import TEST_SETTINGS

pytestmark = pytest.mark.unit


def test_response_schema_includes_safe_domain_and_block_labels(project_config) -> None:
    service = ClassifierService(settings=TEST_SETTINGS)
    schema = service._build_response_schema(project_config)
    category_enum = schema["properties"]["category"]["enum"]

    assert category_enum[0] == "safe_domain"
    assert "illegal" in category_enum
    assert "off_topic" in category_enum
    assert "hacking" in category_enum
