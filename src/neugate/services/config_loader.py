from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import jsonschema
from jsonschema import Draft202012Validator

from neugate.models.config import ProjectConfig
from neugate.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class ProjectConfigNotFoundError(Exception):
    def __init__(self, project_id: str) -> None:
        super().__init__(f"No configuration found for project_id={project_id!r}")
        self.project_id = project_id


class ProjectConfigValidationError(Exception):
    def __init__(self, project_id: str, detail: str) -> None:
        super().__init__(f"Invalid configuration for project_id={project_id!r}: {detail}")
        self.project_id = project_id
        self.detail = detail


class ConfigLoader:
    """Loads and validates per-client JSON configs; hot-reloads when files change."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._schema_validator: Draft202012Validator | None = None
        self._cache: dict[str, tuple[str, ProjectConfig]] = {}

    def _resolve_path(self, base: Path) -> Path:
        path = base if base.is_absolute() else Path.cwd() / base
        return path.resolve()

    @property
    def config_dir(self) -> Path:
        return self._resolve_path(self._settings.config_dir)

    @property
    def schema_path(self) -> Path:
        return self._resolve_path(self._settings.schema_path)

    def _get_schema_validator(self) -> Draft202012Validator:
        if self._schema_validator is not None:
            return self._schema_validator

        schema_file = self.schema_path
        if not schema_file.is_file():
            raise FileNotFoundError(f"NeuGate JSON schema not found: {schema_file}")

        with schema_file.open(encoding="utf-8") as handle:
            schema = json.load(handle)

        jsonschema.Draft202012Validator.check_schema(schema)
        self._schema_validator = Draft202012Validator(schema)
        return self._schema_validator

    def _config_file_for(self, project_id: str) -> Path:
        safe_id = project_id.strip()
        return self.config_dir / f"{safe_id}.json"

    def load(self, project_id: str) -> ProjectConfig:
        path = self._config_file_for(project_id)
        if not path.is_file():
            raise ProjectConfigNotFoundError(project_id)

        content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        cached = self._cache.get(project_id)
        if cached and cached[0] == content_hash:
            return cached[1]

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ProjectConfigValidationError(project_id, f"invalid JSON: {exc}") from exc

        validator = self._get_schema_validator()
        errors = sorted(validator.iter_errors(raw), key=lambda e: e.path)
        if errors:
            first = errors[0]
            location = "/".join(str(part) for part in first.absolute_path)
            detail = f"{first.message}" + (f" at {location}" if location else "")
            raise ProjectConfigValidationError(project_id, detail)

        try:
            config = ProjectConfig.model_validate(raw)
        except Exception as exc:
            raise ProjectConfigValidationError(project_id, str(exc)) from exc

        if config.project_id != project_id:
            raise ProjectConfigValidationError(
                project_id,
                f"project_id in file ({config.project_id!r}) does not match request ({project_id!r})",
            )

        self._cache[project_id] = (content_hash, config)
        logger.debug("Loaded config for %s from %s", project_id, path)
        return config

    def list_project_config_files(self) -> list[Path]:
        if not self.config_dir.is_dir():
            return []
        return sorted(self.config_dir.glob("*.json"))

    def list_loadable_project_ids(self) -> list[str]:
        """Return project_ids whose JSON files pass schema + Pydantic validation."""
        loadable: list[str] = []
        for path in self.list_project_config_files():
            project_id = path.stem
            try:
                self.load(project_id)
            except (ProjectConfigNotFoundError, ProjectConfigValidationError):
                continue
            loadable.append(project_id)
        return loadable

    def invalidate(self, project_id: str | None = None) -> None:
        if project_id is None:
            self._cache.clear()
            return
        self._cache.pop(project_id, None)


_config_loader: ConfigLoader | None = None


def get_config_loader() -> ConfigLoader:
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader
