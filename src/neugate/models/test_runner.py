from typing import Literal

from pydantic import BaseModel, Field

from neugate.models.policy import ConsumerPolicy


class DatasetCase(BaseModel):
    prompt: str = Field(min_length=1, max_length=16_000)
    expected_category: str = Field(min_length=1)


class BatchRunRequest(BaseModel):
    project_id: str = Field(min_length=1)
    policy: ConsumerPolicy
    test_dataset: list[DatasetCase] = Field(min_length=1)


class CaseRunResult(BaseModel):
    prompt: str
    expected_category: str
    llm_category: str
    is_violation: bool
    test_status: Literal["PASSED", "FAILED"]


class BatchRunResponse(BaseModel):
    project_id: str
    total_tests: int
    passed: int
    failed: int
    accuracy_rate: float
    results: list[CaseRunResult]
