"""
pages/6_Trip_Sharing.py
=======================
Live Trip Sharing & Real-Time Journey Tracking.

Allows a traveller to generate a private, shareable trip tracker with
their trusted contacts or family, showing origin, destination, ETA, and
real-time status updates without third-party tracking apps.
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
from core.db import create_trip_share, get_engine, get_trip_share, update_trip_status
from core.geo_utils import distance_m, geocode_or_pilot_place
from core.live_location import get_live_tracking_links, render_live_location_widget
from core.ui import disclaimer, page_header, sidebar_footer

st.set_page_config(page_title=f"Trip Sharing — {cfg.APP_TITLE}", page_icon="📍", layout="wide")

page_header("📍 Live Trip Sharing", "Generate a secure, private trip monitoring link for family or trusted friends.")
disclaimer()

engine = get_engine()

# Read token from query params if someone opened a shared link
query_params = st.query_params
active_token = query_params.get("trip_token", None)

tab_create, tab_view = st.tabs(["🚀 Start & Share a New Trip", "👀 View / Monitor Shared Trip"])

# ---------------------------------------------------------------------------
# Tab 1: Start New Trip
# ---------------------------------------------------------------------------
with tab_create:
    st.subheader("Start Monitored Journey")

    trip_lat, trip_lon, trip_addr, is_live_start = render_live_location_widget(
        label="Capture My Departure GPS Location",
        key_prefix="trip_start_gps",
        show_mini_map=False,
    )

    with st.form("new_trip_form"):
        col1, col2 = st.columns(2)
        with col1:
            use_gps_origin = st.checkbox("Use Live GPS as Origin", value=is_live_start)
            if use_gps_origin and trip_addr:
                origin = trip_addr
                st.caption(f"Starting from: {origin}")
            else:
                origin = st.selectbox("Journey Origin", list(cfg.PILOT_PLACES.keys()), index=0)
            dest = st.selectbox("Journey Destination", list(cfg.PILOT_PLACES.keys()), index=3)
        with col2:
            mode = st.selectbox("Transit Mode", ["Cab / Taxi (Ola/Uber)", "Auto Rickshaw", "Metro + Walk", "Personal Vehicle"])
            vehicle_plate = st.text_input("Vehicle Number (Optional but recommended)", placeholder="e.g. DL 1R AB 1234")

        trip_note = st.text_input("Traveller note for family:", value=f"Travelling via {mode}. Expected travel time ~25 mins.")
        start_btn = st.form_submit_button("Generate Secure Shareable Trip Link", type="primary")

        if start_btn:
            coords = (trip_lat, trip_lon) if use_gps_origin else cfg.PILOT_PLACES.get(origin, (28.6315, 77.2167))
            combined_note = f"{trip_note} | Vehicle: {vehicle_plate}" if vehicle_plate else trip_note
            trip = create_trip_share(
                engine=engine,
                origin=origin,
                destination=dest,
                lat=coords[0],
                lon=coords[1],
                note=combined_note,
            )
            st.session_state["created_token"] = trip.token
            st.success("🎉 Trip monitor initialized!")

    if "created_token" in st.session_state:
        token = st.session_state["created_token"]
        st.info(f"**Your Private Trip Token:** `{token}`")
        share_url = f"http://localhost:8501/Trip_Sharing?trip_token={token}"
        st.text_input("📋 Copy Link for Family/WhatsApp:", value=share_url)
        st.markdown(f"[📲 Open and Send via WhatsApp](https://api.whatsapp.com/send?text=Tracking%20my%20trip%20on%20Mahila%20Suraksha%20Marg:%20{share_url})")

# ---------------------------------------------------------------------------
# Tab 2: Monitor Shared Trip
# ---------------------------------------------------------------------------
with tab_view:
    st.subheader("Monitor Active Journey")
    token_input = st.text_input("Enter Trip Token:", value=active_token or st.session_state.get("created_token", ""))

    if token_input:
        trip = get_trip_share(engine, token_input.strip())
        if not trip:
            st.error("No trip found with this token. Please verify with the sender.")
        else:
            status_colors = {
                "active": "#2980B9",
                "in_transit": "#E67E22",
                "arrived": "#27AE60",
                "emergency": "#C0392B",
            }
            bg = status_colors.get(trip.status, "#555")

            st.markdown(
                f"""
                <div style="background-color: {bg}; color: white; padding: 18px; border-radius: 10px; margin-bottom: 20px;">
                    <h3 style="margin: 0; color: white;">Status: {trip.status.upper().replace('_', ' ')}</h3>
                    <p style="margin: 5px 0 0 0;">Route: <b>{trip.origin}</b> ➔ <b>{trip.destination}</b></p>
                    <small>Last updated: {trip.updated_at} UTC</small>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if trip.note:
                st.info(f"📝 **Note from traveller:** {trip.note}")

            # Traveller Status Controller
            st.markdown("**Traveller Status Actions:**")
            act_col1, act_col2, act_col3 = st.columns(3)
            with act_col1:
                if st.button("🟢 Mark as Arrived Safely", width="stretch"):
                    update_trip_status(engine, trip.token, "arrived")
                    st.success("Trip updated to ARRIVED.")
                    st.rerun()
            with act_col2:
                if st.button("🟡 In Transit / Moving", width="stretch"):
                    update_trip_status(engine, trip.token, "in_transit")
                    st.rerun()
            with act_col3:
                if st.button("🔴 Report Alert / Delay", width="stretch"):
                    update_trip_status(engine, trip.token, "emergency")
                    st.rerun()

            # Traveller live GPS update expander
            with st.expander("🛰️ Update Live Coordinates (For Traveller)", expanded=False):
                up_lat, up_lon, up_addr, up_live = render_live_location_widget(
                    label="Transmit My Current Location",
                    key_prefix=f"update_{trip.token}",
                    show_mini_map=False,
                )
                if st.button("📡 Broadcast Updated Location to Family", type="primary"):
                    update_trip_status(engine, trip.token, trip.status, lat=up_lat, lon=up_lon)
                    st.success(f"Position updated to: {up_addr}")
                    st.rerun()

            # Map view of trip origin, destination & live traveller pin
            orig_pt = geocode_or_pilot_place(trip.origin) or (28.6315, 77.2167)
            dest_pt = geocode_or_pilot_place(trip.destination) or (28.5245, 77.2066)
            current_traveller_pt = (trip.lat, trip.lon) if (trip.lat and trip.lon) else orig_pt

            tile_url, tile_attr = cfg.get_map_tile_layer()
            if tile_attr:
                m = folium.Map(
                    location=[current_traveller_pt[0], current_traveller_pt[1]],
                    zoom_start=13,
                    tiles=tile_url,
                    attr=tile_attr,
                )
            else:
                m = folium.Map(
                    location=[current_traveller_pt[0], current_traveller_pt[1]],
                    zoom_start=13,
                    tiles=tile_url,
                )
            folium.Marker(orig_pt, popup=f"Origin: {trip.origin}", icon=folium.Icon(color="green")).add_to(m)
            folium.Marker(dest_pt, popup=f"Destination: {trip.destination}", icon=folium.Icon(color="red")).add_to(m)
            folium.PolyLine([orig_pt, dest_pt], color="#7B2D8E", weight=4, dash_array="10").add_to(m)

            # Glowing Live Traveller Marker
            folium.Circle(
                location=current_traveller_pt,
                radius=45,
                color="#00C9FF",
                fill=True,
                fill_color="#00C9FF",
                fill_opacity=0.35,
                tooltip="Traveller GPS Uncertainty Radius",
            ).add_to(m)
            folium.CircleMarker(
                location=current_traveller_pt,
                radius=10,
                color="#FFFFFF",
                weight=3,
                fill=True,
                fill_color="#00C9FF",
                fill_opacity=1.0,
                popup=f"<b>📍 Traveller Live Position</b><br>Lat: {current_traveller_pt[0]:.5f}, Lon: {current_traveller_pt[1]:.5f}",
                tooltip="📍 Traveller Current Real-Time Position",
            ).add_to(m)

            st_folium(m, width="100%", height=380)

            # Quick external link for family
            gmaps_live = f"https://www.google.com/maps/search/?api=1&query={current_traveller_pt[0]},{current_traveller_pt[1]}"
            st.markdown(f"📍 [Open Traveller's Current Position on Google Maps]({gmaps_live})")

sidebar_footer()
