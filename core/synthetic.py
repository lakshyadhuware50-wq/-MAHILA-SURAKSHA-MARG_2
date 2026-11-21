"""
core/synthetic.py
=================
The actual synthetic incident generator logic — importable by both
scripts/03_generate_synthetic_data.py AND the test suite.

See scripts/03_generate_synthetic_data.py for the full documented rationale
on why the Kaggle datasets cannot be used as street-level truth and how
their patterns DO calibrate this generator.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config as cfg

# ---------------------------------------------------------------------------
# Road-type distribution for synthetic incidents
# ---------------------------------------------------------------------------
ROAD_TYPE_PROBS = {
    "primary":     0.10,
    "secondary":   0.18,
    "residential": 0.40,
    "footway":     0.17,
    "service":     0.15,
}

_WEEKDAY_WEIGHTS = [1.0, 1.0, 1.0, 1.0, 1.1, 1.3, 1.1]  # Mon-Sun

NORTH, SOUTH, EAST, WEST = cfg.PILOT_BBOX


def generate_synthetic_incidents(n: int | None = None) -> pd.DataFrame:
    """
    Generate n synthetic incident rows inside PILOT_BBOX.

    Parameters
    ----------
    n : Number of rows. Defaults to config.SYNTHETIC_N_INCIDENTS.

    Returns
    -------
    pd.DataFrame with columns:
        lat, lon, hour_of_day, day_of_week, incident_type,
        near_isolated_lane, near_low_lighting, dist_to_police_m,
        dist_to_metro_m, dist_to_hospital_m, road_type,
        risk_factors_sum, risk_label, is_synthetic

    Risk labelling (documented for transparency)
    --------------------------------------------
    risk_label = 1 when risk_factors_sum >= 3, where factors are:
      +1 if hour has weight > 1.2  (late night / early morning)
      +1 if near_isolated_lane = 1
      +1 if near_low_lighting = 1
      +1 if dist_to_police_m  > 2000
      +1 if dist_to_metro_m   > 1500
      +1 if road_type in (footway, service)
      +1 if day_of_week in (4=Fri, 5=Sat)
    """
    if n is None:
        n = cfg.SYNTHETIC_N_INCIDENTS

    rng = np.random.default_rng(cfg.SYNTHETIC_RANDOM_SEED)

    # Spatial
    lats = rng.uniform(SOUTH, NORTH, n)
    lons = rng.uniform(WEST, EAST, n)

    # Time
    hour_weights = np.array(cfg.HOUR_RISK_WEIGHTS, dtype=float)
    hour_weights /= hour_weights.sum()
    hours = rng.choice(np.arange(24), size=n, p=hour_weights)

    day_weights = np.array(_WEEKDAY_WEIGHTS, dtype=float) / sum(_WEEKDAY_WEIGHTS)
    days = rng.choice(np.arange(7), size=n, p=day_weights)

    # Incident type
    types  = list(cfg.INCIDENT_TYPES.keys())
    tprobs = np.array(list(cfg.INCIDENT_TYPES.values()), dtype=float)
    tprobs /= tprobs.sum()
    incident_types = rng.choice(types, size=n, p=tprobs)

    # Environmental
    near_isolated  = rng.binomial(1, 0.35, n).astype(bool)
    near_low_light = rng.binomial(1, 0.40, n).astype(bool)
    dist_police    = np.clip(rng.gamma(shape=2.5, scale=600, size=n), 100, 8000)
    dist_metro     = np.clip(rng.gamma(shape=2.0, scale=550, size=n), 50, 6000)
    dist_hospital  = np.clip(rng.gamma(shape=2.5, scale=500, size=n), 100, 7000)

    road_types_list = list(ROAD_TYPE_PROBS.keys())
    road_probs = np.array(list(ROAD_TYPE_PROBS.values()), dtype=float)
    road_probs /= road_probs.sum()
    road_types = rng.choice(road_types_list, size=n, p=road_probs)

    # Risk factors
    hour_high_risk = hour_weights[hours] > (1.2 / 24)
    risk_factors = (
        hour_high_risk.astype(int)
        + near_isolated.astype(int)
        + near_low_light.astype(int)
        + (dist_police > 2000).astype(int)
        + (dist_metro > 1500).astype(int)
        + np.isin(road_types, ["footway", "service"]).astype(int)
        + np.isin(days, [4, 5]).astype(int)
    )
    risk_label = (risk_factors >= 3).astype(int)

    return pd.DataFrame({
        "lat":               lats,
        "lon":               lons,
        "hour_of_day":       hours,
        "day_of_week":       days,
        "incident_type":     incident_types,
        "near_isolated_lane": near_isolated.astype(int),
        "near_low_lighting":  near_low_light.astype(int),
        "dist_to_police_m":   dist_police.round(1),
        "dist_to_metro_m":    dist_metro.round(1),
        "dist_to_hospital_m": dist_hospital.round(1),
        "road_type":          road_types,
        "risk_factors_sum":   risk_factors,
        "risk_label":         risk_label,
        "is_synthetic":       True,
    })
