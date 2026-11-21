"""
core/live_location.py
=====================
Live GPS Location Tracking & Real-Time Geolocation Service.

Provides:
- One-click device GPS coordinate acquisition via browser/phone Geolocation API
- High-accuracy reverse geocoding via Geoapify API & Nominatim
- Proximity resolution to pilot landmarks (Connaught Place, Saket, etc.)
- Visual live pulsing beacon map with accuracy radius
- Live Google Maps & OpenStreetMap tracking links
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import folium
import requests
import streamlit as st
from streamlit_folium import st_folium

try:
    from streamlit_geolocation import streamlit_geolocation
    _HAS_GEO = True
except ImportError:
    _HAS_GEO = False

import config as cfg
from core.geo_utils import distance_m

log = logging.getLogger(__name__)


def reverse_geocode_coords(lat: float, lon: float) -> str:
    """
    Reverse geocodes (lat, lon) into a clean, human-readable Delhi street address.
    Uses Google Maps first, then Geoapify, then landmark proximity.
    """
    if cfg.GOOGLE_MAPS_API_KEY:
        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            resp = requests.get(
                url,
                params={"latlng": f"{lat},{lon}", "key": cfg.GOOGLE_MAPS_API_KEY},
                timeout=4,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "OK":
                    results = data.get("results", [])
                    if results:
                        formatted = results[0].get("formatted_address")
                        if formatted:
                            return formatted
        except Exception as exc:
            log.warning("Google reverse geocode failed: %s", exc)

    if cfg.MAPS_API_KEY:
        try:
            url = "https://api.geoapify.com/v1/geocode/reverse"
            resp = requests.get(
                url,
                params={"lat": lat, "lon": lon, "apiKey": cfg.MAPS_API_KEY, "limit": 1},
                timeout=4,
            )
            if resp.status_code == 200:
                features = resp.json().get("features", [])
                if features:
                    formatted = features[0].get("properties", {}).get("formatted")
                    if formatted:
                        return formatted
        except Exception as exc:
            log.warning("Geoapify reverse geocode failed: %s", exc)

    # Fallback to proximity to closest known Delhi pilot landmarks
    closest_place = None
    min_dist = float("inf")
    for name, coords in cfg.PILOT_PLACES.items():
        d = distance_m((lat, lon), coords)
        if d < min_dist:
            min_dist = d
            closest_place = name

    if closest_place:
        if min_dist < 100:
            return f"At {closest_place}, Delhi"
        elif min_dist < 1000:
            return f"Near {closest_place} (~{int(min_dist)}m away), Delhi"
        else:
            return f"{closest_place} sector (~{min_dist/1000:.1f} km away), Delhi"

    return f"Delhi coordinates ({lat:.4f}° N, {lon:.4f}° E)"


def get_live_tracking_links(lat: float, lon: float) -> dict[str, str]:
    """Generates direct live location URLs for Google Maps and OpenStreetMap."""
    return {
        "google_maps": f"https://www.google.com/maps/search/?api=1&query={lat:.6f},{lon:.6f}",
        "google_directions": f"https://www.google.com/maps/dir/?api=1&destination={lat:.6f},{lon:.6f}",
        "osm": f"https://www.openstreetmap.org/?mlat={lat:.6f}&mlon={lon:.6f}#map=16/{lat:.6f}/{lon:.6f}",
    }


def render_live_location_widget(
    label: str = "📍 Detect My Live GPS Location",
    key_prefix: str = "gps",
    show_mini_map: bool = True,
) -> Tuple[float, float, str, bool]:
    """
    Renders an interactive GPS locator with device sensor integration.

    Returns:
        (latitude, longitude, readable_address, is_live_detected)
    """
    # Check session state for existing locked location
    live_lat = st.session_state.get(f"{key_prefix}_lat", None)
    live_lon = st.session_state.get(f"{key_prefix}_lon", None)
    live_acc = st.session_state.get(f"{key_prefix}_acc", None)
    live_addr = st.session_state.get(f"{key_prefix}_addr", "")
    is_live = live_lat is not None and live_lon is not None

    st.markdown(
        """
        <div style="background: rgba(187, 134, 252, 0.08); border-left: 4px solid #BB86FC; padding: 10px 14px; border-radius: 6px; margin-bottom: 12px;">
            <span style="font-weight: 600; color: #BB86FC;">🛰️ Live Device GPS Telemetry</span>
            <div style="font-size: 13px; color: #BBB;">Click below to capture your real-time coordinates via device sensor or browser GPS.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    btn_col, status_col = st.columns([1.2, 2.8])

    with btn_col:
        st.write(f"**{label}**")
        raw_geo = None
        if _HAS_GEO:
            raw_geo = streamlit_geolocation()

        # If user clicked the geolocation button and coordinates were received
        if raw_geo and raw_geo.get("latitude") is not None and raw_geo.get("longitude") is not None:
            new_lat = float(raw_geo["latitude"])
            new_lon = float(raw_geo["longitude"])
            new_acc = float(raw_geo.get("accuracy") or 15.0)

            # Store in session state
            st.session_state[f"{key_prefix}_lat"] = new_lat
            st.session_state[f"{key_prefix}_lon"] = new_lon
            st.session_state[f"{key_prefix}_acc"] = new_acc
            st.session_state[f"{key_prefix}_addr"] = reverse_geocode_coords(new_lat, new_lon)

            # Also update global live location
            st.session_state["global_live_lat"] = new_lat
            st.session_state["global_live_lon"] = new_lon
            st.session_state["global_live_addr"] = st.session_state[f"{key_prefix}_addr"]

            live_lat, live_lon, live_acc = new_lat, new_lon, new_acc
            live_addr = st.session_state[f"{key_prefix}_addr"]
            is_live = True

    with status_col:
        if is_live and live_lat and live_lon:
            st.success(
                f"🛰️ **GPS Locked**: `{live_lat:.5f}° N, {live_lon:.5f}° E`  \n"
                f"📍 **Address**: {live_addr}  \n"
                f"🎯 **Sensor Accuracy**: ±{int(live_acc or 15)} metres"
            )
        else:
            st.caption("Waiting for device GPS signal... (Or select a preset landmark below)")

    # Provide manual override / preset fallback if on desktop without GPS hardware
    with st.expander("⚙️ Manual Coordinate Override / Landmark Presets", expanded=not is_live):
        preset_col, lat_col, lon_col = st.columns([2, 1, 1])
        with preset_col:
            selected_preset = st.selectbox(
                "Delhi Landmark Preset:",
                options=["(None - Use Custom GPS)"] + list(cfg.PILOT_PLACES.keys()),
                index=0,
                key=f"{key_prefix}_preset_select",
            )
            if selected_preset != "(None - Use Custom GPS)":
                p_lat, p_lon = cfg.PILOT_PLACES[selected_preset]
                live_lat, live_lon = p_lat, p_lon
                live_acc = 5.0
                live_addr = f"{selected_preset}, Delhi"
                is_live = True
                st.session_state[f"{key_prefix}_lat"] = live_lat
                st.session_state[f"{key_prefix}_lon"] = live_lon
                st.session_state[f"{key_prefix}_addr"] = live_addr

        with lat_col:
            manual_lat = st.number_input(
                "Latitude",
                value=float(live_lat or 28.6315),
                format="%.5f",
                key=f"{key_prefix}_man_lat",
            )
        with lon_col:
            manual_lon = st.number_input(
                "Longitude",
                value=float(live_lon or 77.2167),
                format="%.5f",
                key=f"{key_prefix}_man_lon",
            )

        if not is_live:
            live_lat, live_lon = manual_lat, manual_lon
            live_addr = reverse_geocode_coords(live_lat, live_lon)
            live_acc = 20.0

    # Optional mini beacon map
    if show_mini_map and live_lat and live_lon:
        render_live_beacon_map(live_lat, live_lon, accuracy=live_acc or 20.0, address=live_addr)

    return float(live_lat or 28.6315), float(live_lon or 77.2167), live_addr, is_live


