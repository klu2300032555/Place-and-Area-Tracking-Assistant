import logging
import time

import requests

logger = logging.getLogger(__name__)


class NominatimService:

    BASE_URL = "https://nominatim.openstreetmap.org/search"

    HEADERS = {
        "User-Agent": "PATA-AddressEngine/1.0 (contact: hv130706@gmail.com)",
    }

    def _get(self, params, query_desc):
        try:
            response = requests.get(
                self.BASE_URL,
                params={**params, "format": "jsonv2", "limit": 1, "countrycodes": "in"},
                headers=self.HEADERS,
                timeout=20,
            )
            if response.status_code != 200:
                logger.warning(
                    "Nominatim non-200 for %s: status=%s body=%s",
                    query_desc, response.status_code, response.text[:300],
                )
                return None
            results = response.json()
        except requests.RequestException as exc:
            logger.warning("Nominatim request error for %s: %s", query_desc, exc)
            return None

        if not results:
            logger.info("Nominatim returned zero results for %s", query_desc)
            return None

        place = results[0]
        try:
            return {
                "display_name": place.get("display_name"),
                "lat": float(place["lat"]),
                "lon": float(place["lon"]),
                "boundingbox": {
                    "south": float(place["boundingbox"][0]),
                    "north": float(place["boundingbox"][1]),
                    "west": float(place["boundingbox"][2]),
                    "east": float(place["boundingbox"][3]),
                },
            }
        except (KeyError, ValueError, IndexError) as exc:
            logger.warning("Malformed Nominatim response for %s: %s", query_desc, exc)
            return None

    def search_place(self, locality: str = "", city: str = "", state: str = "", pincode: str = ""):
        attempts = []

        full_query = ", ".join(x for x in [locality, city, state, "India"] if x)
        if full_query.strip(", "):
            attempts.append(("full", {"q": full_query}))

        if city and state:
            attempts.append(("city_state", {"q": f"{city}, {state}, India"}))

        if pincode:
            attempts.append(("pincode", {"postalcode": pincode, "country": "India"}))

        for label, params in attempts:
            result = self._get(params, query_desc=f"{label}={params}")
            if result:
                logger.info("Nominatim resolved via '%s' strategy", label)
                return result
            time.sleep(1)

        logger.error(
            "All Nominatim strategies failed for locality=%r city=%r state=%r pincode=%r",
            locality, city, state, pincode,
        )
        return None