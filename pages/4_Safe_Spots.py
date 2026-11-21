"""
pages/4_Safe_Spots.py
=====================
Nearby Safe Havens & Verified Assistance Spots.

Locates verified safety sanctuaries within the Delhi-NCR pilot zone:
- 🚔 Police Stations & Assistance Booths
- 🏥 24/7 Hospitals & Trauma Centers
- 💊 Open Pharmacies
- 🚇 Metro Stations (CCTV monitored, active security personnel)
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
from core.geo_utils import distance_m
from core.live_location import render_live_location_widget
from core.map_builder import create_base_map
from core.osm_features import load_safe_spots
import folium.plugins as fp
from core.ui import disclaimer, page_header, sidebar_footer

st.set_page_config(page_title=f"Safe Spots — {cfg.APP_TITLE}", page_icon="🛡️", layout="wide")

page_header("🛡️ Nearby Safe Havens & Police Posts", "Locate verified illuminated hubs, active police stations, and 24/7 emergency medical posts.")
disclaimer()

# Fallback verified Delhi hubs if Overpass GeoJSON not yet generated
DEFAULT_SAFE_SPOTS = [
    {"name": "Connaught Place Police Station", "category": "police", "lat": 28.6315, "lon": 77.2167, "desc": "24/7 Police Station with Women Desk"},
    {"name": "Parliament Street Police Station", "category": "police", "lat": 28.6235, "lon": 77.2120, "desc": "Central Delhi Police Post"},
    {"name": "North Avenue Police Post", "category": "police", "lat": 28.6175, "lon": 77.2105, "desc": "Police assistance post near Parliament Zone"},
    {"name": "Tilak Marg Police Station", "category": "police", "lat": 28.6248, "lon": 77.2372, "desc": "Central District police station"},
    {"name": "Chanakyapuri Police Station", "category": "police", "lat": 28.5998, "lon": 77.1740, "desc": "New Delhi District police station"},
    {"name": "Kalkaji Police Station", "category": "police", "lat": 28.5443, "lon": 77.2541, "desc": "South East Delhi police station"},
    {"name": "Lajpat Nagar Police Station", "category": "police", "lat": 28.5700, "lon": 77.2400, "desc": "South Delhi Police Division"},
    {"name": "Saket Police Station", "category": "police", "lat": 28.5200, "lon": 77.2100, "desc": "South District Police Station"},
    {"name": "Mehrauli Police Station", "category": "police", "lat": 28.5243, "lon": 77.1838, "desc": "South West Delhi police station"},
    {"name": "Nehru Place Police Station", "category": "police", "lat": 28.5500, "lon": 77.2497, "desc": "South East District police assistance"},
    {"name": "AIIMS New Delhi (Emergency Trauma)", "category": "hospital", "lat": 28.5672, "lon": 77.2100, "desc": "24/7 Apex Emergency Hospital"},
    {"name": "Safdarjung Hospital Emergency", "category": "hospital", "lat": 28.5705, "lon": 77.2078, "desc": "Round-the-clock Emergency Medical Services"},
    {"name": "Ram Manohar Lohia Hospital Emergency", "category": "hospital", "lat": 28.6255, "lon": 77.2065, "desc": "Central Delhi 24/7 emergency hospital"},
    {"name": "Lady Hardinge Medical College Emergency", "category": "hospital", "lat": 28.6259, "lon": 77.2108, "desc": "Emergency medical services in Central Delhi"},
    {"name": "Fortis C-DOC", "category": "hospital", "lat": 28.5676, "lon": 77.2255, "desc": "Hospital emergency and specialist services"},
    {"name": "Batra Hospital and Medical Research Centre", "category": "hospital", "lat": 28.5194, "lon": 77.2473, "desc": "Emergency hospital in Tughlakabad area"},
    {"name": "Max Super Speciality Hospital Saket", "category": "hospital", "lat": 28.5270, "lon": 77.2130, "desc": "24/7 Emergency & Pharmacy"},
    {"name": "Rajiv Chowk Metro Station", "category": "metro", "lat": 28.6328, "lon": 77.2195, "desc": "Major Intersecting DMRC Hub with CISF Security"},
    {"name": "Lajpat Nagar Metro Station", "category": "metro", "lat": 28.5708, "lon": 77.2375, "desc": "Pink/Violet Interchange with Security Desk"},
    {"name": "Kailash Colony Metro Station", "category": "metro", "lat": 28.5554, "lon": 77.2425, "desc": "Violet Line station with public transit security"},
    {"name": "South Extension Metro Station", "category": "metro", "lat": 28.5685, "lon": 77.2208, "desc": "Pink Line station near commercial services"},
    {"name": "Nehru Place Metro Station", "category": "metro", "lat": 28.5515, "lon": 77.2518, "desc": "Well-lit commercial transit hub"},
    {"name": "Malviya Nagar Metro Station", "category": "metro", "lat": 28.5292, "lon": 77.2068, "desc": "Yellow Line metro station"},
    {"name": "Apollo Pharmacy Connaught Place", "category": "pharmacy", "lat": 28.6330, "lon": 77.2175, "desc": "Medicine & First-Aid Store"},
    {"name": "Guardian Pharmacy Saket", "category": "pharmacy", "lat": 28.5255, "lon": 77.2085, "desc": "Illuminated retail pharmacy"},
    {"name": "Wellness Forever Lajpat Nagar", "category": "pharmacy", "lat": 28.5688, "lon": 77.2392, "desc": "Retail pharmacy near Lajpat Nagar"},
    {"name": "Apollo Pharmacy Nehru Place", "category": "pharmacy", "lat": 28.5488, "lon": 77.2504, "desc": "Retail pharmacy near Nehru Place"},
    {"name": "Connaught Place Fire Station", "category": "fire_station", "lat": 28.6288, "lon": 77.2266, "desc": "Emergency fire and rescue assistance"},
    {"name": "South Delhi Fire Station", "category": "fire_station", "lat": 28.5490, "lon": 77.2510, "desc": "Emergency fire and rescue assistance"},
]

# ---------------------------------------------------------------------------
# Filter Controls & Live GPS Proximity
# ---------------------------------------------------------------------------
with st.expander("🛰️ Real-Time Device GPS Proximity Locator", expanded=True):
    user_lat, user_lon, user_addr, is_live_user = render_live_location_widget(
        label="Capture My Live Location",
        key_prefix="spots_geo",
        show_mini_map=False,
    )

col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    show_police = st.checkbox("Police", value=True)
with col2:
    show_hospitals = st.checkbox("Hospitals", value=True)
with col3:
    show_metro = st.checkbox("Metro", value=True)
with col4:
    show_pharmacies = st.checkbox("Pharmacies", value=True)
with col5:
    show_fire = st.checkbox("Fire stations", value=True)
with col6:
    show_bus = st.checkbox("Bus stops", value=False)

# Load data
spots_gdf = load_safe_spots()
display_rows = []

category_enabled = {
    "police": show_police,
    "hospital": show_hospitals,
    "metro": show_metro,
    "pharmacy": show_pharmacies,
    "fire_station": show_fire,
    "bus_stop": show_bus,
}

if spots_gdf is not None and len(spots_gdf) > 0:
    for _, row in spots_gdf.iterrows():
        cat = str(row.get("category", "")).lower()
        if not category_enabled.get(cat, False):
            continue
        s_lat = float(row.geometry.y if hasattr(row.geometry, 'y') else row.get("lat", 28.58))
        s_lon = float(row.geometry.x if hasattr(row.geometry, 'x') else row.get("lon", 77.22))
        dist_val = distance_m((user_lat, user_lon), (s_lat, s_lon)) if (user_lat and user_lon) else None
        display_rows.append({
            "name": row.get("name") or f"Verified {cat.replace('_', ' ').title()} Point",
            "category": cat,
            "lat": s_lat,
            "lon": s_lon,
            "distance_m": dist_val,
            "desc": f"Verified OpenStreetMap {cat.replace('_', ' ')} spot",
        })

# Always retain curated Delhi hubs as coverage fallbacks, but remove duplicates
# when a live OSM entry is already within roughly 500 metres.
for item in DEFAULT_SAFE_SPOTS:
    cat = item["category"]
    if not category_enabled.get(cat, False):
        continue

    s_lat = float(item["lat"])
    s_lon = float(item["lon"])
    duplicate = any(
        row["category"] == cat
        and distance_m((row["lat"], row["lon"]), (s_lat, s_lon)) < 500
        for row in display_rows
    )
    if duplicate:
        continue

    dist_val = distance_m((user_lat, user_lon), (s_lat, s_lon)) if (user_lat and user_lon) else None
    display_rows.append({
        "name": item["name"],
        "category": cat,
        "lat": s_lat,
        "lon": s_lon,
        "distance_m": dist_val,
        "desc": item.get("desc", ""),
    })

# Sort by distance from user if live location available
if user_lat and user_lon:
    display_rows.sort(key=lambda x: x["distance_m"] if x["distance_m"] is not None else float("inf"))

# ---------------------------------------------------------------------------
# Closest Safe Spot Hero Banner
# ---------------------------------------------------------------------------
if user_lat and user_lon and display_rows:
    closest = display_rows[0]
    c_dist = closest["distance_m"]
    walk_mins = max(1, int(c_dist / 80))  # approx 80 m/min walking speed
    gmaps_nav = f"https://www.google.com/maps/dir/?api=1&origin={user_lat},{user_lon}&destination={closest['lat']},{closest['lon']}"

    st.markdown(
        f"""
        <div style="background: rgba(46, 204, 113, 0.12); border-left: 5px solid #2ECC71; padding: 14px 18px; border-radius: 8px; margin-bottom: 16px;">
            <div style="font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: #2ECC71; font-weight: bold;">
                🚨 Closest Safe Haven to You
            </div>
            <div style="font-size: 20px; font-weight: bold; color: #FFF; margin-top: 4px;">
                {closest['name']}
            </div>
            <div style="color: #DDD; font-size: 14px; margin-top: 4px;">
                📍 Distance: <b>{int(c_dist):,} metres</b> (~{walk_mins} min walk) &nbsp;|&nbsp; Category: <b>{closest['category'].upper()}</b>
            </div>
            <div style="margin-top: 10px;">
                <a href="{gmaps_nav}" target="_blank" style="background:#2ECC71; color:#0E1117; padding:6px 14px; border-radius:4px; text-decoration:none; font-weight:bold; font-size:13px;">
                    🧭 Open Direct Navigation in Google Maps
                </a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Map View
