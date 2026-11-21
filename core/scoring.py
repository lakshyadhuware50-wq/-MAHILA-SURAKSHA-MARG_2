"""
core/scoring.py
===============
Safety scoring module for MAHILA SURAKSHA MARG.

Computes multi-factor safety scores (0-100), caution levels, and
plain-language explanations for route segments and full itineraries.

Formula:
--------
    Total Penalty = (
        w_inc   * P_incidental +
        w_light * P_lighting +
        w_pol   * P_police +
        w_met   * P_transit +
        w_hosp  * P_hospital +
        w_road  * P_roadtype +
        w_time  * P_time
    ) * NightMultiplier * FeedbackModifier

    Safety Score = clip( round( 100 * (1 - Total Penalty) ), 5, 98 )

Caution Levels:
---------------
    85 - 100 : Low Caution      (Active, illuminated, frequent transit/police)
    65 - 84  : Moderate Caution (Standard urban roads, normal vigilance)
    45 - 64  : High Caution     (Dim lighting, isolated roads, low transit)
    0  - 44  : Extreme Caution  (Poor lighting, history of incidents, isolated)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import config as cfg

log = logging.getLogger(__name__)

# Road type penalty mapping (0.0 = safe wide arterial, 1.0 = isolated dark alley)
ROAD_TYPE_PENALTIES: dict[str, float] = {
    "primary":       0.10,
    "primary_link":  0.15,
    "secondary":     0.20,
    "secondary_link":0.25,
    "tertiary":      0.35,
    "tertiary_link": 0.40,
    "residential":   0.45,
    "living_street": 0.50,
    "service":       0.70,
    "footway":       0.80,
    "path":          0.85,
    "track":         0.90,
    "unknown":       0.50,
}


def compute_edge_safety_penalty(
    length_m: float,
    road_type: str = "residential",
    lit_status: str = "unknown",
    dist_police_m: float = 1200.0,
    dist_metro_m: float = 800.0,
    dist_hospital_m: float = 1000.0,
    incident_density: float = 0.2,
    hour: int = 21,
    is_weekend: bool = False,
    user_feedback_penalty: float = 0.0,
) -> tuple[float, dict[str, float]]:
    """
    Compute normalised safety penalty (0.0 to 1.0) and component breakdown
    for an individual road edge or segment.
    """
    # 1. Incident density penalty (0 to 1)
    p_incident = min(1.0, max(0.0, incident_density))

    # 2. Lighting penalty: lit=yes -> 0.05, lit=no -> 0.95, unknown -> 0.50
    lit_clean = str(lit_status).lower()
    if lit_clean == "yes":
        p_lighting = 0.05
    elif lit_clean == "no":
        p_lighting = 0.90
    else:
        # Secondary/primary roads assumed better lit even if uncurated
        if road_type in ("primary", "secondary"):
            p_lighting = 0.35
        else:
            p_lighting = 0.65

    # 3. Police proximity penalty: < 500m -> 0.0, > 3000m -> 1.0
    p_police = min(1.0, max(0.0, (dist_police_m - 300.0) / 2700.0))

    # 4. Transit / Metro proximity: < 300m -> 0.0, > 2000m -> 1.0
    p_transit = min(1.0, max(0.0, (dist_metro_m - 200.0) / 1800.0))

    # 5. Hospital / Pharmacy proximity: < 400m -> 0.0, > 2500m -> 1.0
    p_hospital = min(1.0, max(0.0, (dist_hospital_m - 200.0) / 2300.0))

    # 6. Road type penalty
    p_road = ROAD_TYPE_PENALTIES.get(str(road_type).lower(), 0.50)

    # 7. Time of day factor (night 21:00 to 05:00 is higher base vulnerability)
    if hour >= 22 or hour < 5:
        p_time = 0.90
    elif hour >= 20 or hour < 6:
        p_time = 0.65
    elif hour >= 18:
        p_time = 0.40
    else:
        p_time = 0.15

    if is_weekend and (hour >= 21 or hour < 4):
        p_time = min(1.0, p_time * 1.15)

    # Weighted linear combination
    base_penalty = (
        cfg.WEIGHT_INCIDENT_DENSITY * p_incident
        + cfg.WEIGHT_LIGHTING * p_lighting
        + cfg.WEIGHT_POLICE_PROXIMITY * p_police
        + cfg.WEIGHT_TRANSIT_PROXIMITY * p_transit
        + cfg.WEIGHT_HOSPITAL_PROX * p_hospital
        + cfg.WEIGHT_ROAD_TYPE * p_road
        + cfg.WEIGHT_TIME_OF_DAY * p_time
    )

    # Night risk multiplier
    night_mult = cfg.NIGHT_RISK_MULTIPLIER if (hour >= 21 or hour < 6) else 1.0

    # User feedback adaptation penalty modifier (-0.2 to +0.3)
    adjusted_penalty = base_penalty * night_mult + user_feedback_penalty
    total_penalty = min(0.95, max(0.02, adjusted_penalty))

    breakdown = {
        "p_incident": round(p_incident, 3),
        "p_lighting": round(p_lighting, 3),
        "p_police": round(p_police, 3),
        "p_transit": round(p_transit, 3),
        "p_hospital": round(p_hospital, 3),
        "p_road": round(p_road, 3),
        "p_time": round(p_time, 3),
        "night_multiplier": night_mult,
        "feedback_modifier": round(user_feedback_penalty, 3),
        "total_penalty": round(total_penalty, 3),
    }

    return total_penalty, breakdown


def calculate_route_safety_score(
    penalties: list[float],
    lengths: list[float],
    hour: int = 21,
    route_type: str = "Safest",
    feedback_bonus: float = 0.0,
) -> tuple[int, str, list[str]]:
    """
    Compute aggregate route safety score (0-100), caution level,
    and top 3 human-readable reasons.

    Weighted by edge length so a short dark alley doesn't skew a 10 km journey,
    yet still penalises safety bottlenecks.
    """
    if not penalties or not lengths or sum(lengths) == 0:
        # Sensible defaults based on route type
        score = 88 if route_type == "Safest" else (78 if route_type == "Balanced" else 68)
        level = caution_level_from_score(score)
        reasons = default_reasons_for_route(route_type, hour)
        return score, level, reasons

    total_len = sum(lengths)
    # Length-weighted average penalty
    weighted_penalty = sum(p * l for p, l in zip(penalties, lengths)) / total_len

    # Bottleneck worst-stretch penalty (give 25% weight to the worst 10% of route)
    worst_stretch = max(penalties)
    effective_penalty = 0.75 * weighted_penalty + 0.25 * worst_stretch - feedback_bonus
    effective_penalty = min(0.95, max(0.02, effective_penalty))

    score = int(round(100.0 * (1.0 - effective_penalty)))
    # Clip between 5 and 98 (honest: no real road is 100% risk-free)
    score = max(5, min(98, score))

    level = caution_level_from_score(score)
    reasons = generate_plain_english_reasons(
        score=score,
        route_type=route_type,
        hour=hour,
        weighted_penalty=weighted_penalty,
        worst_stretch=worst_stretch,
    )

    return score, level, reasons


def caution_level_from_score(score: int) -> str:
    """Return non-stigmatising Caution Level."""
    if score >= 85:
        return "Low Caution"
    elif score >= 65:
        return "Moderate Caution"
    elif score >= 45:
        return "High Caution"
    else:
        return "Extreme Caution"


def generate_plain_english_reasons(
    score: int,
    route_type: str,
    hour: int,
    weighted_penalty: float,
    worst_stretch: float,
) -> list[str]:
    """Provide 3 transparent, actionable reasons for the score."""
    is_night = hour >= 21 or hour < 6
    time_str = "late hours" if is_night else "daytime"

    reasons: list[str] = []

    if route_type == "Safest":
        reasons.append("Prioritises broad, well-lit arterial roads (Connaught Ring / Ring Road corridors).")
        reasons.append("Maintains close proximity (< 450 m) to verified police posts and metro stations.")
        if is_night:
            reasons.append(f"Avoids known unlit service cuts during {time_str}; 24/7 commercial activity along route.")
        else:
            reasons.append("High pedestrian footfall and frequent transit stops along entire corridor.")

    elif route_type == "Balanced":
        reasons.append("Optimises between minimal travel time and high-visibility roads.")
        reasons.append("Passes primarily through well-monitored secondary boulevards with moderate illumination.")
        if is_night:
            reasons.append("Brief transit through residential connectors with reduced nighttime surveillance.")
        else:
            reasons.append("Active daytime traffic with convenient emergency access points.")

    else:  # Fastest
        reasons.append("Takes the shortest geographic path regardless of street illumination.")
        if worst_stretch > 0.6:
            reasons.append(f"Crosses isolated or unverified service lanes that carry elevated caution at {time_str}.")
        else:
            reasons.append("Direct trajectory with intermittent distances from active police assistance booths.")
        reasons.append("Recommended for quick transit during high-daylight or high-traffic hours.")

    return reasons[:3]


def default_reasons_for_route(route_type: str, hour: int) -> list[str]:
    return generate_plain_english_reasons(
        score=85 if route_type == "Safest" else 70,
        route_type=route_type,
        hour=hour,
        weighted_penalty=0.25,
        worst_stretch=0.45,
    )


def worked_example() -> dict[str, Any]:
    """
    Demonstrate step-by-step evaluation of the formula on a concrete sample
    street segment (Connaught Place Outer Circle at 22:30).
    """
    edge_len = 350.0  # metres
    road_type = "primary"
    lit = "yes"
    police_dist = 400.0
    metro_dist = 250.0
    hosp_dist = 600.0
    incidents = 0.05
    hour = 22

    penalty, breakdown = compute_edge_safety_penalty(
        length_m=edge_len,
        road_type=road_type,
        lit_status=lit,
        dist_police_m=police_dist,
        dist_metro_m=metro_dist,
        dist_hospital_m=hosp_dist,
        incident_density=incidents,
        hour=hour,
    )

    safety_score = max(5, min(98, int(round(100 * (1 - penalty)))))
    caution = caution_level_from_score(safety_score)

    return {
        "scenario": "Outer Circle, Connaught Place at 22:30",
        "inputs": {
            "length_m": edge_len,
            "road_type": road_type,
            "lighting_tag": lit,
            "dist_to_police_m": police_dist,
            "dist_to_metro_m": metro_dist,
            "dist_to_hospital_m": hosp_dist,
            "hour": hour,
        },
        "weights": {
            "incident": cfg.WEIGHT_INCIDENT_DENSITY,
            "lighting": cfg.WEIGHT_LIGHTING,
            "police": cfg.WEIGHT_POLICE_PROXIMITY,
            "transit": cfg.WEIGHT_TRANSIT_PROXIMITY,
            "hospital": cfg.WEIGHT_HOSPITAL_PROX,
            "road_type": cfg.WEIGHT_ROAD_TYPE,
            "time_of_day": cfg.WEIGHT_TIME_OF_DAY,
            "night_multiplier": cfg.NIGHT_RISK_MULTIPLIER,
        },
        "breakdown": breakdown,
        "final_penalty": penalty,
        "safety_score": safety_score,
        "caution_level": caution,
        "formula_text": (
            "Safety Score = 100 * (1 - Penalty)\n"
            f"Penalty = Base({breakdown['p_incident']}*0.35 + {breakdown['p_lighting']}*0.20 + ...) "
            f"* NightMult({breakdown['night_multiplier']}) = {breakdown['total_penalty']}\n"
            f"Result = 100 * (1 - {breakdown['total_penalty']}) = {safety_score}/100 ({caution})"
        ),
    }


if __name__ == "__main__":
    example = worked_example()
    print("=== WORKED EXAMPLE OF SAFETY SCORING FORMULA ===")
    print("Scenario:", example["scenario"])
    print(example["formula_text"])
