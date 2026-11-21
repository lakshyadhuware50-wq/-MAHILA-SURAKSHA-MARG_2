"""
app.py
======
Home page of MAHILA SURAKSHA MARG.

Run it with:
    streamlit run app.py

This file is intentionally light: it only imports Streamlit + config, so
the app starts in ~2 seconds even before the OSM graph is downloaded.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Guarantee project root is in sys.path
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

import config as cfg
from core.db import init_db
from core.ui import disclaimer, inject_pwa_meta, sidebar_footer, synthetic_notice

# Ensure SQLite schema is initialized on first start
try:
    init_db()
except Exception:
    pass

st.set_page_config(
    page_title=cfg.APP_TITLE,
    page_icon=cfg.APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------
# Demo-mode banner (shown on EVERY page when DEMO_MODE=True)
# ---------------------------------------------------------------------
if cfg.DEMO_MODE:
    st.error(cfg.DEMO_BANNER, icon="⚠️")

inject_pwa_meta()

# ---------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------
st.title(cfg.APP_ICON + " " + cfg.APP_TITLE)
st.subheader(cfg.APP_SUBTITLE)
st.caption("Pilot zone: " + cfg.AREA_LABEL)

disclaimer()

st.markdown(
    """
**What this app does**

1. You enter a **start point**, a **destination** and the **time** you plan to travel.
2. It computes **three routes**: the Fastest, the Safest and a Balanced mix.
3. Each route gets a **0-100 safety score** plus **three plain-English reasons**,
   for example *"well lit main road"* or *"passes an isolated stretch after 10 PM"*.
4. Extra tools: **SOS**, fake call screen, nearby safe spots, helplines and
   community reports.

**What this app does not do**

- It does not guarantee safety. No route is ever 100% safe.
- It does not replace **112** or official police services.
- It does not use real crime data. See the note below.
"""
)

synthetic_notice()

# ---------------------------------------------------------------------
# Build status: shows which phase files already exist on disk
# ---------------------------------------------------------------------
st.divider()
st.header("Project build status")

checks = [
    ("Road graph (OSM, pilot area)", cfg.GRAPH_PATH, "Phase 2"),
    ("OSM safety features (lit, police, metro...)", cfg.OSM_FEATURES_PATH, "Phase 2"),
    ("Safe spots layer (police/hospital/pharmacy/metro)", cfg.SAFE_SPOTS_PATH, "Phase 2"),
    ("Synthetic training data", cfg.SYNTHETIC_DATA_PATH, "Phase 2"),
    ("SQLite database", cfg.DB_PATH, "Phase 2"),
    ("Trained risk model", cfg.RISK_MODEL_PATH, "Phase 5"),
]

rows = ["| Item | Phase | Status |", "|---|---|---|"]
for label, path, phase in checks:
    status = "\u2705 ready" if path.exists() else "\u23f3 not built yet"
    rows.append(f"| {label} | {phase} | {status} |")
st.markdown("\n".join(rows))

if not cfg.twilio_is_configured():
    st.caption(
        "SMS alerts: **not configured** (no Twilio keys in `.env`). "
        "Everything still works - the SOS page will show a copy-paste message."
    )
else:
    st.caption("SMS alerts: **Twilio configured**. Real SMS will be sent on SOS.")

# ---------------------------------------------------------------------
# How to use / where to start
# ---------------------------------------------------------------------
st.divider()
left, right = st.columns(2)

with left:
    st.header("Start here")
    st.markdown(
        """
        1. Open **Plan My Route** in the sidebar.
        2. Type a start and destination (for example *Connaught Place* to *Saket*).
        3. Pick your travel time, then compare the three routes.
        4. Before travelling, save a trusted contact on the **SOS** page.

        First time running the project? Follow `README.md` step by step.
        """
    )

with right:
    st.header("Pages in this app")
    st.markdown(
        """
        - **Plan My Route** - 3 routes, safety scores & 🛰️ real-time GPS departure point
        - **SOS** - trusted contacts + 🛰️ live device GPS telemetry + Google Maps pin + 112 button
        - **Fake Call** - simulated incoming call with custom scripts
        - **Safe Spots** - police, hospitals, pharmacies, metro + 🛰️ live distance & nearest safe spot hero
        - **Helplines** - 112 / 1091 / 181 with tap-to-call & rights guide
        - **Trip Sharing** - shareable live journey tracking link + 🛰️ real-time traveller beacon map
        - **Community Reports** - anonymous reports + Hinglish NLP spam filter & time decay
        - **Model Insights** - metrics, SHAP explainability & user-feedback model retraining
        """
    )

st.divider()
with st.expander("📱 Android APK & Mobile App Installation", expanded=False):
    st.markdown(
        """
        ### Install on Android Phone

        **Option 1: Native Android APK**
        - A native Android Studio project is included in [`android_app/`](./android_app/README_APK.md).
        - Open it in Android Studio and select **Build > Build APK(s)** to generate `app-debug.apk`.
        - The project includes native emergency dialer integration (`tel:112`), fine-grained GPS permissions, dark theme system bars, and offline handling.

        **Option 2: Direct Wi-Fi Phone Access (No APK build needed)**
        - Connect your Android phone to the same Wi-Fi network as this PC.
        - Open Chrome on your phone and browse to:  
          `http://10.206.24.45:8501`
        - Tap the **3-dot menu (⋮)** in Chrome and tap **Add to Home Screen** to install it as an app icon.
        """
    )

st.caption(
    "Privacy: no account, no name, no phone number is required to use route "
    "planning. Personal data (trusted contacts) is stored only on this computer, "
    "only if you choose to save it, and can be deleted from the SOS page."
)

sidebar_footer()