# ---------------------------------------------------------------------------
st.subheader(f"📍 Active Safe Havens ({len(display_rows)} spots found)")
st.caption(
    "💡 **Map Controls**: Switch between **🌙 Dark Matter**, **🛰️ Satellite View**, and **🏙️ Detailed Street Nav** using the bottom-left panel. "
    "Expand to **Fullscreen** via the top-right button or measure distances with the ruler tool."
)

map_center = (user_lat, user_lon) if (user_lat and user_lon) else cfg.pilot_center()
m = create_base_map(center=map_center, zoom_start=14 if is_live_user else 12)

# Add User Live Marker if present
if user_lat and user_lon:
    folium.Circle(
        location=[user_lat, user_lon],
        radius=40,
        color="#3498DB",
        fill=True,
        fill_color="#2980B9",
        fill_opacity=0.3,
        tooltip="Your GPS Location",
    ).add_to(m)
    folium.CircleMarker(
        location=[user_lat, user_lon],
        radius=10,
        color="#FFFFFF",
        weight=2.5,
        fill=True,
        fill_color="#00C9FF",
        fill_opacity=0.95,
        popup=f"<b>📍 You Are Here</b><br>{user_addr}",
        tooltip="📍 Current Real-Time Position",
    ).add_to(m)

    # Draw animated walking connector to the closest safe haven
    if display_rows:
        closest = display_rows[0]
        fp.AntPath(
            locations=[[user_lat, user_lon], [closest["lat"], closest["lon"]]],
            color="#2ECC71",
            pulse_color="#FFFFFF",
            weight=4,
            dash_array=[8, 16],
            delay=1000,
            tooltip=f"Quickest Escape Path to {closest['name']} (~{int(closest['distance_m']):,}m)",
        ).add_to(m)

