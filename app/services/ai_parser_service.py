import json
import logging
import os

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

from google import genai

load_dotenv()
logger = logging.getLogger(__name__)

_client = None


def _get_client():
    """Lazy singleton — the client is only built on first actual use,
    not at import time. This means a missing/late-loaded API key fails
    with a clear error on the request that needs it, not silently at
    server boot."""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Check backend/.env and make sure "
                "you're running uvicorn from inside the backend/ directory."
            )
        _client = genai.Client(api_key=api_key)
    return _client


class AIAddressParser:

    def parse(self, raw_address: str):
        prompt = f"""
You are an Indian Address Intelligence Engine.

Your task:

Understand addresses written in

-English
-Hinglish
-Telugu
-Hindi
-Tamil
-Kannada
-Malayalam
-Bengali

Also understand:

-short forms
-misspellings
-regional words
-transliterated text

Normalize the address.

Return ONLY VALID JSON.

Schema:

{{
"house_number":"",
"building_name":"",
"street":"",
"landmark":"",
"locality":"",
"area":"",
"city":"",
"district":"",
"state":"",
"country":"India",
"pincode":"",
"language":"",
"normalized_address":""
}}

Address:

{raw_address}
"""

        response = _get_client().models.generate_content(
            model="gemini-3.6-flash",  # "gemini-3.5-flash" does not exist
            contents=prompt,
        )

        text = (response.text or "").strip()

        if text.startswith("```"):
            text = text.replace("```json", "")
            text = text.replace("```", "").strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("Gemini returned non-JSON: %s", text[:500])
            raise ValueError(f"AI parser returned invalid JSON: {exc}") from exc