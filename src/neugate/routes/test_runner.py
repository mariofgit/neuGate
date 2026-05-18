from fastapi import APIRouter, Depends

from neugate.models.test_runner import BatchRunRequest, BatchRunResponse
from neugate.routes._errors import run_with_neugate_errors
from neugate.services.test_runner import BatchRunnerService, get_batch_runner_service

router = APIRouter(prefix="/v1", tags=["test-runner"])


@router.post("/test-runner", response_model=BatchRunResponse)
async def run_test_batch(
    body: BatchRunRequest,
    service: BatchRunnerService = Depends(get_batch_runner_service),
) -> BatchRunResponse:
    return await run_with_neugate_errors(lambda: service.run(body))
