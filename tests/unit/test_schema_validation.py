"""Schema validation — client JSON must conform to neugate-schema.json before load."""

from __future__ import annotations

import json

import pytest

from neugate.models.config import ProjectConfig
from neugate.services.config_loader import (
    ConfigLoader,
    ProjectConfigNotFoundError,
    ProjectConfigValidationError,
)

pytestmark = pytest.mark.unit


def _write_config(loader: ConfigLoader, project_id: str, payload: dict) -> None:
    path = loader.config_dir / f"{project_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")


def _valid_payload(project_id: str = "test-brand") -> dict:
    return {
        "project_id": project_id,
        "version": "test-1.0.0",
        "categories": {
            "critical_blocks": ["illegal"],
            "soft_blocks": ["off_topic"],
        },
        "persona_pivot": {
            "strategy": "rotation",
            "templates": ["Pivot one"],
        },
    }


class TestSchemaValidationHappyPath:
    def test_loads_test_brand_fixture(self, config_loader: ConfigLoader, test_brand_id: str) -> None:
        config = config_loader.load(test_brand_id)
        assert config.project_id == test_brand_id
        assert "illegal" in config.categories.critical_blocks
        assert len(config.persona_pivot.templates) >= 1

    def test_hot_reload_when_file_content_changes(
        self,
        config_loader: ConfigLoader,
        test_brand_id: str,
    ) -> None:
        path = config_loader.config_dir / f"{test_brand_id}.json"
        first = config_loader.load(test_brand_id)
        assert first.version == "test-1.0.0"

        data = json.loads(path.read_text(encoding="utf-8"))
        data["version"] = "test-1.0.1"
        path.write_text(json.dumps(data), encoding="utf-8")

        second = config_loader.load(test_brand_id)
        assert second.version == "test-1.0.1"


class TestSchemaValidationErrors:
    def test_missing_project_file_returns_404_equivalent(self, config_loader: ConfigLoader) -> None:
        with pytest.raises(ProjectConfigNotFoundError, match="missing-client"):
            config_loader.load("missing-client")

    def test_malformed_json(self, config_loader: ConfigLoader) -> None:
        path = config_loader.config_dir / "bad-json.json"
        path.write_text("{not-valid-json", encoding="utf-8")
        with pytest.raises(ProjectConfigValidationError, match="invalid JSON"):
            config_loader.load("bad-json")

    @pytest.mark.parametrize(
        ("project_id", "payload_override"),
        [
            ("missing-root", {}),
            ("missing-version", {"project_id": "missing-version", "categories": {}, "persona_pivot": {}}),
            (
                "missing-categories",
                {
                    "project_id": "missing-categories",
                    "version": "1",
                    "persona_pivot": {"strategy": "rotation", "templates": ["x"]},
                },
            ),
            (
                "missing-pivot",
                {
                    "project_id": "missing-pivot",
                    "version": "1",
                    "categories": {"critical_blocks": [], "soft_blocks": []},
                },
            ),
        ],
    )
    def test_rejects_incomplete_json_schema(
        self,
        config_loader: ConfigLoader,
        project_id: str,
        payload_override: dict,
    ) -> None:
        _write_config(config_loader, project_id, payload_override)
        with pytest.raises(ProjectConfigValidationError):
            config_loader.load(project_id)

    @pytest.mark.parametrize(
        ("project_id", "payload"),
        [
            (
                "wrong-types",
                {
                    "project_id": 12345,
                    "version": "1",
                    "categories": {"critical_blocks": "illegal", "soft_blocks": []},
                    "persona_pivot": {"strategy": "rotation", "templates": ["ok"]},
                },
            ),
            (
                "invalid-strategy",
                {
                    "project_id": "invalid-strategy",
                    "version": "1",
                    "categories": {"critical_blocks": [], "soft_blocks": []},
                    "persona_pivot": {"strategy": "random", "templates": ["ok"]},
                },
            ),
            (
                "empty-templates",
                {
                    "project_id": "empty-templates",
                    "version": "1",
                    "categories": {"critical_blocks": [], "soft_blocks": []},
                    "persona_pivot": {"strategy": "rotation", "templates": []},
                },
            ),
            (
                "extra-property",
                {
                    **_valid_payload("extra-property"),
                    "unknown_field": True,
                },
            ),
            (
                "invalid-project-id-pattern",
                {
                    **_valid_payload("invalid-project-id-pattern"),
                    "project_id": "invalid project id",
                },
            ),
        ],
    )
    def test_rejects_invalid_types_and_constraints(
        self,
        config_loader: ConfigLoader,
        project_id: str,
        payload: dict,
    ) -> None:
        _write_config(config_loader, project_id, payload)
        with pytest.raises(ProjectConfigValidationError):
            config_loader.load(project_id)

    def test_rejects_project_id_mismatch_with_filename(self, config_loader: ConfigLoader) -> None:
        _write_config(config_loader, "file-a", _valid_payload("file-b"))
        with pytest.raises(ProjectConfigValidationError, match="does not match"):
            config_loader.load("file-a")

    def test_pydantic_rejects_duplicate_category_labels(self) -> None:
        with pytest.raises(ValueError, match="unique"):
            ProjectConfig.model_validate(
                {
                    **_valid_payload(),
                    "categories": {
                        "critical_blocks": ["illegal", "illegal"],
                        "soft_blocks": [],
                    },
                }
            )

    def test_pydantic_rejects_empty_pivot_templates_after_strip(self) -> None:
        with pytest.raises(ValueError):
            ProjectConfig.model_validate(
                {
                    **_valid_payload(),
                    "persona_pivot": {"strategy": "rotation", "templates": ["   "]},
                }
            )
