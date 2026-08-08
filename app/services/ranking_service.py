from difflib import SequenceMatcher
from math import radians, sin, cos, sqrt, atan2


class RankingService:

    def similarity(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def haversine(self, lat1, lon1, lat2, lon2):
        R = 6371000
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    def rank_candidates(self, parsed_address, locality_center, candidates, validated_pincode=None, top_n=10):
        ranked = []
        center_lat = locality_center["lat"]
        center_lon = locality_center["lon"]

        for candidate in candidates:
            score = 0
            explanation = []

            similarity = self.similarity(
                parsed_address.get("landmark"),
                candidate.get("name"),
            )
            score += similarity * 40
            explanation.append(f"Landmark similarity = {similarity:.2f}")

            lat, lon = candidate.get("lat"), candidate.get("lon")
            if lat is not None and lon is not None:
                distance = self.haversine(center_lat, center_lon, lat, lon)
                candidate["distance"] = round(distance, 2)

                if distance < 100:
                    score += 30
                    explanation.append("Within 100 meters")
                elif distance < 300:
                    score += 20
                    explanation.append("Within 300 meters")
                elif distance < 500:
                    score += 10
                    explanation.append("Within 500 meters")

            postcode = (candidate.get("tags") or {}).get("addr:postcode")
            if postcode and validated_pincode and postcode == validated_pincode:
                score += 20
                explanation.append("Pincode matched")

            if candidate.get("name"):
                score += 5

            candidate["score"] = round(score, 2)
            candidate["reason"] = explanation
            ranked.append(candidate)

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked[:top_n]

    def get_best_geocoded_point(self, ranked_candidates, locality_center=None):
        """
        THIS is the extraction step: takes the ranked candidate list and
        pulls out ONE final answer — the highest-scoring point — with
        evidence attached. Falls back to the locality center if nothing
        was found nearby.
        """
        if not ranked_candidates:
            if locality_center:
                return {
                    "lat": locality_center["lat"],
                    "lon": locality_center["lon"],
                    "source": "locality_center_fallback",
                    "name": None,
                    "score": None,
                    "confidence": "low",
                    "reason": ["No nearby landmarks found — using locality center as approximate point"],
                }
            return None

        best = ranked_candidates[0]  # already sorted highest-first
        score = best.get("score", 0)

        if score >= 60:
            confidence = "high"
        elif score >= 35:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "lat": best["lat"],
            "lon": best["lon"],
            "source": "osm_candidate",
            "name": best.get("name"),
            "osm_id": best.get("osm_id"),
            "score": score,
            "distance_from_locality_center": best.get("distance"),
            "confidence": confidence,
            "reason": best.get("reason", []),
        }