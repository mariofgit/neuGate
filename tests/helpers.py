from __future__ import annotations

import asyncio

from neugate.models.config import ProjectConfig
from neugate.models.evaluate import ClassifierVerdict
from neugate.services.classifier import ClassifierService
from neugate.settings import Settings

TEST_SETTINGS = Settings.model_validate({"openai_api_key": "test-key-no-network"})


class StubClassifier(ClassifierService):
    """Deterministic classifier mock — never calls OpenAI."""

    def __init__(self, verdict: ClassifierVerdict) -> None:
        super().__init__(settings=TEST_SETTINGS)
        self._verdict = verdict
        self.call_count = 0

    async def classify(self, message: str, config: ProjectConfig) -> ClassifierVerdict:
        self.call_count += 1
        return self._verdict


class MappingStubClassifier(ClassifierService):
    """Returns a verdict per prompt string; useful for batch scenarios."""

    def __init__(
        self,
        verdicts_by_prompt: dict[str, ClassifierVerdict],
        *,
        default: ClassifierVerdict | None = None,
    ) -> None:
        super().__init__(settings=TEST_SETTINGS)
        self._verdicts_by_prompt = verdicts_by_prompt
        self._default = default or ClassifierVerdict(is_violation=False, category="safe_domain")
        self.call_count = 0

    async def classify(self, message: str, config: ProjectConfig) -> ClassifierVerdict:
        self.call_count += 1
        return self._verdicts_by_prompt.get(message, self._default)


class ConcurrencyTrackingClassifier(ClassifierService):
    """Tracks in-flight classify calls to assert batch concurrency limits."""

    def __init__(
        self,
        *,
        delay_seconds: float = 0.05,
        verdict: ClassifierVerdict | None = None,
    ) -> None:
        super().__init__(settings=TEST_SETTINGS)
        self._delay_seconds = delay_seconds
        self._verdict = verdict or ClassifierVerdict(is_violation=False, category="safe_domain")
        self._in_flight = 0
        self.max_in_flight = 0
        self._lock = asyncio.Lock()
        self.call_count = 0

    async def classify(self, message: str, config: ProjectConfig) -> ClassifierVerdict:
        self.call_count += 1
        async with self._lock:
            self._in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self._in_flight)

        await asyncio.sleep(self._delay_seconds)

        async with self._lock:
            self._in_flight -= 1

        return self._verdict


# Backwards-compatible alias used by older tests
BatchStubClassifier = MappingStubClassifier