def render_live_beacon_map(
    lat: float,
    lon: float,
    accuracy: float = 20.0,
    address: str = "Live Location",
    map_height: int = 240,
) -> None:
    """Renders a dark-theme live GPS beacon map with pulsing accuracy circle."""
    m = folium.Map(
        location=[lat, lon],
        zoom_start=16,
        tiles=None,
        control_scale=True,
    )
    # Add dark tiles
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://carto.com/">CARTO</a>',
        name="CartoDB Dark Matter",
        max_zoom=19,
    ).add_to(m)

    # Accuracy halo (blue translucent radius)
    folium.Circle(
        location=[lat, lon],
        radius=max(accuracy, 25.0),
        color="#3498DB",
        fill=True,
        fill_color="#2980B9",
        fill_opacity=0.25,
        weight=1,
        tooltip=f"GPS Uncertainty Radius: ±{int(accuracy)}m",
    ).add_to(m)

    # Core Beacon Pin
    folium.CircleMarker(
        location=[lat, lon],
        radius=9,
        color="#FFFFFF",
        weight=2.5,
        fill=True,
        fill_color="#00C9FF",
        fill_opacity=0.95,
        popup=f"<b>📍 You Are Here</b><br>{address}<br><small>Lat: {lat:.5f}, Lon: {lon:.5f}</small>",
        tooltip="📍 Current Real-Time GPS Position",
    ).add_to(m)

    st_folium(m, height=map_height, width=None, key=f"beacon_map_{lat:.4f}_{lon:.4f}")
