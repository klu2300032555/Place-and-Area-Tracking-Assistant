import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import AIAddressResponse, AddressInput
from app.services.ai_address_engine import AIAddressEngine

logger = logging.getLogger(__name__)

router = APIRouter()

_engine: AIAddressEngine | None = None


def get_engine() -> AIAddressEngine:
    global _engine
    if _engine is None:
        _engine = AIAddressEngine()
    return _engine

# address_routes.py
@router.post("/analyze-address", response_model=AIAddressResponse)
def analyze_address(payload: AddressInput):
    try:
        return get_engine().analyze(payload.raw_address)
    except Exception as e:
        logger.exception("analyze_address failed")
        raise HTTPException(status_code=500, detail=str(e))