cat_styles = {
    "police": {"color": "blue", "icon": "shield"},
    "hospital": {"color": "red", "icon": "plus-sign"},
    "metro": {"color": "purple", "icon": "road"},
    "pharmacy": {"color": "green", "icon": "medkit"},
    "fire_station": {"color": "orange", "icon": "fire"},
    "bus_stop": {"color": "cadetblue", "icon": "bus"},
}

for spot in display_rows:
    style = cat_styles.get(spot["category"], {"color": "gray", "icon": "info-sign"})
    gmaps_nav = f"https://www.google.com/maps/dir/?api=1&destination={spot['lat']},{spot['lon']}"
    dist_label = f"Distance from you: <b>{int(spot['distance_m']):,} m</b><br>" if spot.get("distance_m") else ""
    popup_html = f"""
    <b>{spot['name']}</b><br>
    Category: {spot['category'].upper()}<br>
    {dist_label}
    <i>{spot.get('desc', '')}</i><br><br>
    <a href="{gmaps_nav}" target="_blank">🧭 Navigate Here in Google Maps</a>
    """
    folium.Marker(
        location=[spot["lat"], spot["lon"]],
        tooltip=spot["name"],
        popup=folium.Popup(popup_html, max_width=300),
        icon=folium.Icon(color=style["color"], icon=style["icon"]),
    ).add_to(m)

folium.LayerControl(position="bottomleft", collapsed=False).add_to(m)

st_folium(m, width="100%", height=540)

# Quick Directory Table
with st.expander("📋 View List of Safe Spots (Sorted by Proximity)"):
    st.dataframe(display_rows, width="stretch")

sidebar_footer()
