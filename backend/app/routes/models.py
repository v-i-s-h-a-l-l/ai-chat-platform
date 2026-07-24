from fastapi import APIRouter

from app.available_models import AVAILABLE_MODELS
from app.schemas.model import ModelResponse

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelResponse])
def list_models():
    return [
        ModelResponse(
            id=model.id,
            name=model.name,
            description=model.description,
            icon=model.icon,
            recommended=model.recommended,
        )
        for model in AVAILABLE_MODELS
    ]
