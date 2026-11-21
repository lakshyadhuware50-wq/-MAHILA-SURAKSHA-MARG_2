"""
pages/7_Community_Reports.py
============================
Community Safety & Hazard Reports with NLP Spam Protection & Time Decay.

Features:
- Anonymous submission of safety hazards and safe zones (zero personal ID stored).
- NLP Spam & Abusive filter (English + Hinglish).
- Automatic time-decay (90-day half life) so old incidents don't permanently stigmatise.
- Feeds directly into the AI Model Enhancement loop to improve routing accuracy.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
import folium
from streamlit_folium import st_folium

import config as cfg
from core.db import add_report, decay_report_weights, get_engine, get_reports
from core.nlp_filter import check_rate_limit, classify_report_text
from core.ui import disclaimer, page_header, sidebar_footer, synthetic_notice

st.set_page_config(page_title=f"Community Reports — {cfg.APP_TITLE}", page_icon="📢", layout="wide")

page_header("📢 Anonymous Community Safety Reports", "Crowdsourced safety hazards, illumination audits, and positive safe spots.")
disclaimer()
synthetic_notice()

engine = get_engine()

# Unique browser session identifier for rate limiting
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())

# ---------------------------------------------------------------------------
# Section 1: Submit Anonymous Safety Report
# ---------------------------------------------------------------------------
with st.expander("📝 Report a Safety Hazard or Positive Safe Spot", expanded=True):
    with st.form("community_report_form"):
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox(
                "Report Category",
                options=[
                    "poor_lighting",
                    "harassment",
                    "isolated_area",
                    "broken_cctv",
                    "unsafe_auto_stand",
                    "felt_safe",
                ],
                format_func=lambda x: {
                    "poor_lighting": "💡 Poor / Broken Street Lighting",
                    "harassment": "⚠️ Harassment / Stalking Incident",
                    "isolated_area": "🌑 Deserted / Isolated Stretch",
                    "broken_cctv": "📹 Broken / Missing CCTV Coverage",
                    "unsafe_auto_stand": "🛺 Unregulated / Unsafe Auto Stand",
                    "felt_safe": "🛡️ Felt Safe Here (Active / Well-Patrolled)",
                }.get(x, x),
            )
            report_place = st.selectbox("Landmark Area", list(cfg.PILOT_PLACES.keys()))

        with col2:
            time_of_day = st.slider("Approximate Hour Incident Occurred (24h clock)", 0, 23, 21, format="%02d:00")
            description = st.text_area(
                "Description / Context (English or Hinglish)",
                placeholder="e.g. 'Street lights off near underpass', 'Police PCR booth was active here', 'Dark cut near metro exit'",
            )

        st.caption("🔒 Privacy Guarantee: Your submission is completely anonymous. IP address and personal credentials are never logged.")
        submit_btn = st.form_submit_button("Submit Anonymous Report", type="primary")

        if submit_btn:
            # 1. Rate limiting check
            allowed, rate_msg = check_rate_limit(st.session_state.session_id)
            if not allowed:
                st.error(rate_msg)
            else:
                # 2. NLP spam and quality check
                is_valid, conf, reason = classify_report_text(description)
                if not is_valid:
                    st.warning(f"Report could not be accepted: {reason}")
                else:
                    coords = cfg.PILOT_PLACES.get(report_place, (28.6315, 77.2167))
                    add_report(
                        engine=engine,
                        lat=coords[0],
                        lon=coords[1],
                        category=category,
                        description=description.strip() if description else None,
                        hour_of_day=time_of_day,
                        is_demo=cfg.DEMO_MODE,
                        is_spam=False,
                    )
                    st.success("✅ Report submitted! Thank you for protecting the community. This report will now calibrate model routing.")

# ---------------------------------------------------------------------------
# Section 2: Active Reports Heatmap & Map View
# ---------------------------------------------------------------------------
st.divider()
st.subheader("🗺️ Recent Community Hazard & Safety Map")

col_act1, col_act2 = st.columns([3, 1])
with col_act2:
    if st.button("🔄 Recalculate 90-Day Time Decay"):
        updated_n = decay_report_weights(engine)
        st.success(f"Recalculated decay for {updated_n} reports.")

reports = get_reports(engine, exclude_spam=True, limit=300)

c_lat, c_lon = cfg.pilot_center()
tile_url, tile_attr = cfg.get_map_tile_layer()
if tile_attr:
    m = folium.Map(location=[c_lat, c_lon], zoom_start=12, tiles=tile_url, attr=tile_attr)
else:
    m = folium.Map(location=[c_lat, c_lon], zoom_start=12, tiles=tile_url)

color_map = {
    "felt_safe": "green",
    "poor_lighting": "orange",
    "harassment": "red",
    "isolated_area": "darkred",
    "broken_cctv": "purple",
    "unsafe_auto_stand": "cadetblue",
}

for r in reports:
    marker_color = color_map.get(r.category, "blue")
    icon_type = "ok" if r.category == "felt_safe" else "exclamation-sign"
    weight_pct = int(round(r.weight * 100))
    popup_text = f"""
    <b>{r.category.upper().replace('_', ' ')}</b><br>
    Time reported: {r.hour_of_day or 'N/A'}:00<br>
    <i>"{r.description or 'No text details'}"</i><br>
    <small>Influence Weight: {weight_pct}% (Half-life 90 days)</small>
    """
    folium.Marker(
        location=[r.lat, r.lon],
        popup=folium.Popup(popup_text, max_width=250),
        tooltip=f"{r.category} ({weight_pct}% weight)",
        icon=folium.Icon(color=marker_color, icon=icon_type),
    ).add_to(m)

st_folium(m, width="100%", height=450)

# Reports Table
if reports:
    with st.expander(f"📋 View All Community Submissions ({len(reports)} entries)"):
        table_data = [
            {
                "Category": r.category,
                "Time (Hour)": f"{r.hour_of_day}:00" if r.hour_of_day is not None else "N/A",
                "Description": r.description or "—",
                "Current Weight": f"{round(r.weight * 100)}%",
                "Submitted At": r.created_at[:10],
                "Demo Flag": "Yes" if r.is_demo else "No",
            }
            for r in reports
        ]
        st.dataframe(table_data, width="stretch")

sidebar_footer()
