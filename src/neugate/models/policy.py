"""Consumer-supplied policy (NeuGate remains brand-agnostic)."""

from pydantic import BaseModel, Field, field_validator

from neugate.models.config import PersonaPivot, ProjectCategories, ProjectConfig


class ConsumerPolicy(BaseModel):
    """Red-team policy and pivot templates sent by the consumer on each request."""

    critical_blocks: list[str] = Field(min_length=0)
    soft_blocks: list[str] = Field(min_length=0)
    pivot_templates: list[str] = Field(min_length=1)

    @field_validator("critical_blocks", "soft_blocks")
    @classmethod
    def strip_unique_labels(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("category labels must be unique")
        return cleaned

    @field_validator("pivot_templates")
    @classmethod
    def non_empty_templates(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if not cleaned:
            raise ValueError("pivot_templates must contain at least one non-empty string")
        return cleaned

    def all_block_labels(self) -> list[str]:
        return list(dict.fromkeys(self.critical_blocks + self.soft_blocks))

    def to_project_config(self, project_id: str) -> ProjectConfig:
        """Adapter for classifier / pivot code that expects ProjectConfig shape."""
        return ProjectConfig(
            project_id=project_id,
            version="consumer-supplied",
            categories=ProjectCategories(
                critical_blocks=list(self.critical_blocks),
                soft_blocks=list(self.soft_blocks),
            ),
            persona_pivot=PersonaPivot(strategy="rotation", templates=list(self.pivot_templates)),
        )

    @classmethod
    def from_project_config(cls, config: ProjectConfig) -> "ConsumerPolicy":
        return cls(
            critical_blocks=list(config.categories.critical_blocks),
            soft_blocks=list(config.categories.soft_blocks),
            pivot_templates=list(config.persona_pivot.templates),
        )
