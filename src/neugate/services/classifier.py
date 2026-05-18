from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI, OpenAIError

from neugate.models.config import ProjectConfig
from neugate.models.evaluate import ClassifierVerdict
from neugate.prompts.classifier import build_classifier_system_prompt, build_classifier_user_message
from neugate.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class ClassifierError(Exception):
    """LLM classifier failed."""


class ClassifierService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: AsyncOpenAI | None = None

    def _client_or_raise(self) -> AsyncOpenAI:
        if not self._settings.openai_api_key:
            raise ClassifierError("OPENAI_API_KEY is not configured")

        if self._client is None:
            kwargs: dict[str, Any] = {"api_key": self._settings.openai_api_key}
            if self._settings.openai_base_url:
                kwargs["base_url"] = self._settings.openai_base_url
            self._client = AsyncOpenAI(**kwargs, timeout=self._settings.llm_timeout_seconds)

        return self._client

    def _build_response_schema(self, config: ProjectConfig) -> dict[str, Any]:
        block_labels = config.categories.all_block_labels()
        category_enum = ["safe_domain", *block_labels]

        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["is_violation", "category"],
            "properties": {
                "is_violation": {
                    "type": "boolean",
                    "description": "True when the message must be short-circuited before the main backend.",
                },
                "category": {
                    "type": "string",
                    "enum": category_enum,
                    "description": "Violation label or safe_domain when the message may proceed.",
                },
            },
        }

    def _normalize_verdict(self, verdict: ClassifierVerdict, config: ProjectConfig) -> ClassifierVerdict:
        blocks = set(config.categories.all_block_labels())

        if verdict.category == "safe_domain":
            return ClassifierVerdict(is_violation=False, category="safe_domain")

        if verdict.category in blocks:
            return ClassifierVerdict(is_violation=True, category=verdict.category)

        # Model returned an unknown label — treat as safe but log for observability.
        logger.warning(
            "Classifier returned unknown category %r for project %s; defaulting to safe_domain",
            verdict.category,
            config.project_id,
        )
        return ClassifierVerdict(is_violation=False, category="safe_domain")

    async def classify(self, message: str, config: ProjectConfig) -> ClassifierVerdict:
        client = self._client_or_raise()
        schema = self._build_response_schema(config)

        try:
            completion = await client.chat.completions.create(
                model=self._settings.openai_model,
                temperature=0,
                max_tokens=self._settings.llm_max_tokens,
                messages=[
                    {"role": "system", "content": build_classifier_system_prompt(config)},
                    {"role": "user", "content": build_classifier_user_message(message)},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "neugate_evaluation",
                        "strict": True,
                        "schema": schema,
                    },
                },
            )
        except OpenAIError as exc:
            logger.exception("OpenAI classifier call failed for project %s", config.project_id)
            raise ClassifierError(str(exc)) from exc

        content = completion.choices[0].message.content
        if not content:
            raise ClassifierError("Empty response from classifier model")

        try:
            payload = json.loads(content)
            verdict = ClassifierVerdict.model_validate(payload)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ClassifierError(f"Invalid classifier JSON: {exc}") from exc

        return self._normalize_verdict(verdict, config)


_classifier: ClassifierService | None = None


def get_classifier() -> ClassifierService:
    global _classifier
    if _classifier is None:
        _classifier = ClassifierService()
    return _classifier
