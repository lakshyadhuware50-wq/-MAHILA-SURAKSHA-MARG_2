"""
pages/3_Fake_Call.py
====================
Simulated Incoming Call Screen.

Designed to assist women in uncomfortable or intimidating environments
(e.g. suspicious cab driver, uncomfortable auto rickshaw, or stalkers)
by generating a realistic incoming phone call screen and dialogue script.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import time

import numpy as np
import streamlit as st

import config as cfg
from core.ui import disclaimer, page_header, sidebar_footer

st.set_page_config(page_title=f"Fake Call — {cfg.APP_TITLE}", page_icon="📞", layout="centered")

page_header("📞 Disarming Fake Call", "Simulate an urgent incoming call to safely exit uncomfortable situations.")
disclaimer()

# State management
if "call_state" not in st.session_state:
    st.session_state.call_state = "idle"  # idle | ringing | connected

st.write(
    "Set up a believable incoming call. When answered, the screen displays a plausible "
    "conversation script so you can speak aloud and deter unsolicited attention."
)

col1, col2 = st.columns(2)
with col1:
    caller_name = st.text_input("Caller Name / Title", value="Inspector Rajesh Sharma (Delhi Police)")
    caller_subtitle = st.text_input("Subtitle / Relationship", value="Mobile • Incoming")

with col2:
    delay_sec = st.selectbox(
        "Call Trigger Delay",
        options=[0, 5, 15, 30],
        format_func=lambda x: "Instant" if x == 0 else f"In {x} seconds",
        index=0,
    )
    script_type = st.selectbox(
        "Conversation Persona / Script",
        options=["Police / Security Relative", "Father / Brother Waiting Outside", "Cab / Ride Dispatcher"],
    )

with col2:
    ringtone = st.segmented_control(
        "Ringtone",
        options=["Classic", "Modern", "Gentle", "Custom"],
        default="Classic",
        key="fake_call_ringtone",
    )
    ringtone_volume = st.slider("Ringtone Volume", 0, 100, 70, 5)

custom_ringtone = None
if ringtone == "Custom":
    def save_custom_ringtone():
        uploaded = st.session_state.get("fake_call_custom_file")
        if uploaded is None:
            st.session_state.pop("fake_call_custom_bytes", None)
            st.session_state.pop("fake_call_custom_format", None)
            st.session_state.pop("fake_call_custom_name", None)
            return
        st.session_state.fake_call_custom_bytes = uploaded.getvalue()
        st.session_state.fake_call_custom_format = uploaded.type or "audio/mpeg"
        st.session_state.fake_call_custom_name = uploaded.name

    st.file_uploader(
        "Upload Custom Ringtone",
        type=["wav", "mp3", "ogg", "m4a", "aac"],
        key="fake_call_custom_file",
        on_change=save_custom_ringtone,
        help="The uploaded file stays in this browser session and is not sent to a server.",
        width="stretch",
    )
    custom_ringtone = st.session_state.get("fake_call_custom_name")
    if custom_ringtone:
        st.caption(f"Using: {custom_ringtone}")

if st.session_state.call_state == "idle":
    if st.button("📲 TRIGGER FAKE CALL", type="primary", width="stretch"):
        if delay_sec > 0:
            with st.spinner(f"Call will ring in {delay_sec} seconds... Pocket your phone or hold naturally."):
                time.sleep(delay_sec)
        st.session_state.call_state = "ringing"
        st.rerun()

# ---------------------------------------------------------------------------
# Ringing Screen
# ---------------------------------------------------------------------------
if st.session_state.call_state == "ringing":
    custom_bytes = st.session_state.get("fake_call_custom_bytes")
    if ringtone == "Custom" and custom_bytes:
        st.audio(
            custom_bytes,
            format=st.session_state.get("fake_call_custom_format", "audio/mpeg"),
            autoplay=True,
            loop=True,
            alt="Custom fake incoming-call ringtone",
            width="stretch",
        )
    elif ringtone == "Custom":
        st.warning("Upload a custom ringtone first. Playing the Classic ringtone instead.", title="Custom ringtone missing")

    sample_rate = 44100
    cycle_duration = 4.0
    t = np.linspace(0, cycle_duration, int(sample_rate * cycle_duration), endpoint=False)

    if ringtone == "Modern":
        frequencies = (880.0, 1108.73)
    elif ringtone == "Gentle":
        frequencies = (523.25, 659.25)
    else:
        frequencies = (480.0, 620.0)

    samples = np.zeros_like(t)
    for start, end in ((0.0, 0.25), (0.35, 0.60), (0.70, 0.95), (1.05, 1.30)):
        mask = (t >= start) & (t < end)
        segment_t = t[mask] - start
        tone = (np.sin(2 * np.pi * frequencies[0] * segment_t)
                + np.sin(2 * np.pi * frequencies[1] * segment_t)) * 0.25
        samples[mask] = tone

    samples *= ringtone_volume / 100.0
    if not (ringtone == "Custom" and custom_bytes):
        st.audio(
            samples,
            sample_rate=sample_rate,
            format="audio/wav",
            autoplay=True,
            loop=True,
            alt="Looping fake incoming-call ringtone",
            width="stretch",
        )

    st.markdown(
        f"""
        <div style="background-color: #121212; color: white; border-radius: 20px; padding: 40px 20px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
            <div style="font-size: 14px; color: #888; text-transform: uppercase; letter-spacing: 2px;">Incoming Call...</div>
            <div style="font-size: 28px; font-weight: bold; margin: 15px 0 5px 0; color: #FFF;">{caller_name}</div>
            <div style="font-size: 15px; color: #AAA;">{caller_subtitle}</div>
            <div style="font-size: 50px; margin: 25px 0;">🔔</div>
            <div style="color: #4CAF50; font-size: 14px; animation: blinker 1s linear infinite;">● Ringing...</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    r_col1, r_col2 = st.columns(2)
    with r_col1:
        if st.button("❌ Decline", width="stretch"):
            st.session_state.call_state = "idle"
            st.rerun()
    with r_col2:
        if st.button("📞 Accept Call", type="primary", width="stretch"):
            st.session_state.call_state = "connected"
            st.rerun()

