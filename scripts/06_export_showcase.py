"""
scripts/06_export_showcase.py
=============================
Standalone Showcase Page Exporter for MAHILA SURAKSHA MARG.

Generates a self-contained, interactive HTML file (`demo.html`) using Folium.
Features:
- Sample routes (Fastest, Safest, Balanced) between Connaught Place and Saket.
- Color-coded route polylines and markers.
- HTML overlay card with 0-100 safety scores, caution levels, and top reasons.
- Emergency numbers and responsible-design disclaimer.
- Works offline in any modern web browser without running Streamlit!

Run:
    python scripts/06_export_showcase.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import folium
import config as cfg
from core.map_builder import build_enhanced_route_map
from core.route_engine import plan_three_routes

OUTPUT_HTML = PROJECT_ROOT / "demo.html"


def generate_showcase_html() -> Path:
    print("Generating standalone showcase export...")

    origin = "Connaught Place"
    destination = "Saket"
    travel_hour = 22

    route_plan = plan_three_routes(
        origin_name=origin,
        destination_name=destination,
        travel_hour=travel_hour,
    )

    routes = route_plan["routes"]
    start_pt = route_plan["origin_coords"]
    end_pt = route_plan["dest_coords"]

    # Build Enhanced Pro Map with multi-layer switcher and animated AntPath
    m = build_enhanced_route_map(
        routes=routes,
        origin_coords=start_pt,
        dest_coords=end_pt,
        origin_name=origin,
        dest_name=destination,
        travel_hour=travel_hour,
    )

    # Floating Info Card via Leaflet HTML element (Dark Theme)
    card_html = f"""
    <div style="
        position: fixed;
        bottom: 30px;
        left: 30px;
        width: 380px;
        background: rgba(26, 28, 36, 0.95);
        border: 1px solid #3A3F58;
        color: #F0F2F6;
        padding: 18px;
        border-radius: 14px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        z-index: 9999;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 13px;
        line-height: 1.4;
        backdrop-filter: blur(8px);
    ">
        <h3 style="margin: 0 0 4px 0; color: #BB86FC; font-size: 17px;">🛡️ MAHILA SURAKSHA MARG</h3>
        <p style="margin: 0 0 12px 0; color: #9CA3AF; font-size: 12px;"><b>{origin}</b> ➔ <b>{destination}</b> (Travel Hour: {travel_hour}:00)</p>
        
        <div style="background: #142E25; border-left: 4px solid #27AE60; padding: 8px 12px; margin-bottom: 8px; border-radius: 4px;">
            <b style="color: #A7F3D0;">Safest Route:</b> <span style="color:#27AE60; font-weight:bold;">{routes['Safest']['safety_score']}/100</span> ({routes['Safest']['distance_km']} km, ~{routes['Safest']['eta_mins']}m)<br>
            <small style="color: #D1D5DB;">{routes['Safest']['reasons'][0]}</small>
        </div>

        <div style="background: #251B2E; border-left: 4px solid #BB86FC; padding: 8px 12px; margin-bottom: 8px; border-radius: 4px;">
            <b style="color: #E9D5FF;">Balanced Route:</b> <span style="color:#BB86FC; font-weight:bold;">{routes['Balanced']['safety_score']}/100</span> ({routes['Balanced']['distance_km']} km)<br>
            <small style="color: #D1D5DB;">{routes['Balanced']['reasons'][0]}</small>
        </div>

        <div style="background: #2D2013; border-left: 4px solid #E67E22; padding: 8px 12px; margin-bottom: 10px; border-radius: 4px;">
            <b style="color: #FED7AA;">Fastest Route:</b> <span style="color:#E67E22; font-weight:bold;">{routes['Fastest']['safety_score']}/100</span> ({routes['Fastest']['distance_km']} km)<br>
            <small style="color: #D1D5DB;">{routes['Fastest']['reasons'][0]}</small>
        </div>

        <hr style="margin: 10px 0; border: none; border-top: 1px solid #3A3F58;">
        <div style="font-size: 11px; color: #9CA3AF;">
            ⚠️ <i>Safer does not mean safe. Supports, not replaces, 112.</i><br>
            Emergency: <b style="color: #FF6B6B;">112</b> | Women Helpline: <b style="color: #BB86FC;">1091 / 181</b>
        </div>
    </div>
    """

    m.get_root().html.add_child(folium.Element(card_html))

    m.save(str(OUTPUT_HTML))
    print(f"✅ Standalone showcase successfully exported to: {OUTPUT_HTML}")
    return OUTPUT_HTML


if __name__ == "__main__":
    generate_showcase_html()
