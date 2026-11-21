"""
core/ui.py
==========
Small shared Streamlit helpers so every page looks the same and the
responsible-design text is NEVER forgotten.

Nothing here imports osmnx / sklearn, so pages open instantly.
"""

from __future__ import annotations

import streamlit as st

import config as cfg


def inject_pwa_meta() -> None:
    """Inject PWA meta tags & manifest link for PWABuilder and mobile browsers."""
    pwa_html = """
    <link rel="manifest" href="/app/static/manifest.json">
    <meta name="theme-color" content="#0E1117">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Mahila Suraksha">
    <link rel="apple-touch-icon" href="/app/static/icon-192.png">
    """
    st.markdown(pwa_html, unsafe_allow_html=True)


def page_header(title: str, subtitle: str | None = None) -> None:
    """Consistent page title + optional one-line subtitle."""
    inject_pwa_meta()
    # Show demo banner on every page if DEMO_MODE is on
    if cfg.DEMO_MODE:
        st.error(cfg.DEMO_BANNER, icon="⚠️")
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def disclaimer() -> None:
    """The mandatory note: call this on every page that shows results."""
    st.warning(cfg.DISCLAIMER, icon="⚠️")


def synthetic_notice() -> None:
    """Honest label for anything driven by the synthetic training data."""
    st.info(cfg.SYNTHETIC_DATA_NOTICE, icon="🧪")


def sidebar_footer() -> None:
    """Project info shown in the sidebar on every page."""
    with st.sidebar:
        st.divider()
        st.caption("**Pilot area:** " + cfg.AREA_LABEL)
        st.caption(cfg.DISCLAIMER)
        st.caption("Emergency: **112** | Women helpline: **1091 / 181**")
        if cfg.DEMO_MODE:
            st.caption("🔬 Demo / prototype mode")