# ---------------------------------------------------------------------------
# Connected Call Screen & Script
# ---------------------------------------------------------------------------
elif st.session_state.call_state == "connected":
    st.markdown(
        f"""
        <div style="background-color: #1E272C; color: white; border-radius: 20px; padding: 30px 20px; text-align: center;">
            <div style="font-size: 14px; color: #4CAF50;">● Connected (00:14)</div>
            <div style="font-size: 26px; font-weight: bold; margin: 10px 0; color: #FFF;">{caller_name}</div>
            <div style="font-size: 14px; color: #DDD;">Speaker On • Mute • Keypad</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("🗣️ Speak These Lines Naturally:")
    if script_type == "Police / Security Relative":
        st.info(
            """
            **Read aloud clearly:**
            1. *"Haan uncle, main bilkul theek hoon. Aap Outer Ring Road chowki pe khade ho?"*
            2. *"Haan main auto/cab mein hoon, live GPS location share kar di hai maine WhatsApp pe."*
            3. *"Bas do minute mein pahunch rahi hoon, aap PCR van ke paas hi rukna."*
            """
        )
    elif script_type == "Father / Brother Waiting Outside":
        st.info(
            """
            **Read aloud clearly:**
            1. *"Haan Papa, main 5 minute mein gate ke samne utar rahi hoon."*
            2. *"Aap aur Bhaiya dono bahar road pe hi wait karna, car ki headlight on rakhna."*
            3. *"Driver bhaiya, aage se left lijiye, mere papa samne hi khade hain."*
            """
        )
    else:
        st.info(
            """
            **Read aloud clearly:**
            1. *"Hello, haan company control room? Cab route monitor ho raha hai?"*
            2. *"Haan main ride tracking link check kar sakti hoon, alert button working hai."*
            """
        )

    if st.button("🔴 End Call", type="secondary", width="stretch"):
        st.session_state.call_state = "idle"
        st.rerun()

sidebar_footer()
