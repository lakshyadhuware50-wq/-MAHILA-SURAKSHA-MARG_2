"""
core/sos.py
===========
Emergency SOS toolkit for MAHILA SURAKSHA MARG.

Features:
- Formats emergency broadcast messages with live GPS / Google Maps pin.
- Optional Twilio SMS dispatch (if credentials exist in .env).
- WhatsApp one-tap broadcast link.
- One-tap 112 calling protocol.
- Consent-based privacy management.
"""

from __future__ import annotations

import logging
import urllib.parse
from typing import Optional

import config as cfg
from core.db import get_contacts, get_engine

log = logging.getLogger(__name__)


def build_sos_message(
    lat: float,
    lon: float,
    note: Optional[str] = None,
) -> str:
    """Construct standardised SOS alert message with map link."""
    gmaps_url = f"https://www.google.com/maps?q={lat:.5f},{lon:.5f}"
    base = (
        f"🚨 EMERGENCY ALERT (MAHILA SURAKSHA MARG) 🚨\n"
        f"I require immediate assistance. My current location is:\n{gmaps_url}\n"
    )
    if note and note.strip():
        base += f"Status note: {note.strip()}\n"
    base += "If you cannot reach me, please alert Police Emergency at 112."
    return base


def get_whatsapp_share_url(message: str) -> str:
    """Generate universal WhatsApp pre-filled message URL."""
    encoded = urllib.parse.quote(message)
    return f"https://api.whatsapp.com/send?text={encoded}"


def send_sos_sms(
    message: str,
    recipient_phone: Optional[str] = None,
) -> tuple[bool, str]:
    """
    Send SMS alert via Twilio if configured.
    Returns (success_boolean, status_message).
    """
    if cfg.DEMO_MODE:
        return False, "DEMO_MODE is Active: Real SMS dispatch suppressed for simulation safety."

    if not cfg.twilio_is_configured():
        return False, "Twilio credentials not found in .env. Use WhatsApp or direct SMS copy fallback."

    try:
        from twilio.rest import Client

        client = Client(cfg.TWILIO_ACCOUNT_SID, cfg.TWILIO_AUTH_TOKEN)
        target = recipient_phone or cfg.TWILIO_TO_NUMBER
        if not target:
            return False, "No recipient phone number specified."

        msg = client.messages.create(
            body=message,
            from_=cfg.TWILIO_FROM_NUMBER,
            to=target,
        )
        log.info("Twilio SMS dispatched SID=%s to %s", msg.sid, target)
        return True, f"SMS successfully sent to {target} (SID: {msg.sid[:8]}...)"
    except Exception as exc:
        log.warning("Twilio SMS dispatch failed: %s", exc)
        return False, f"Twilio SMS error: {str(exc)}"


def dispatch_emergency_broadcast(
    lat: float,
    lon: float,
    note: Optional[str] = None,
) -> dict:
    """Broadcast to all consent-stored trusted contacts."""
    engine = get_engine()
    contacts = get_contacts(engine)
    message = build_sos_message(lat, lon, note)
    whatsapp_url = get_whatsapp_share_url(message)

    results = []
    for c in contacts:
        success, status = send_sos_sms(message, recipient_phone=c.phone)
        results.append({
            "contact_name": c.name,
            "phone": c.phone,
            "success": success,
            "status": status,
        })

    return {
        "message": message,
        "whatsapp_url": whatsapp_url,
        "results": results,
        "contacts_count": len(contacts),
        "lat": lat,
        "lon": lon,
    }
