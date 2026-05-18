from fastapi import APIRouter, Depends

from neugate.models.evaluate import EvaluateRequest, EvaluateResponse
from neugate.routes._errors import run_with_neugate_errors
from neugate.services.evaluate import EvaluateService, get_evaluate_service

router = APIRouter(prefix="/v1", tags=["evaluate"])


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_message(
    body: EvaluateRequest,
    service: EvaluateService = Depends(get_evaluate_service),
) -> EvaluateResponse:
    return await run_with_neugate_errors(lambda: service.evaluate(body))
