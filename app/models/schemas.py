from typing import List, Optional
from pydantic import BaseModel


class AddressInput(BaseModel):
    raw_address: str


# -----------------------------
# CSV Match
# -----------------------------
class PostalMatch(BaseModel):
    pincode: Optional[str] = None
    office_name: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None


# -----------------------------
# AI Parsed Address
# -----------------------------
class ParsedAddress(BaseModel):
    house_number: Optional[str] = None
    building_name: Optional[str] = None
    street: Optional[str] = None
    landmark: Optional[str] = None
    locality: Optional[str] = None
    area: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None
    language: Optional[str] = None
    normalized_address: Optional[str] = None


# -----------------------------
# Pincode Validation
# -----------------------------
class PincodeValidation(BaseModel):
    detected_pincode: Optional[str] = None
    is_valid_pincode: bool
    matches_found: int
    postal_matches: List[PostalMatch] = []


# -----------------------------
# Nominatim geocoding result
# -----------------------------
class BoundingBox(BaseModel):
    south: float
    north: float
    west: float
    east: float


class LocalityMatch(BaseModel):
    display_name: Optional[str] = None
    lat: float
    lon: float
    boundingbox: BoundingBox


# -----------------------------
# OSM / Overpass candidate
# -----------------------------
class OSMCandidate(BaseModel):
    osm_id: Optional[int] = None
    type: Optional[str] = None
    name: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    distance: Optional[float] = None   # set by RankingService.haversine, was missing
    score: Optional[float] = None      # set by RankingService, was missing
    reason: List[str] = []             # set by RankingService, was missing (note: singular "reason", matches your ranking_service.py key)
    tags: dict = {}


# -----------------------------
# Response for POST /analyze-address
# (AIAddressEngine.analyze() — full pipeline: parse -> pincode -> geocode -> evidence -> rank)
# -----------------------------
class AIAddressResponse(BaseModel):
    raw_address: str
    parsed_address: ParsedAddress
    pincode_validation: PincodeValidation
    locality: Optional[LocalityMatch] = None
    best_match: Optional[OSMCandidate] = None
    candidate_count: int = 0
    candidates: List[OSMCandidate] = []
    warning: Optional[str] = None   # set when locality couldn't be geocoded


# -----------------------------
# Response for POST /validate-pincode
# (PincodeService.validate_address() — parses + validates + attaches osm_candidates)
# -----------------------------
class PincodeAddressResponse(BaseModel):
    raw_address: str
    parsed_address: ParsedAddress
    pincode_validation: PincodeValidation
    osm_candidates: List[OSMCandidate] = []
    ai_error: Optional[str] = None

class GeocodedPoint(BaseModel):
    lat: float
    lon: float
    source: str
    name: Optional[str] = None
    osm_id: Optional[int] = None
    score: Optional[float] = None
    distance_from_locality_center: Optional[float] = None
    confidence: str
    reason: List[str] = []

class AIAddressResponse(BaseModel):
    raw_address: str
    parsed_address: ParsedAddress
    pincode_validation: PincodeValidation
    locality: Optional[LocalityMatch] = None
    best_match: Optional[OSMCandidate] = None
    final_geocoded_point: Optional[GeocodedPoint] = None   # ADD THIS
    candidate_count: int = 0
    candidates: List[OSMCandidate] = []
    warning: Optional[str] = None