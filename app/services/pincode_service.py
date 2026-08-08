import csv
import logging
import re

logger = logging.getLogger(__name__)


class PincodeService:
    """Pure offline CSV lookup. No AI, no network calls — that's what makes
    it safe to reuse from multiple places without paying for a duplicate
    Gemini call each time."""

    def __init__(self, csv_path: str):
        with open(csv_path, newline="", encoding="utf-8-sig") as csv_file:
            self.rows = list(csv.DictReader(csv_file))

        self.column_map = self._detect_columns()

        self._index: dict[str, list[dict]] = {}
        for row in self.rows:
            normalized = self._normalize_pincode_value(row.get(self.column_map["pincode"], ""))
            row["__normalized_pincode__"] = normalized
            if normalized:
                self._index.setdefault(normalized, []).append(row)

    def _clean_value(self, value):
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    def _normalize_pincode_value(self, value):
        if value is None:
            return ""
        match = re.search(r"(\d{6})", str(value))
        return match.group(1) if match else ""

    def _normalize_col(self, col_name):
        return str(col_name).strip().lower().replace("_", " ")

    def _get_csv_columns(self):
        return list(self.rows[0].keys()) if self.rows else []

    def _detect_columns(self):
        columns = {self._normalize_col(c): c for c in self._get_csv_columns()}

        def find(possible_names):
            for name in possible_names:
                if name in columns:
                    return columns[name]
            return None

        mapping = {
            "pincode": find(["pincode", "pin code", "pin"]),
            "office_name": find(["office name", "post office", "office"]),
            "district": find(["district", "district name"]),
            "state": find(["state", "state name"]),
        }
        if not mapping["pincode"]:
            raise ValueError("Could not find pincode column in CSV")
        return mapping

    def lookup_pincode(self, pincode):
        if not pincode:
            return []
        target = self._normalize_pincode_value(pincode)
        if not target:
            return []

        matches = self._index.get(target, [])  # O(1) instead of a full scan
        return [
            {
                "pincode": self._clean_value(row.get(self.column_map["pincode"])),
                "office_name": self._clean_value(row.get(self.column_map["office_name"]))
                if self.column_map["office_name"] else None,
                "district": self._clean_value(row.get(self.column_map["district"]))
                if self.column_map["district"] else None,
                "state": self._clean_value(row.get(self.column_map["state"]))
                if self.column_map["state"] else None,
            }
            for row in matches
        ]

    def validate_address(self, raw_address: str, parser=None, nominatim=None, osm=None):
        """Accepts already-constructed services instead of building its own
        AIAddressParser/NominatimService/OSMService — pass in the same
        instances the rest of the app uses so you never double-call Gemini."""
        from app.services.ai_parser_service import AIAddressParser
        from app.services.nominatim_service import NominatimService
        from app.services.osm_service import OSMService

        parser = parser or AIAddressParser()
        nominatim = nominatim or NominatimService()
        osm = osm or OSMService()

        try:
            parsed = parser.parse(raw_address)
        except Exception as error:
            logger.warning("AI parse failed: %s", error)
            return {
                "raw_address": raw_address,
                "parsed_address": {
                    "house_number": None, "building_name": None, "street": None,
                    "landmark": None, "locality": None, "area": None, "city": None,
                    "district": None, "state": None, "country": None, "pincode": None,
                    "language": None, "normalized_address": None,
                },
                "pincode_validation": {
                    "detected_pincode": None, "is_valid_pincode": False,
                    "matches_found": 0, "postal_matches": [],
                },
                "osm_candidates": [],
            }

        pincode = parsed.get("pincode")
        postal_matches = self.lookup_pincode(pincode) if pincode else []

        osm_candidates = []
        try:
            location = nominatim.search_place(
                locality=parsed.get("locality", ""),
                city=parsed.get("city", ""),
                state=parsed.get("state", ""),
            )
            logger.info("Nominatim result: %s", location)

            if location:
                bbox = location["boundingbox"]
                osm_candidates = osm.search_landmarks(
                    landmark=parsed.get("landmark", ""),
                    south=bbox["south"], west=bbox["west"],
                    north=bbox["north"], east=bbox["east"],
                )
        except Exception as e:
            logger.warning("OSM lookup failed: %s", e)

        return {
            "raw_address": raw_address,
            "parsed_address": parsed,
            "pincode_validation": {
                "detected_pincode": pincode,
                "is_valid_pincode": len(postal_matches) > 0,
                "matches_found": len(postal_matches),
                "postal_matches": postal_matches,
            },
            "osm_candidates": osm_candidates,
        }