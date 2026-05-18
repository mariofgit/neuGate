from typing import Literal

from pydantic import BaseModel, Field

from neugate.models.policy import ConsumerPolicy


class EvaluateRequest(BaseModel):
    project_id: str = Field(min_length=1, description="Correlation id for logs; not a config lookup key.")
    message: str = Field(min_length=1, max_length=16_000)
    policy: ConsumerPolicy


class EvaluateResponse(BaseModel):
    is_violation: bool
    category: str
    action: Literal["short_circuit", "proceed"]
    cached_response: str | None


class ClassifierVerdict(BaseModel):
    """Structured output from the LLM classifier (internal)."""

    is_violation: bool
    category: str = Field(
        description="Violation label from the project block list, or safe_domain when allowed."
    )
