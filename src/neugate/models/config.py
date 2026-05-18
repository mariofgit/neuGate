from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ProjectCategories(BaseModel):
    critical_blocks: list[str] = Field(min_length=0)
    soft_blocks: list[str] = Field(min_length=0)

    @field_validator("critical_blocks", "soft_blocks")
    @classmethod
    def non_empty_labels(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("category labels must be unique")
        return cleaned

    def all_block_labels(self) -> list[str]:
        return list(dict.fromkeys(self.critical_blocks + self.soft_blocks))


class PersonaPivot(BaseModel):
    strategy: Literal["rotation"]
    templates: list[str] = Field(min_length=1)

    @field_validator("templates")
    @classmethod
    def non_empty_templates(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("persona_pivot.templates must contain at least one non-empty string")
        return cleaned


class ProjectConfig(BaseModel):
    project_id: str
    version: str
    categories: ProjectCategories
    persona_pivot: PersonaPivot

    @field_validator("project_id")
    @classmethod
    def valid_project_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("project_id is required")
        return value

    def is_critical(self, category: str) -> bool:
        return category in self.categories.critical_blocks
