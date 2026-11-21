"""
pages/5_Helplines.py
====================
Emergency Helplines Directory & Legal Quick-Guide.

Provides immediate one-tap calling access to verified Indian and Delhi
women's safety helplines along with procedural rights (Zero FIR, PCR response).
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

import config as cfg
from core.ui import disclaimer, page_header, sidebar_footer

st.set_page_config(page_title=f"Helplines — {cfg.APP_TITLE}", page_icon="☎️", layout="wide")

page_header("☎️ Emergency Helplines & Support Services", "Direct access to official emergency dispatchers, women's support desks, and legal rights.")
disclaimer()

# ---------------------------------------------------------------------------
# Section 1: Top Emergency Lines (One-Tap Dial)
# ---------------------------------------------------------------------------
st.subheader("🚨 Immediate Crisis Numbers (Tap to Call)")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
        <div style="border: 2px solid #E74C3C; border-radius: 12px; padding: 20px; background-color: #221415; color: #F0F2F6; text-align: center; box-shadow: 0 4px 14px rgba(0,0,0,0.4);">
            <h2 style="color: #FF6B6B; margin: 0; font-size: 32px;">112</h2>
            <p style="margin: 8px 0;"><b>National Emergency (ERSS)</b></p>
            <p style="font-size: 13px; color: #CBD5E1;">Integrated all-India emergency line for Police, Fire, and Ambulance. Operational 24/7 across Delhi-NCR with GPS PCR dispatch.</p>
            <a href="tel:112" style="text-decoration:none;">
                <div style="background-color: #C0392B; color: white; padding: 12px; border-radius: 8px; font-weight: bold; margin-top: 12px;">
                    📞 Dial 112 Now
                </div>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        """
        <div style="border: 2px solid #BB86FC; border-radius: 12px; padding: 20px; background-color: #20152B; color: #F0F2F6; text-align: center; box-shadow: 0 4px 14px rgba(0,0,0,0.4);">
            <h2 style="color: #DDA0DD; margin: 0; font-size: 32px;">1091</h2>
            <p style="margin: 8px 0;"><b>Delhi Police Women Helpline</b></p>
            <p style="font-size: 13px; color: #CBD5E1;">Dedicated Delhi Police women's safety desk. Responds immediately to stalking, harassment, domestic threat, and suspicious movement.</p>
            <a href="tel:1091" style="text-decoration:none;">
                <div style="background-color: #7B2D8E; color: white; padding: 12px; border-radius: 8px; font-weight: bold; margin-top: 12px;">
                    📞 Dial 1091 Now
                </div>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        """
        <div style="border: 2px solid #3498DB; border-radius: 12px; padding: 20px; background-color: #121F2B; color: #F0F2F6; text-align: center; box-shadow: 0 4px 14px rgba(0,0,0,0.4);">
            <h2 style="color: #5DADE2; margin: 0; font-size: 32px;">181</h2>
            <p style="margin: 8px 0;"><b>National Women's Helpline (DCW)</b></p>
            <p style="font-size: 13px; color: #CBD5E1;">Toll-free 24-hour telephonic helpline providing crisis intervention, counselling, shelter referrals, and legal aid connection.</p>
            <a href="tel:181" style="text-decoration:none;">
                <div style="background-color: #2980B9; color: white; padding: 12px; border-radius: 8px; font-weight: bold; margin-top: 12px;">
                    📞 Dial 181 Now
                </div>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Section 2: Specialized & Mental Health Helplines
# ---------------------------------------------------------------------------
st.subheader("🛡️ Specialized & Transit Support Lines")

extra_col1, extra_col2, extra_col3 = st.columns(3)

with extra_col1:
    st.markdown(
        """
        **🚇 Delhi Metro Security (DMRC)**
        - **Helpline:** `155370` / `155655`
        - **DMRC CISF Control:** `011-23417910`
        - *Use when travelling on DMRC trains or stations for immediate CISF physical response at next platform.*
        """
    )

with extra_col2:
    st.markdown(
        """
        **⚖️ Delhi Commission for Women (DCW)**
        - **Mobile Helpline:** `011-23379181`
        - **Rape Crisis Cell:** `011-23378044`
        - *Assistance with court representation, immediate medical examination support, and FIR follow-ups.*
        """
    )

with extra_col3:
    st.markdown(
        """
        **🧠 Mental Health & Crisis Counselling**
        - **KIRAN Helpline:** `1800-599-0019`
        - **Vandrevala Foundation:** `9999 666 555`
        - *24/7 confidential psychological first-aid and trauma counselling.*
        """
    )

st.divider()

# ---------------------------------------------------------------------------
# Section 3: Legal Rights & Rapid Emergency Protocol
# ---------------------------------------------------------------------------
with st.expander("📖 Know Your Rights: What to Say When Calling 112 & Zero-FIR Guide"):
    st.markdown(
        """
        ### What to say when you call 112:
        1. **Location First:** State your exact landmark immediately (e.g., *"Outer Circle CP, near Metro Gate 4"*). If call drops, they dispatch to your last spoken landmark.
        2. **Nature of Threat:** State whether someone is following you, threatening physical harm, or blocking your way.
        3. **Vehicle Details:** If in a cab or auto, read out the vehicle license plate number aloud immediately.

        ### Key Legal Protections in India:
        - **Zero FIR Right:** Under Indian criminal law (Section 173 BNSS / 154 CrPC), any police station is legally mandated to register an FIR for crimes against women, **regardless of jurisdiction**, and transfer it afterwards.
        - **Right to Female Officer:** Statements regarding offences against women must be recorded by a woman police officer.
        - **Prohibition of Night Arrest:** Women cannot be arrested after sunset and before sunrise except under exceptional circumstances with prior judicial magistrate sanction.
        """
    )

sidebar_footer()
