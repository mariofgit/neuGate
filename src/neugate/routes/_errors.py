from collections.abc import Awaitable, Callable
from typing import TypeVar

from fastapi import HTTPException, status

from neugate.services.classifier import ClassifierError
from neugate.services.config_loader import ProjectConfigNotFoundError, ProjectConfigValidationError
from neugate.services.test_runner import BatchRunValidationError

T = TypeVar("T")


async def run_with_neugate_errors(handler: Callable[[], Awaitable[T]]) -> T:
    try:
        return await handler()
    except ProjectConfigNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProjectConfigValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except BatchRunValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ClassifierError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Classifier unavailable: {exc}",
        ) from exc
