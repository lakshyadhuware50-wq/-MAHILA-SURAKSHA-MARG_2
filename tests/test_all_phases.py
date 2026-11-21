"""
tests/test_all_phases.py
========================
End-to-end integration and unit tests for MAHILA SURAKSHA MARG.

Tests:
- Scoring formula & worked example breakdown
- 3-Route engine generation (Fastest, Safest, Balanced)
- User feedback engine and adaptive penalty calculation
- NLP spam filter & Hinglish validation
- SOS alert construction and WhatsApp link formatting
- Database CRUD for route feedback
- ML risk model loading and SHAP attribution fallback
"""

from __future__ import annotations

import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import config as cfg
from core.db import add_route_feedback, get_engine, get_feedback_summary, get_route_feedbacks, init_db
from core.feedback_engine import get_feedback_edge_penalty_offset
from core.nlp_filter import check_rate_limit, classify_report_text
from core.risk_model import explain_prediction_shap, get_model_metrics, load_risk_model
from core.route_engine import plan_three_routes
from core.scoring import (
    calculate_route_safety_score,
    caution_level_from_score,
    compute_edge_safety_penalty,
    worked_example,
)
from core.sos import build_sos_message, get_whatsapp_share_url


# ---------------------------------------------------------------------------
# 1. Scoring & Formula Tests
# ---------------------------------------------------------------------------
def test_worked_example():
    ex = worked_example()
    assert "safety_score" in ex
    assert 5 <= ex["safety_score"] <= 98
    assert ex["caution_level"] in ("Low Caution", "Moderate Caution", "High Caution", "Extreme Caution")
    assert "breakdown" in ex
    assert ex["breakdown"]["total_penalty"] > 0


def test_edge_penalty_night_multiplier():
    p_day, _ = compute_edge_safety_penalty(length_m=500, hour=14)
    p_night, _ = compute_edge_safety_penalty(length_m=500, hour=23)
    assert p_night > p_day


def test_route_score_bounds():
    score, caution, reasons = calculate_route_safety_score([0.2, 0.3], [1000, 1000], hour=21, route_type="Safest")
    assert 5 <= score <= 98
    assert len(reasons) == 3


# ---------------------------------------------------------------------------
# 2. 3-Route Engine Tests
# ---------------------------------------------------------------------------
def test_plan_three_routes():
    res = plan_three_routes(
        origin_name="Connaught Place",
        destination_name="Saket",
        travel_hour=22,
    )
    assert "routes" in res
    routes = res["routes"]
    assert "Fastest" in routes
    assert "Safest" in routes
    assert "Balanced" in routes

    # Safest route should have higher or equal safety score compared to fastest
    assert routes["Safest"]["safety_score"] >= routes["Fastest"]["safety_score"]
    assert routes["Safest"]["distance_km"] > 0
    assert len(routes["Safest"]["coordinates"]) >= 2


# ---------------------------------------------------------------------------
# 3. User Feedback & Model Enhancement Tests
# ---------------------------------------------------------------------------
def test_user_feedback_db_and_offset(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "test_feedback.db")
    import core.db as db
    db._engine = None

    engine = get_engine()
    init_db(engine)

    # Add 2 positive route feedback submissions
    add_route_feedback(
        engine=engine,
        route_type="Safest",
        origin="Connaught Place",
        destination="Saket",
        rating=5,
        felt_safe=True,
        lighting_rating=5,
        police_patrol_seen=True,
    )
    add_route_feedback(
        engine=engine,
        route_type="Safest",
        origin="Connaught Place",
        destination="Saket",
        rating=4,
        felt_safe=True,
        lighting_rating=4,
        police_patrol_seen=True,
    )

    feedbacks = get_route_feedbacks(engine)
    assert len(feedbacks) == 2

    summary = get_feedback_summary(engine)
    assert summary["total_count"] == 2
    assert summary["safe_percentage"] == 100.0

    # Offset should reward the route with negative penalty offset (safer)
    offset, explanation = get_feedback_edge_penalty_offset("Connaught Place", "Saket")
    assert offset < 0.0
    assert "enhanced" in explanation.lower() or "reviews" in explanation.lower()


# ---------------------------------------------------------------------------
# 4. NLP Spam & Quality Filter Tests
# ---------------------------------------------------------------------------
def test_nlp_filter_valid_reports():
    valid, _, _ = classify_report_text("Street light is not functioning properly near the bus stop.")
    assert valid is True

    valid_hinglish, _, _ = classify_report_text("CP metro gate 2 ke paas police booth active hai.")
    assert valid_hinglish is True


def test_nlp_filter_spam_detection():
    valid, _, reason = classify_report_text("Buy cheap crypto bitcoin casino telegram link here")
    assert valid is False
    assert "spam" in reason.lower() or "indicator" in reason.lower()


def test_rate_limiting():
    session_id = "test_session_123"
    for _ in range(cfg.MAX_REPORTS_PER_SESSION_PER_HOUR):
        allowed, _ = check_rate_limit(session_id)
        assert allowed is True

    # Next attempt should be blocked
    blocked, msg = check_rate_limit(session_id)
    assert blocked is False
    assert "rate limit" in msg.lower()


# ---------------------------------------------------------------------------
# 5. SOS & Helplines Tests
# ---------------------------------------------------------------------------
def test_sos_message_format():
    msg = build_sos_message(28.6315, 77.2167, "Need urgent assistance")
    assert "28.63150,77.21670" in msg
    assert "112" in msg
    assert "EMERGENCY ALERT" in msg

    wa_url = get_whatsapp_share_url(msg)
    assert "api.whatsapp.com" in wa_url


# ---------------------------------------------------------------------------
# 6. ML Risk Model & SHAP Tests
# ---------------------------------------------------------------------------
def test_risk_model_and_shap():
    metrics = get_model_metrics()
    assert "accuracy" in metrics
    assert metrics["accuracy"] > 0.70

    shap_res = explain_prediction_shap({
        "hour_of_day": 23,
        "day_of_week": 5,
        "near_isolated_lane": 1,
        "near_low_lighting": 1,
        "dist_to_police_m": 2500.0,
        "dist_to_metro_m": 1200.0,
        "dist_to_hospital_m": 1400.0,
        "road_type": "service",
    })
    assert "attributions" in shap_res
    assert len(shap_res["attributions"]) > 0


# ---------------------------------------------------------------------------
# 7. Live Location & Telemetry Tests
# ---------------------------------------------------------------------------
def test_live_location_helpers():
    from core.live_location import get_live_tracking_links, reverse_geocode_coords

    # Test reverse geocoding Connaught Place coordinates
    addr = reverse_geocode_coords(28.6315, 77.2167)
    assert isinstance(addr, str)
    assert len(addr) > 3

    # Test live tracking links
    links = get_live_tracking_links(28.6315, 77.2167)
    assert "google_maps" in links
    assert "28.631500" in links["google_maps"]
    assert "osm" in links
    assert "openstreetmap.org" in links["osm"]

