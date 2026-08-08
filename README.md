# PATA — AI Address Resolution Engine

PATA takes a messy, real-world Indian address — written in any regional language, misspelled, abbreviated, or built around a landmark instead of a street name — and resolves it to a single accurate GPS point. The result is cross-verified against the official Indian pincode directory and live OpenStreetMap data, and returned with a confidence score and human-readable evidence.

```
"HNo12 Hanuman gudi ke paas madhaper hyd"
        →  17.4483, 78.3915  (High confidence)
```

---

## How it works

Every address goes through the same five-stage pipeline:

```
Raw address
   │
   ▼
① AI Parsing        — Gemini reads the free text and extracts structured fields
   │                   (house no, landmark, locality, city, state, pincode)
   ▼
② Pincode Validation — checked against India's official pincode/post-office CSV
   │
   ▼
③ Locality Geocoding — Nominatim resolves locality/city/state into an approximate
   │                   lat/lon + bounding box
   ▼
④ Nearby Landmark Search — Overpass API pulls every real, named place (shops,
   │                        temples, hospitals, etc.) within ~600m
   ▼
⑤ Ranking             — every nearby candidate is scored against the parsed
                        landmark name, distance, and pincode match; the highest
                        scorer becomes the final answer
   │
   ▼
Final point: lat/lon + confidence (high / medium / low) + reasons
```

---

## Tech stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python | Entire project — backend and frontend |
| Backend framework | FastAPI | Exposes the pipeline as an HTTP API |
| Server | Uvicorn | Runs the FastAPI app |
| Validation | Pydantic | Request/response schema validation |
| AI parsing | Google Gemini (`google-genai`) | Understands multilingual/informal address text |
| Geocoding | Nominatim (OpenStreetMap) | Locality → coordinates |
| Landmark data | Overpass API (OpenStreetMap) | Real nearby places |
| Reference data | Local CSV (`all_india_pincode_directory_2025.csv`) | Official pincode verification |
| Frontend | Streamlit | Interactive web UI, written entirely in Python |
| Data display | Pandas | Tables for parsed fields / candidates |
| Maps | PyDeck | Interactive scatterplot map of candidates |
| Secrets | `python-dotenv` + `.env` | Keeps the Gemini API key out of source code |

---

## Project structure

```
Pata/
├── app/
│   ├── main.py                     # FastAPI entrypoint, registers routes
│   ├── routes/
│   │   ├── address_routes.py       # POST /analyze-address
│   │   └── pincode_routes.py       # GET /health, POST /validate-pincode
│   ├── services/
│   │   ├── ai_parser_service.py    # Stage ① — Gemini address parsing
│   │   ├── pincode_service.py      # Stage ② — CSV pincode lookup
│   │   ├── nominatim_service.py    # Stage ③ — locality geocoding
│   │   ├── osm_service.py          # Stage ④ — nearby landmark search
│   │   ├── ranking_service.py      # Stage ⑤ — scoring + final point
│   │   └── ai_address_engine.py    # Orchestrates all five stages
│   ├── models/
│   │   └── schemas.py              # Pydantic request/response models
│   └── frontend/
│       └── streamlit_app.py        # Streamlit UI
├── data/
│   └── all_india_pincode_directory_2025.csv
├── requirements.txt
└── .env                             # GEMINI_API_KEY (not committed)
```

---

## Setup

### 1. Clone / unzip the project
```bash
cd Pata
```

### 2. Create a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your Gemini API key
Create a `.env` file in the project root:
```
GEMINI_API_KEY=your_real_key_here
```

---

## Running the project

You need **two terminals** — the backend and frontend are separate processes.

**Terminal 1 — start the backend (FastAPI)**
```bash
uvicorn app.main:app --reload --port 8000
```
Runs at `http://127.0.0.1:8000`. Visit `/docs` for interactive Swagger API docs.

**Terminal 2 — start the frontend (Streamlit)**
```bash
streamlit run app/frontend/streamlit_app.py
```
Opens automatically at `http://localhost:8501`.

> The frontend calls the backend over HTTP, so the backend must be running first.

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health/info — lists available routes |
| `GET` | `/health` | Simple health check (`{"status": "ok"}`) |
| `POST` | `/analyze-address` | Full pipeline — returns parsed address, pincode validation, locality, best-matching landmark, ranked candidates, and confidence |
| `POST` | `/validate-pincode` | Lighter check — parses the address and validates the pincode + nearby OSM candidates, without full ranking |

**Example request:**
```json
POST /analyze-address
{
  "raw_address": "HNo12 Hanuman gudi ke paas madhaper hyd"
}
```

**Example response (shortened):**
```json
{
  "raw_address": "...",
  "parsed_address": { "landmark": "Hanuman gudi", "city": "Hyderabad", "pincode": "500081", ... },
  "pincode_validation": { "is_valid_pincode": true, "matches_found": 1, ... },
  "locality": { "lat": 17.4486, "lon": 78.3908, ... },
  "best_match": { "name": "Sri Hanuman Temple", "score": 68.5, "distance": 45.2, ... },
  "final_geocoded_point": { "lat": 17.4483, "lon": 78.3915, "confidence": "high", ... },
  "candidates": [ ... up to 10 ranked candidates ... ]
}
```

---

## Ranking logic

Each nearby OSM candidate is scored:

| Signal | Points |
|---|---|
| Landmark name similarity (text match) | up to 40 |
| Distance < 100m from locality center | +30 |
| Distance < 300m | +20 |
| Distance < 500m | +10 |
| OSM tag's pincode matches validated pincode | +20 |
| Candidate has a name at all | +5 |

**Confidence:** score ≥ 60 → *high* · ≥ 35 → *medium* · below → *low*. If no candidates are found nearby, the locality center is returned as a fallback point, explicitly marked low confidence.

---

## Notes

- Nominatim and Overpass are free public services — please don't send excessive request volume; the code already includes fallback mirrors and retry delays to be a good API citizen.
- The pincode CSV is loaded and indexed once at startup for fast (O(1)) lookups.
- `.env` is required for the AI parsing stage — without `GEMINI_API_KEY`, `/analyze-address` and `/validate-pincode` will fail with a clear error on first use.
