from fastapi import APIRouter
from pydantic import BaseModel
from services.reputation_service import analyze_reputation

router = APIRouter()


class ReputationRequest(BaseModel):
    entity_name: str
    context: str | None = None


class ReputationResponse(BaseModel):
    entity_name: str
    score: float | None
    summary: str
    raw: dict


@router.post("/analyze", response_model=ReputationResponse)
def analyze(request: ReputationRequest):
    result = analyze_reputation(
        entity_name=request.entity_name,
        context=request.context,
    )
    return result


@router.get("/ping")
def ping():
    return {"message": "reputation router alive"}
