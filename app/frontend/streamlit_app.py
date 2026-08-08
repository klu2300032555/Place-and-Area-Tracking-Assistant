"""
PATA — AI Address Resolution Frontend
Run with: streamlit run streamlit_app.py

Make sure your FastAPI backend is running first:
    uvicorn app.main:app --reload
(default expected at http://127.0.0.1:8000)
"""

import streamlit as st
import requests
import pandas as pd
import pydeck as pdk
import threading
import time
import itertools

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"

EXAMPLE_ADDRESSES = [
    "HNo12 Hanuman gudi degara, madhaper, hyd, 500081",
    "HNo12 Hanuman gudi ke paas madhaper hyd",
    "Apollo hospital pakkathula",
    "plot 45 gachibowli main road hyderabad telangana",
]

st.set_page_config(
    page_title="PATA — Address Resolver",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# CUSTOM STYLING
# ---------------------------------------------------------
st.markdown(
    """
    <style>
        .main > div { padding-top: 1.5rem; }

        .pata-hero {
            padding: 1.75rem 2rem;
            border-radius: 14px;
            background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
            border: 1px solid #2d3748;
            margin-bottom: 1.5rem;
        }
        .pata-hero h1 {
            margin: 0 0 0.35rem 0;
            font-size: 1.9rem;
        }
        .pata-hero p {
            margin: 0;
            color: #9ca3af;
            font-size: 0.95rem;
        }

        .result-card {
            padding: 1.25rem 1.5rem;
            border-radius: 12px;
            border: 1px solid #2d3748;
            background-color: rgba(255,255,255,0.02);
            margin-bottom: 1rem;
        }

        .confidence-badge {
            display: inline-block;
            padding: 0.2rem 0.7rem;
            border-radius: 999px;
            font-weight: 600;
            font-size: 0.8rem;
            letter-spacing: 0.03em;
        }
        .confidence-high   { background-color: #14532d; color: #86efac; }
        .confidence-medium { background-color: #713f12; color: #fde68a; }
        .confidence-low    { background-color: #7f1d1d; color: #fca5a5; }

        .evidence-chip {
            display: inline-block;
            padding: 0.15rem 0.6rem;
            margin: 0.15rem 0.25rem 0.15rem 0;
            border-radius: 6px;
            background-color: rgba(255,255,255,0.06);
            font-size: 0.82rem;
            color: #d1d5db;
        }

        div[data-testid="stMetricValue"] { font-size: 1.4rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    backend_url = st.text_input("Backend URL", value=DEFAULT_BACKEND_URL)
    analyze_endpoint = f"{backend_url.rstrip('/')}/analyze-address"

    st.markdown("---")
    st.markdown("### 🧪 Try an example")
    for i, example in enumerate(EXAMPLE_ADDRESSES):
        if st.button(example, key=f"example_{i}", use_container_width=True):
            st.session_state["raw_address_input"] = example

    st.markdown("---")
    st.markdown(
        "### How it works\n"
        "1. **Gemini** parses the raw text\n"
        "2. **CSV** validates the pincode\n"
        "3. **Nominatim** anchors the locality\n"
        "4. **Overpass** pulls real nearby landmarks\n"
        "5. **Ranking** scores and picks the best point"
    )

# ---------------------------------------------------------
# HERO HEADER
# ---------------------------------------------------------
st.markdown(
    """
    <div class="pata-hero">
        <h1> PATA — AI Address Resolution Engine</h1>
        <p>Takes one messy Indian address and turns it into a single, accurately
        geocoded point — verified against real OpenStreetMap landmarks and pincode records.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# INPUT
# ---------------------------------------------------------
if "raw_address_input" not in st.session_state:
    st.session_state["raw_address_input"] = ""

with st.form("address_form"):
    raw_address = st.text_area(
        "Enter a raw address",
        placeholder="Enter Your Address Here...",
        height=90,
        key="raw_address_input",
    )
    col_submit, col_hint = st.columns([1, 4])
    with col_submit:
        submitted = st.form_submit_button("🔍 Resolve Address", type="primary", use_container_width=True)
    with col_hint:
        st.caption("Mixed languages, landmarks, abbreviations, wrong pincodes — all fine.")

# ---------------------------------------------------------
# CALL BACKEND
# ---------------------------------------------------------
if submitted:
    if not raw_address.strip():
        st.warning("Please enter an address first.")
        st.stop()

    # ---------------------------------------------------
    # ANIMATED "THINKING" LOADER — pulsing dots + shimmer
    # text that keep animating continuously in the browser
    # (pure CSS, so it never stutters), while the actual
    # backend call runs on a background thread.
    # ---------------------------------------------------
    loader_html = """
    <style>
    @keyframes pata-pulse {
        0%, 80%, 100% { transform: scale(0.55); opacity: 0.35; }
        40% { transform: scale(1); opacity: 1; }
    }
    @keyframes pata-shimmer {
        0% { background-position: 0% 50%; }
        100% { background-position: 200% 50%; }
    }
    .pata-loader-wrap {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 1.1rem 1.4rem;
        border-radius: 12px;
        border: 1px solid #2d3748;
        background-color: rgba(255,255,255,0.02);
        margin-bottom: 0.6rem;
    }
    .pata-dots { display: flex; gap: 6px; }
    .pata-dots span {
        width: 9px; height: 9px; border-radius: 50%;
        background: linear-gradient(135deg, #34d399, #fbbf24);
        animation: pata-pulse 1.1s infinite ease-in-out;
        display: inline-block;
    }
    .pata-dots span:nth-child(2) { animation-delay: 0.15s; }
    .pata-dots span:nth-child(3) { animation-delay: 0.3s; }
    .pata-loader-text {
        font-size: 0.95rem;
        font-weight: 500;
        background: linear-gradient(90deg, #6b7280, #f3f4f6, #6b7280);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: pata-shimmer 2.2s linear infinite;
    }
    </style>
    <div class="pata-loader-wrap">
        <div class="pata-dots"><span></span><span></span><span></span></div>
        <div class="pata-loader-text">PATA is resolving your address...</div>
    </div>
    """
    dots_placeholder = st.empty()
    dots_placeholder.markdown(loader_html, unsafe_allow_html=True)

    stage_placeholder = st.empty()
    stages = [
        "🧩 Parsing with Gemini...",
        "📮 Validating pincode against official records...",
        "📍 Anchoring locality via Nominatim...",
        "🏷️ Fetching nearby landmarks via OpenStreetMap...",
        "🏆 Scoring and ranking candidates...",
    ]

    result_holder = {}

    def _call_backend():
        try:
            r = requests.post(analyze_endpoint, json={"raw_address": raw_address}, timeout=60)
            r.raise_for_status()
            result_holder["data"] = r.json()
        except requests.exceptions.ConnectionError:
            result_holder["error"] = "connection"
        except requests.exceptions.HTTPError as e:
            result_holder["error"] = f"http:{e}"
        except requests.exceptions.RequestException as e:
            result_holder["error"] = f"req:{e}"

    thread = threading.Thread(target=_call_backend)
    thread.start()

    stage_cycle = itertools.cycle(stages)
    while thread.is_alive():
        stage_placeholder.caption(next(stage_cycle))
        time.sleep(0.9)
    thread.join()

    dots_placeholder.empty()
    stage_placeholder.empty()

    if "error" in result_holder:
        err = result_holder["error"]
        if err == "connection":
            st.error(f"Could not reach backend at {backend_url}. Make sure `uvicorn app.main:app --reload` is running.")
        elif err.startswith("http:"):
            st.error(f"Backend returned an error: {err[5:]}")
        else:
            st.error(f"Request failed: {err[4:]}")
        st.stop()

    data = result_holder["data"]

    if data.get("warning"):
        st.warning(data["warning"])

    # -------------------------------------------------------
    # TABS
    # -------------------------------------------------------
    tab_result, tab_parsed, tab_pincode, tab_candidates, tab_raw = st.tabs(
        ["✅ Result", "🧩 Parsed Address", "📮 Pincode", "🏷️ Candidates", "🔍 Raw JSON"]
    )

    # ---- TAB: Result ----
    with tab_result:
        final_point = data.get("final_geocoded_point")
        if final_point:
            confidence = final_point.get("confidence", "unknown")

            st.markdown('<div class="result-card">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 1, 1.3])
            col1.metric("Latitude", f"{final_point['lat']:.6f}")
            col2.metric("Longitude", f"{final_point['lon']:.6f}")
            with col3:
                st.markdown(
                    f'<span class="confidence-badge confidence-{confidence}">'
                    f'{confidence.upper()} CONFIDENCE</span>'
                    f'&nbsp;&nbsp;Score: <b>{final_point.get("score")}</b>',
                    unsafe_allow_html=True,
                )

            st.write(f"**Anchored to:** {final_point.get('name') or 'Locality center'}")
            if final_point.get("reason"):
                chips = "".join(f'<span class="evidence-chip">{r}</span>' for r in final_point["reason"])
                st.markdown(chips, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            coord_str = f"{final_point['lat']}, {final_point['lon']}"
            st.code(coord_str, language=None)

            map_df = pd.DataFrame([{"lat": final_point["lat"], "lon": final_point["lon"]}])
            st.map(map_df, zoom=15)
        else:
            st.info("No geocoded point could be determined for this address.")

    # ---- TAB: Parsed Address ----
    with tab_parsed:
        parsed = data.get("parsed_address", {})
        if parsed.get("normalized_address"):
            st.success(parsed["normalized_address"])

        cols = st.columns(3)
        fields = list(parsed.items())
        for i, (key, value) in enumerate(fields):
            if key == "normalized_address":
                continue
            cols[i % 3].markdown(f"**{key.replace('_', ' ').title()}**  \n{value or '—'}")

    # ---- TAB: Pincode ----
    with tab_pincode:
        pv = data.get("pincode_validation", {})
        col1, col2, col3 = st.columns(3)
        col1.metric("Detected Pincode", pv.get("detected_pincode") or "—")
        col2.metric("Valid?", "✅ Yes" if pv.get("is_valid_pincode") else "❌ No")
        col3.metric("Matches Found", pv.get("matches_found", 0))

        if pv.get("postal_matches"):
            st.dataframe(pd.DataFrame(pv["postal_matches"]), use_container_width=True, hide_index=True)

    # ---- TAB: Candidates ----
    with tab_candidates:
        candidates = data.get("candidates", [])
        st.caption(f"{data.get('candidate_count', 0)} nearby landmarks evaluated")

        if candidates:
            best_candidate = max(candidates, key=lambda c: c.get("score", 0))
            st.success(
                f"🏆 Best-scoring candidate: **{best_candidate.get('name')}**  "
                f"(score: {best_candidate.get('score')}, "
                f"{best_candidate.get('distance')} m from locality center)"
            )

            table_rows = [
                {
                    "Name": c.get("name"),
                    "Score": c.get("score"),
                    "Distance (m)": c.get("distance"),
                    "Type": c.get("type"),
                    "Reason": "; ".join(c.get("reason", [])),
                    "Best": "🏆" if c is best_candidate else "",
                }
                for c in candidates
            ]
            cand_df = pd.DataFrame(table_rows).sort_values("Score", ascending=False)

            def _highlight_best(row):
                return ["background-color: #14532d" if row["Best"] == "🏆" else "" for _ in row]

            st.dataframe(
                cand_df.style.apply(_highlight_best, axis=1),
                use_container_width=True,
                hide_index=True,
            )

            geo_candidates = [c for c in candidates if c.get("lat") and c.get("lon")]
            if geo_candidates:
                layer_all = pdk.Layer(
                    "ScatterplotLayer",
                    data=[c for c in geo_candidates if c is not best_candidate],
                    get_position="[lon, lat]",
                    get_color="[30, 100, 220, 160]",
                    get_radius=25,
                    pickable=True,
                )
                layer_best = pdk.Layer(
                    "ScatterplotLayer",
                    data=[best_candidate],
                    get_position="[lon, lat]",
                    get_color="[220, 30, 30, 220]",
                    get_radius=55,
                    pickable=True,
                )
                view_state = pdk.ViewState(
                    latitude=best_candidate["lat"],
                    longitude=best_candidate["lon"],
                    zoom=15,
                )
                st.pydeck_chart(
                    pdk.Deck(
                        layers=[layer_all, layer_best],
                        initial_view_state=view_state,
                        tooltip={"text": "{name}\nScore: {score}"},
                    )
                )
                st.caption("🔴 Red = best-scoring (final) point · 🔵 Blue = other candidates considered")
        else:
            st.write("No nearby candidates were found.")

    # ---- TAB: Raw JSON ----
    with tab_raw:
        st.json(data)