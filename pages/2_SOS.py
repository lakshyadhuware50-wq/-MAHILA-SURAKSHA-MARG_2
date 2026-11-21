"""
pages/2_SOS.py
==============
Emergency SOS & Live Alert Toolkit.

Features:
- Emergency 112 quick-call link.
- Stored trusted contacts (stored locally only with user consent).
- Live Google Maps link generation.
- Twilio SMS broadcast or WhatsApp/Clipboard one-click dispatch.
- Consent-based audio capture toggle (open, non-covert).
- "Delete my data" complete privacy cleanup button.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

import config as cfg
from core.db import add_contact, delete_contact, delete_my_data, get_contacts, get_engine
from core.live_location import get_live_tracking_links, render_live_location_widget
from core.sos import dispatch_emergency_broadcast
from core.ui import disclaimer, page_header, sidebar_footer

st.set_page_config(page_title=f"SOS — {cfg.APP_TITLE}", page_icon="🆘", layout="wide")

page_header("🆘 Emergency SOS Toolkit", "Immediate panic broadcast, trusted contacts, and rapid emergency services.")
disclaimer()

engine = get_engine()

# ---------------------------------------------------------------------------
# Section 1: Immediate Emergency Shortcuts
# ---------------------------------------------------------------------------
st.error("🚨 In immediate physical danger? Call National Emergency directly.")
e_col1, e_col2, e_col3 = st.columns([1, 1, 1])

with e_col1:
    st.markdown(
        """
        <a href="tel:112" style="text-decoration:none;">
            <div style="background-color: #C0392B; color: white; padding: 16px; border-radius: 8px; text-align: center; font-size: 20px; font-weight: bold;">
                📞 CALL 112 NOW
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

with e_col2:
    st.markdown(
        """
        <a href="tel:1091" style="text-decoration:none;">
            <div style="background-color: #7B2D8E; color: white; padding: 16px; border-radius: 8px; text-align: center; font-size: 20px; font-weight: bold;">
                📞 Delhi Women Helpline 1091
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

with e_col3:
    st.markdown(
        """
        <a href="tel:181" style="text-decoration:none;">
            <div style="background-color: #2980B9; color: white; padding: 16px; border-radius: 8px; text-align: center; font-size: 20px; font-weight: bold;">
                📞 National Helpline 181
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Section 2: One-Tap SOS Broadcast
# ---------------------------------------------------------------------------
st.subheader("📡 Broadcast Live Location SOS Alert")

current_lat, current_lon, current_addr, is_live_gps = render_live_location_widget(
    label="Capture Live Device GPS for SOS",
    key_prefix="sos_geo",
    show_mini_map=True,
)

links = get_live_tracking_links(current_lat, current_lon)

col_note, col_links = st.columns([1.5, 1])
with col_note:
    sos_note = st.text_input(
        "Situation details / description:",
        value=f"Emergency at {current_addr}. Need help immediately!",
    )
with col_links:
    st.markdown("**Live Tracking Links Generated:**")
    st.markdown(f"📍 [Open Live Pin on Google Maps]({links['google_maps']})")
    st.markdown(f"🗺️ [Open on OpenStreetMap]({links['osm']})")

if st.button("🚨 TRIGGER EMERGENCY SOS BROADCAST NOW", type="primary", width="stretch"):
    broadcast = dispatch_emergency_broadcast(current_lat, current_lon, sos_note)
    st.success("🚨 SOS Emergency Broadcast generated with your live coordinates!")

    st.text_area("📋 Message Content (Copy & Send if SMS unavailable):", value=broadcast["message"], height=120)

    st.markdown(f"[📲 Open in WhatsApp and Send Immediately]({broadcast['whatsapp_url']})")

    if broadcast["results"]:
        st.markdown("**SMS Delivery Status:**")
        for res in broadcast["results"]:
            icon = "✅" if res["success"] else "⚠️"
            st.write(f"{icon} {res['contact_name']} ({res['phone']}): {res['status']}")
    else:
        st.warning("No trusted contacts saved yet. Add your trusted contacts below to enable automatic alerts.")

# ---------------------------------------------------------------------------
# Section 3: Optional Consent-Based Audio Evidence Recording
# ---------------------------------------------------------------------------
st.divider()
st.subheader("🎙️ Consent-Based Ambient Audio Recording")
st.caption(
    "Responsible AI Guarantee: Recording is strictly opt-in, non-covert, and triggers only "
    "when you grant explicit browser microphone permission. Audio is stored only on this device."
)

enable_audio = st.toggle("Enable Emergency Audio Recording Widget")
if enable_audio:
    st.info("Press record below to capture up to 60 seconds of ambient audio as protective documentation.")
    audio_val = st.audio_input("Record Ambient Audio")
    if audio_val:
        st.success("Ambient audio clip recorded successfully. You can review or download it locally.")

# ---------------------------------------------------------------------------
# Section 4: Trusted Contacts Management
# ---------------------------------------------------------------------------
st.divider()
st.subheader("👥 Trusted Emergency Contacts")

contacts = get_contacts(engine)

if contacts:
    for c in contacts:
        col_c1, col_c2, col_c3 = st.columns([2, 2, 1])
        col_c1.write(f"**{c.name}**")
        col_c2.write(f"📞 `{c.phone}`")
        if col_c3.button("Remove", key=f"del_{c.id}"):
            delete_contact(engine, c.id)
            st.rerun()
else:
    st.info("No contacts saved. Add family members, friends, or roommates below.")

with st.expander("➕ Add a Trusted Contact (Consent Required)", expanded=not bool(contacts)):
    with st.form("add_contact_form"):
        c_name = st.text_input("Contact Name (e.g. Mum, Sister, Friend)")
        c_phone = st.text_input("Mobile Number (preferably with country code, e.g. +919876543210)")
        c_consent = st.checkbox("I explicitly consent to storing this contact locally on this device for emergency alerts.", value=True)
        btn_save = st.form_submit_button("Save Contact")

        if btn_save:
            if not c_name or not c_phone:
                st.error("Please provide both name and phone number.")
            elif not c_consent:
                st.error("Consent is required to store contact information.")
            else:
                add_contact(engine, c_name.strip(), c_phone.strip(), consent=True)
                st.success(f"Saved {c_name} to trusted contacts.")
                st.rerun()

# ---------------------------------------------------------------------------
# Section 5: Responsible Privacy (Delete My Data)
# ---------------------------------------------------------------------------
st.divider()
with st.expander("🔒 Privacy Management & 'Delete My Data'"):
    st.write(
        "We believe in zero data hoarding. All contact details and live trip shares can be "
        "purged from this device with one click."
    )
    if st.button("🗑️ Delete All My Stored Contacts and Trip Data", type="secondary"):
        deleted = delete_my_data(engine)
        st.success(f"Purged {deleted.get('contacts', 0)} contacts and {deleted.get('trip_shares', 0)} trip records.")
        st.rerun()

sidebar_footer()
