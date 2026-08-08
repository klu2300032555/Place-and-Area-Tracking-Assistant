import logging
from math import radians, sin, cos, sqrt, atan2

import requests

logger = logging.getLogger(__name__)

MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

HEADERS = {"User-Agent": "PATA-AddressEngine/1.0 (contact: hv130706@gmail.com)"}


class OSMService:

    def search_nearby(self, lat: float, lon: float, radius: int = 600):
        query = f"""
[out:json][timeout:20];
(
  nwr["amenity"](around:{radius},{lat},{lon});
  nwr["shop"](around:{radius},{lat},{lon});
  nwr["place_of_worship"](around:{radius},{lat},{lon});
  nwr["tourism"](around:{radius},{lat},{lon});
);
out center tags 60;
"""
        for mirror in MIRRORS:
            try:
                response = requests.post(mirror, data={"data": query}, headers=HEADERS, timeout=20)
                response.raise_for_status()
                logger.info("Overpass succeeded via %s", mirror)
                return self.parse(response.json(), lat, lon)
            except requests.RequestException as exc:
                logger.warning("Overpass mirror %s failed: %s", mirror, exc)
                continue
        logger.error("All Overpass mirrors failed for (%s, %s)", lat, lon)
        return []

    def _haversine(self, lat1, lon1, lat2, lon2):
        R = 6371000
        dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        return R * 2 * atan2(sqrt(a), sqrt(1 - a))

    def parse(self, data, origin_lat=None, origin_lon=None):
        places = []
        for item in data.get("elements", []):
            lat = item.get("lat")
            lon = item.get("lon")
            if lat is None:
                center = item.get("center", {})
                lat, lon = center.get("lat"), center.get("lon")

            tags = item.get("tags", {})
            name = tags.get("name")

            if not name or lat is None or lon is None:
                continue

            entry = {
                "osm_id": item.get("id"),
                "type": item.get("type"),
                "name": name,
                "lat": lat,
                "lon": lon,
                "tags": tags,
            }
            if origin_lat is not None and origin_lon is not None:
                entry["distance"] = round(self._haversine(origin_lat, origin_lon, lat, lon), 1)
            places.append(entry)

        logger.info("Overpass returned %d named candidates", len(places))
        return places