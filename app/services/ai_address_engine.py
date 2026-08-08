import logging

from app.services.ai_parser_service import AIAddressParser
from app.services.pincode_service import PincodeService
from app.services.nominatim_service import NominatimService
from app.services.osm_service import OSMService
from app.services.ranking_service import RankingService

logger = logging.getLogger(__name__)


class AIAddressEngine:

    def __init__(self):
        self.parser = AIAddressParser()
        self.pincode = PincodeService("data/all_india_pincode_directory_2025.csv")
        self.nominatim = NominatimService()
        self.osm = OSMService()
        self.ranking = RankingService()

    def analyze(self, raw_address: str):
        parsed = self.parser.parse(raw_address)

        pincode = parsed.get("pincode")
        postal_matches = self.pincode.lookup_pincode(pincode) if pincode else []
        pincode_validation = {
            "detected_pincode": pincode,
            "is_valid_pincode": len(postal_matches) > 0,
            "matches_found": len(postal_matches),
            "postal_matches": postal_matches,
        }

        locality = self.nominatim.search_place(
            locality=parsed.get("locality", ""),
            city=parsed.get("city", ""),
            state=parsed.get("state", ""),
            pincode=pincode,
        )

        if locality is None:
            return {
                "raw_address": raw_address,
                "parsed_address": parsed,
                "pincode_validation": pincode_validation,
                "locality": None,
                "best_match": None,
                "final_geocoded_point": None,
                "candidate_count": 0,
                "candidates": [],
                "warning": "Unable to locate locality.",
            }

        candidates = self.osm.search_nearby(lat=locality["lat"], lon=locality["lon"])

        ranked = self.ranking.rank_candidates(
            parsed_address=parsed,
            locality_center=locality,
            candidates=candidates,
            validated_pincode=pincode,
            top_n=10,
        )
        best = ranked[0] if ranked else None

        final_point = self.ranking.get_best_geocoded_point(ranked, locality_center=locality)

        return {
            "raw_address": raw_address,
            "parsed_address": parsed,
            "pincode_validation": pincode_validation,
            "locality": locality,
            "best_match": best,
            "final_geocoded_point": final_point,
            "candidate_count": len(ranked),
            "candidates": ranked,
        }