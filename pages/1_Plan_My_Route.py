"""
pages/1_Plan_My_Route.py
========================
Epic Google Maps Navigation & AI Route Advisor for Delhi-NCR.

Features:
- Google Maps 2-column layout (Left: Navigation & Route Cards; Right: 700px Epic Map Canvas)
- Active route selection: selected corridor glows with animated marching AntPath; alternatives are dimmed in secondary grey
- One-tap "Start Live Navigation in Google Maps" launcher
- Step-by-step turn-by-turn safety guidance maneuvers
- Multi-layer tile switcher (Dark Matter, Satellite Imagery, Detailed Street Nav, Cyberpunk)
- Interactive GPS device telemetry, fullscreen, measurement tool & minimap
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
from streamlit_folium import st_folium

import config as cfg
from core.db import add_route_feedback, get_engine
from core.live_location import render_live_location_widget
from core.map_builder import build_enhanced_route_map, generate_turn_by_turn_waypoints
from core.route_engine import plan_three_routes
from core.ui import disclaimer, page_header, sidebar_footer, synthetic_notice

st.set_page_config(page_title=f"Plan Route — {cfg.APP_TITLE}", page_icon="🧭", layout="wide")

page_header("🧭 Plan My Route", "Google Maps-Style Intelligent Navigation & Safety Advisor for Delhi-NCR.")

disclaimer()
synthetic_notice()

# ---------------------------------------------------------------------------
# Navigation Command Center & Master-Detail Layout
# ---------------------------------------------------------------------------
nav_col, map_col = st.columns([1.18, 2.32], gap="large")

pilot_places_list = list(cfg.PILOT_PLACES.keys())
origin_coords = None

with nav_col:
    # -----------------------------------------------------------------------
    # 1. Google Maps Floating Search Card
    # -----------------------------------------------------------------------
    st.markdown(
        """
        <div style="background: #1A1C24; border: 1px solid #2D3139; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.5);">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <span style="font-weight: 700; color: #BB86FC; font-size: 15px; letter-spacing: 0.5px;">📍 ROUTE SEARCH</span>
                <span style="background: #2D3139; color: #38BDF8; font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: 600;">LIVE NAV</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    use_live_gps = st.checkbox("🛰️ Auto-Fill Origin with Live Device GPS", value=False)
    if use_live_gps:
        live_lat, live_lon, live_addr, is_live = render_live_location_widget(
            label="Acquire GPS Origin",
            key_prefix="route_origin",
            show_mini_map=False,
        )
        origin = live_addr or f"Live GPS ({live_lat:.4f}, {live_lon:.4f})"
        origin_coords = (live_lat, live_lon)
    else:
        origin = st.selectbox(
            "🔵 Start Departure Point:",
            options=pilot_places_list + ["Custom input..."],
            index=0,
            help="Departure location in Delhi.",
        )
        if origin == "Custom input...":
            origin = st.text_input("Enter starting address / landmark:", value="Connaught Place, Delhi")

    dest_idx = 3 if len(pilot_places_list) > 3 else 1
    destination = st.selectbox(
        "🔴 Final Destination:",
        options=pilot_places_list + ["Custom input..."],
        index=dest_idx,
        help="Destination location in Delhi.",
    )
    if destination == "Custom input...":
        destination = st.text_input("Enter destination address / landmark:", value="Saket, Delhi")

    time_col, mode_col = st.columns([1.2, 1.0])
    with time_col:
        travel_hour = st.slider(
            "🕒 Travel Time",
            min_value=0,
            max_value=23,
            value=cfg.DEFAULT_TRAVEL_HOUR,
            format="%02d:00",
            help="Night multiplier triggers from 21:00 to 05:00.",
        )
    with mode_col:
        transit_mode = st.selectbox("🚗 Transit", ["Driving", "Cab / Auto", "Walking"], index=0)

    if travel_hour >= 21 or travel_hour < 6:
        st.caption(f"🌙 **Night Shield Active ({travel_hour:02d}:00)**: Avoids unlit service cuts.")

    # -----------------------------------------------------------------------
    # Compute Routes
    # -----------------------------------------------------------------------
    with st.spinner("Calculating safety penalties & computing routes..."):
        route_data = plan_three_routes(
            origin_name=origin,
            destination_name=destination,
            travel_hour=travel_hour,
            origin_coords=origin_coords,
        )

    routes = route_data["routes"]
    origin_coords = route_data["origin_coords"]
    dest_coords = route_data["dest_coords"]

    # -----------------------------------------------------------------------
    # 2. Google Maps Route Option Cards (Clickable Selection)
    # -----------------------------------------------------------------------
    st.markdown("#### Choose Your Route")

    route_choices = ["Safest", "Balanced", "Fastest"]
    selected_route_key = st.radio(
        "Select active route to highlight on map:",
        options=route_choices,
        index=0,
        horizontal=True,
        label_visibility="collapsed",
    )

    # Render card for each route
    for r_key in route_choices:
        r = routes[r_key]
        score = r["safety_score"]
        is_selected = (r_key == selected_route_key)

        if score >= 85:
            score_color = "#2ECC71"
        elif score >= 65:
            score_color = "#00C9FF"
        elif score >= 45:
            score_color = "#E67E22"
        else:
            score_color = "#C0392B"

        border_style = f"3px solid {r['color']}" if is_selected else "1px solid #2D3139"
        bg_card = "#222530" if is_selected else "#16181F"
        badge_text = "RECOMMENDED · BEST ILLUMINATION" if r_key == "Safest" else ("OPTIMAL TRADE-OFF" if r_key == "Balanced" else "SHORTEST PHYSICAL DISTANCE")

        st.markdown(
            f"""
            <div style="border: {border_style}; border-radius: 10px; padding: 12px 14px; background: {bg_card}; margin-bottom: 8px; transition: all 0.2s;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 700; color: {r['color']}; font-size: 16px;">{r['name']}</span>
                    <span style="font-size: 11px; background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px; color: #CBD5E1;">{badge_text}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 6px;">
                    <div>
                        <span style="font-size: 22px; font-weight: 800; color: #FFF;">{r['eta_mins']} min</span>
                        <span style="color: #94A3B8; font-size: 14px; margin-left: 6px;">({r['distance_km']} km)</span>
                    </div>
                    <div>
                        <span style="font-size: 18px; font-weight: 800; color: {score_color};">{score}/100</span>
                        <span style="font-size: 12px; color: #CBD5E1; margin-left: 4px;">{r['caution_level']}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # -----------------------------------------------------------------------
    # 3. Google Maps Primary Action: Launch Live Turn-by-Turn
    # -----------------------------------------------------------------------
    active_route = routes[selected_route_key]
    gmaps_nav_url = (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={origin_coords[0]},{origin_coords[1]}"
        f"&destination={dest_coords[0]},{dest_coords[1]}"
        f"&travelmode=driving"
    )

    st.markdown(
        f"""
        <div style="margin: 14px 0;">
            <a href="{gmaps_nav_url}" target="_blank" style="text-decoration: none;">
                <div style="background: linear-gradient(135deg, #1A73E8, #0D47A1); color: white; padding: 14px; border-radius: 8px; text-align: center; font-size: 16px; font-weight: bold; box-shadow: 0 4px 14px rgba(26,115,232,0.4);">
                    🚀 START NAVIGATION IN GOOGLE MAPS
                </div>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -----------------------------------------------------------------------
    # 4. Turn-by-Turn Safety Guidance Drawer
    # -----------------------------------------------------------------------
    with st.expander(f"📋 Step-by-Step Safety Guidance for {selected_route_key} Route", expanded=True):
        waypoints = generate_turn_by_turn_waypoints(active_route, origin, destination)
        for wp in waypoints:
            st.markdown(
                f"""
                <div style="display: flex; align-items: flex-start; margin-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 8px;">
                    <div style="font-size: 20px; margin-right: 12px; line-height: 1.2;">{wp['icon']}</div>
                    <div style="flex-grow: 1;">
                        <div style="font-size: 14px; font-weight: 600; color: #FFF;">{wp['maneuver']}</div>
                        <div style="font-size: 12px; color: #94A3B8; margin-top: 2px;">{wp['detail']}</div>
                        <span style="display: inline-block; font-size: 10px; background: rgba(255,255,255,0.06); color: {wp['tag_color']}; padding: 1px 6px; border-radius: 4px; margin-top: 4px; font-weight: 600;">
                            {wp['safety_tag']}
                        </span>
                    </div>
                    <div style="font-size: 12px; color: #64748B; font-weight: 600; min-width: 45px; text-align: right;">{wp['dist_cum']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # -----------------------------------------------------------------------
    # 5. Continuous Learning Feedback
    # -----------------------------------------------------------------------
    with st.expander("⭐ Rate This Route to Train the AI", expanded=False):
        with st.form("quick_feedback_form"):
            f_rating = st.slider("Safety Rating", 1, 5, 4)
            f_safe = st.radio("Felt safe?", ["Yes", "No"], horizontal=True) == "Yes"
            f_police = st.checkbox("Saw active police / PCR patrol")
            f_note = st.text_input("Comment (e.g. good lighting, isolated lane)")
            if st.form_submit_button("Submit Rating"):
                add_route_feedback(
                    engine=get_engine(),
                    route_type=selected_route_key,
                    origin=origin,
                    destination=destination,
                    rating=f_rating,
                    felt_safe=f_safe,
                    lighting_rating=4 if f_safe else 2,
                    crowd_rating=4 if f_safe else 2,
                    police_patrol_seen=f_police,
                    comments=f_note,
                    travel_hour=travel_hour,
                )
                st.success("Feedback saved & incorporated into route weights!")

# ---------------------------------------------------------------------------
# Right Column: Epic 720px Google Maps Canvas
# ---------------------------------------------------------------------------
with map_col:
    map_tab1, map_tab2 = st.tabs([
        "🛡️ AI Safety Route Map (Official Google Maps Tiles)",
        "🌐 Live Google Maps Web Navigation (Native View)",
    ])

    live_user_pt = (live_lat, live_lon) if (use_live_gps and 'live_lat' in locals()) else None

    with map_tab1:
        # Style selector bar directly above the map
        style_choice = st.radio(
            "Select Map Style:",
            options=[
                "🗺️ Google Maps (Standard)",
                "🛰️ Google Satellite (Hybrid)",
                "🚦 Google Live Traffic",
                "🌙 Dark Safety Mode",
            ],
            index=0,
            horizontal=True,
            label_visibility="collapsed",
        )

        style_map = {
            "🗺️ Google Maps (Standard)": "google_roads",
            "🛰️ Google Satellite (Hybrid)": "google_satellite",
            "🚦 Google Live Traffic": "google_traffic",
            "🌙 Dark Safety Mode": "dark_matter",
        }
        chosen_style = style_map.get(style_choice, "google_roads")

        # Build the enhanced map with Google Maps tiles & the active route prominently highlighted
        m = build_enhanced_route_map(
            routes=routes,
            origin_coords=origin_coords,
            dest_coords=dest_coords,
            origin_name=origin,
            dest_name=destination,
            travel_hour=travel_hour,
            active_route_key=selected_route_key,
            default_style=chosen_style,
            live_user_coords=live_user_pt,
        )

        # Render expansive 720px tall map viewport
        st_folium(m, width="100%", height=720, key=f"route_map_{chosen_style}_{selected_route_key}")

    with map_tab2:
        st.markdown(
            """
            <div style="background: rgba(26,115,232,0.1); border-left: 4px solid #1A73E8; padding: 10px 14px; border-radius: 6px; margin-bottom: 10px;">
                <span style="font-weight: 700; color: #1A73E8;">🌐 Live Google Maps Driving & Walking Interface</span>
                <div style="font-size: 13px; color: #AAA;">Direct interactive Google Maps navigation between your departure and destination coordinates.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        embed_url = f"https://maps.google.com/maps?saddr={origin_coords[0]},{origin_coords[1]}&daddr={dest_coords[0]},{dest_coords[1]}&output=embed"
        st.components.v1.iframe(embed_url, height=720, scrolling=True)

sidebar_footer()
