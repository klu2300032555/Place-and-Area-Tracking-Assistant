import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import AddressInput, PincodeAddressResponse
from app.services.pincode_service import PincodeService
logger = logging.getLogger(__name__)

router = APIRouter()

_service: PincodeService | None = None


def get_service() -> PincodeService:
    # Lazy — the Gemini client (via AIAddressParser inside PincodeService)
    # is only built on first request, not at import time.
    global _service
    if _service is None:
        _service = PincodeService("data/all_india_pincode_directory_2025.csv")
    return _service


@router.get("/health")
def health_check():
    return {"status": "ok"}

# pincode_routes.py
@router.post("/validate-pincode", response_model=PincodeAddressResponse)
def validate_pincode(payload: AddressInput):
    try:
        return get_service().validate_address(payload.raw_address)
    except Exception as error:
        logger.exception("validate_pincode failed")
        raise HTTPException(status_code=500, detail=str(error))