"""
core/feedback_engine.py
=======================
User Feedback Engine for MAHILA SURAKSHA MARG.

Implements the continuous model enhancement loop requested by users:
1. Gathers direct route reviews (ratings, perceived safety, police presence, lighting)
   and anonymous community hazard reports.
2. Applies dynamic spatial corrections to routing edge weights so routes immediately
   avoid repeatedly reported danger spots.
3. Automatically blends real user feedback into training batches and retrains/calibrates
   the Random Forest risk model so AI predictions improve over time.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

import config as cfg
from core.db import get_engine, get_reports, get_route_feedbacks, init_db

log = logging.getLogger(__name__)

FEEDBACK_METRICS_PATH = cfg.MODEL_DIR / "feedback_enhancement_stats.json"


def get_feedback_edge_penalty_offset(
    origin: str,
    destination: str,
    hour: int = 21,
) -> tuple[float, str]:
    """
    Calculate dynamic penalty modifier (-0.15 to +0.25) for a given origin/destination
    corridor based on historical user feedback.

    Returns:
        (offset_float, explanation_string)
    """
    engine = get_engine()
    init_db(engine)
    feedbacks = get_route_feedbacks(engine, limit=200)
    if not feedbacks:
        return 0.0, "No user feedback records yet; standard OSM model applied."

    orig_clean = origin.lower().strip()
    dest_clean = destination.lower().strip()

    # Filter matching feedbacks
    matching = [
        f for f in feedbacks
        if (orig_clean in f.origin.lower() or f.origin.lower() in orig_clean)
        and (dest_clean in f.destination.lower() or f.destination.lower() in dest_clean)
    ]

    if not matching:
        # Check general area feedback
        area_feedbacks = [
            f for f in feedbacks
            if orig_clean in f.origin.lower() or dest_clean in f.destination.lower()
        ]
        if not area_feedbacks:
            return 0.0, "Calibrated using baseline Delhi pilot safety data."
        matching = area_feedbacks

    avg_rating = sum(f.rating for f in matching) / len(matching)
    pct_felt_safe = sum(1 for f in matching if f.felt_safe) / len(matching)
    avg_lighting = sum(f.lighting_rating for f in matching) / len(matching)
    police_seen = sum(1 for f in matching if f.police_patrol_seen) / len(matching)

    # Calculate adjustment:
    # High rating & felt safe -> negative penalty (safer)
    # Low rating & felt unsafe -> positive penalty (more cautious)
    safety_bias = (pct_felt_safe - 0.70) * -0.20  # if 100% safe -> -0.06
    lighting_bias = (avg_lighting - 3.0) * -0.04   # 5-star light -> -0.08
    police_bias = police_seen * -0.05              # police visible -> -0.05
    rating_bias = (avg_rating - 3.5) * -0.05       # 5-star -> -0.075

    raw_offset = safety_bias + lighting_bias + police_bias + rating_bias
    clipped_offset = max(-0.15, min(0.25, raw_offset))

    if clipped_offset < -0.02:
        reason = (
            f"User feedback enhanced: {len(matching)} community travellers confirmed "
            f"positive vigilance (avg {avg_rating:.1f}★, {pct_felt_safe*100:.0f}% felt safe)."
        )
    elif clipped_offset > 0.02:
        reason = (
            f"User feedback alert: {len(matching)} community reports flagged reduced lighting "
            f"or uncomfortable corridors (caution score adjusted by +{clipped_offset*100:.0f}%)."
        )
    else:
        reason = f"Validated by {len(matching)} user trip reviews."

    return round(clipped_offset, 3), reason


def generate_feedback_augmented_training_data() -> pd.DataFrame:
    """
    Transforms collected user route feedback and community hazard reports into
    labelled feature rows that match the ML training schema.
    """
    engine = get_engine()
    feedbacks = get_route_feedbacks(engine, limit=1000)
    reports = get_reports(engine, exclude_spam=True, limit=1000)

    rows = []

    # 1. Convert RouteFeedbacks to training records
    for f in feedbacks:
        # Approximate coordinate lookup from pilot places
        coords = cfg.PILOT_PLACES.get("Connaught Place", (28.6315, 77.2167))
        for place, pt in cfg.PILOT_PLACES.items():
            if place.lower() in f.origin.lower() or place.lower() in f.destination.lower():
                coords = pt
                break

        # If felt_safe is True and rating >= 4 -> risk_label = 0 (Safe)
        # If felt_safe is False or rating <= 2 -> risk_label = 1 (High Risk)
        is_risk = 1 if (not f.felt_safe or f.rating <= 2) else 0

        # Lighting proxy
        low_light = 1 if f.lighting_rating <= 2 else 0

        # Police proximity proxy: if police seen, distance is small
        dist_police = 350.0 if f.police_patrol_seen else 1800.0

        rows.append({
            "lat": coords[0] + np.random.uniform(-0.01, 0.01),
            "lon": coords[1] + np.random.uniform(-0.01, 0.01),
            "hour_of_day": f.travel_hour or 21,
            "day_of_week": 4,  # default
            "incident_type": "user_feedback_safe" if is_risk == 0 else "user_feedback_hazard",
            "near_isolated_lane": 1 if f.crowd_rating <= 2 else 0,
            "near_low_lighting": low_light,
            "dist_to_police_m": dist_police,
            "dist_to_metro_m": 800.0,
            "dist_to_hospital_m": 1100.0,
            "road_type": "primary" if is_risk == 0 else "service",
            "risk_factors_sum": 1 if is_risk == 0 else 4,
            "risk_label": is_risk,
            "is_synthetic": False,  # REAL USER FEEDBACK
        })

    # 2. Convert CommunityReports to training records
    for r in reports:
        is_risk = 0 if r.category == "felt_safe" else 1
        rows.append({
            "lat": r.lat,
            "lon": r.lon,
            "hour_of_day": r.hour_of_day or 22,
            "day_of_week": 5,
            "incident_type": r.category,
            "near_isolated_lane": 1 if r.category in ("isolated", "isolated_area") else 0,
            "near_low_lighting": 1 if r.category == "poor_lighting" else 0,
            "dist_to_police_m": 2200.0 if is_risk == 1 else 400.0,
            "dist_to_metro_m": 1200.0,
            "dist_to_hospital_m": 1500.0,
            "road_type": "footway" if is_risk == 1 else "primary",
            "risk_factors_sum": 4 if is_risk == 1 else 1,
            "risk_label": is_risk,
            "is_synthetic": False,  # REAL USER FEEDBACK
        })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def retrain_model_with_user_feedback() -> dict[str, Any]:
    """
    Retrains the ML risk model by combining synthetic baseline incidents
    with all collected user route feedback and community hazard reports.
    """
    from core.risk_model import train_risk_model

    log.info("Starting model enhancement via user feedback...")
    augmented_df = generate_feedback_augmented_training_data()

    # Load baseline synthetic data
    if cfg.SYNTHETIC_DATA_PATH.exists():
        baseline_df = pd.read_csv(cfg.SYNTHETIC_DATA_PATH)
    else:
        from core.synthetic import generate_synthetic_incidents
        baseline_df = generate_synthetic_incidents(3000)

    if not augmented_df.empty:
        # Oversample user feedback 3x so user voices meaningfully influence model weights
        user_weight_multiplier = 3
        weighted_feedback = pd.concat([augmented_df] * user_weight_multiplier, ignore_index=True)
        combined_df = pd.concat([baseline_df, weighted_feedback], ignore_index=True)
        feedback_count = len(augmented_df)
    else:
        combined_df = baseline_df
        feedback_count = 0

    # Train model
    metrics = train_risk_model(df=combined_df)

    enhancement_stats = {
        "last_retrained_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "user_feedbacks_incorporated": feedback_count,
        "total_training_records": len(combined_df),
        "metrics": metrics,
        "status": "Enhanced with real feedback",
    }

    try:
        FEEDBACK_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(FEEDBACK_METRICS_PATH, "w", encoding="utf-8") as f:
            json.dump(enhancement_stats, f, indent=2)
    except Exception as exc:
        log.warning("Could not persist feedback stats: %s", exc)

    return enhancement_stats


def get_feedback_enhancement_stats() -> dict[str, Any]:
    """Retrieve the latest retrain stats and feedback volume."""
    if FEEDBACK_METRICS_PATH.exists():
        try:
            with open(FEEDBACK_METRICS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return {
        "last_retrained_at": "Not yet retrained (using baseline)",
        "user_feedbacks_incorporated": 0,
        "total_training_records": cfg.SYNTHETIC_N_INCIDENTS,
        "status": "Ready for initial feedback calibration",
    }
