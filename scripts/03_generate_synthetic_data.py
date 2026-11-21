"""
scripts/03_generate_synthetic_data.py
======================================
Generate a clearly labelled SYNTHETIC street-level incident dataset for
the Delhi pilot area.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HONEST DISCLAIMER (printed before every run, shown in the UI)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The Kaggle datasets in archive/ are:
  - crime_statistics_district_annual.csv  — NCRB district-level rape FIR counts
                                            (2015-2022, state/UT level, NOT street)
  - crime_statistics_state_annual.csv     — State-level NCRB counts
  - CRIME_DETAILS.csv                     — State-level multi-crime totals (2001-2021)

WHAT THEY HAVE:   State/district, year, case count.
WHAT THEY LACK:   Street coordinates, time-of-day, location type, lighting.
CONCLUSION:       They cannot be used as street-level truth.

HOW WE USE THEM:
  1. Hour-of-day pattern  → from transport safety research literature
     (consistent with NCRB pattern analysis in CHRI Part 3 report)
  2. Incident-type mix    → approximate shares from NCRB "Head of Crime" tables
  3. Delhi relative rate  → Delhi tends to record 2-5× the national avg per 100k
     (this is used only to set the density of synthetic points)

The resulting CSV is labelled "is_synthetic=True" in every row and shown
with a warning banner in the app.  It is a student project, NOT a factual
statement about any place or person.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Output columns
--------------
  lat, lon            – random point inside PILOT_BBOX (uniform spatial prior,
                        then reweighted by proximity to roads, isolation, lighting)
  hour_of_day         – 0-23, sampled from HOUR_RISK_WEIGHTS
  day_of_week         – 0=Mon … 6=Sun, slightly higher risk on Fri/Sat nights
  incident_type       – from INCIDENT_TYPES dict in config.py
  near_isolated_lane  – 1 if far from main roads (synthetic flag)
  near_low_lighting   – 1 if area tagged as unlit (synthetic)
  dist_to_police_m    – synthetic distance in metres (Gamma-distributed)
  dist_to_metro_m     – synthetic distance in metres
  dist_to_hospital_m  – synthetic distance in metres
  road_type           – primary/secondary/residential/footway/service
  risk_label          – 0 (low risk) or 1 (high risk) — for model training
  is_synthetic        – always True (never hide this)

Run:
    python scripts/03_generate_synthetic_data.py
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

import numpy as np
import pandas as pd

import config as cfg
from core.synthetic import generate_synthetic_incidents


N = cfg.SYNTHETIC_N_INCIDENTS

# ---------------------------------------------------------------------------
# Helper: load Delhi NCRB data for calibration notes
# ---------------------------------------------------------------------------

def _load_kaggle_summary() -> str:
    """
    Read the Kaggle CSVs and return a human-readable calibration note.
    This is printed to the console for transparency — it does NOT affect
    the generated coordinates or risk labels.
    """
    lines = ["=== Kaggle dataset inspection ==="]

    # 1. District-level NCRB
    district_path = PROJECT_ROOT.parent.parent / "archive" / "crime_statistics_district_annual.csv"
    if district_path.exists():
        try:
            df = pd.read_csv(district_path)
            lines.append(f"\n[1] crime_statistics_district_annual.csv")
            lines.append(f"    Columns : {list(df.columns)}")
            lines.append(f"    Shape   : {df.shape}")
            delhi = df[df["state_ut"].str.upper().str.contains("DELHI", na=False)]
            if len(delhi) > 0:
                lines.append(f"    Delhi rows: {len(delhi)}")
                lines.append(f"    Delhi years: {sorted(delhi['year'].unique())}")
                lines.append(f"    Delhi case range: {delhi['cases_registered'].min()}-"
                             f"{delhi['cases_registered'].max()}")
            lines.append(f"    ⚠ No street coordinates — DISTRICT LEVEL ONLY")
        except Exception as exc:
            lines.append(f"    Could not read: {exc}")
    else:
        lines.append(f"\n[1] district file not found at {district_path}")

    # 2. CRIME_DETAILS.csv
    details_path = PROJECT_ROOT.parent.parent / "archive (1)" / "CRIME_DETAILS.csv"
    if details_path.exists():
        try:
            df2 = pd.read_csv(details_path)
            lines.append(f"\n[2] CRIME_DETAILS.csv")
            lines.append(f"    Columns : {list(df2.columns)}")
            lines.append(f"    Shape   : {df2.shape}")
            lines.append(f"    Years   : {sorted(df2['Year'].unique())}")
            lines.append(f"    ⚠ No street coordinates — STATE LEVEL ONLY")
        except Exception as exc:
            lines.append(f"    Could not read: {exc}")
    else:
        lines.append(f"\n[2] CRIME_DETAILS.csv not found at {details_path}")

    lines.append("\nCONCLUSION: Datasets are state/district aggregates.")
    lines.append("They calibrate HOUR/TYPE patterns only — NOT used as street-level truth.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def generate_synthetic_incidents(n: int = N) -> pd.DataFrame:
    """
    Generate n synthetic incident rows inside PILOT_BBOX.

    Risk labelling logic (documented here for transparency):
    --------------------------------------------------------
    A point is labelled high-risk (risk_label=1) if it has 3 or more of:
      - Hour of day has risk weight > 1.2  (late night or early morning)
      - near_isolated_lane = 1
      - near_low_lighting  = 1
      - dist_to_police_m   > 2000 m
      - dist_to_metro_m    > 1500 m
      - road_type in ('footway', 'service')
      - day_of_week in (4, 5)   (Friday or Saturday)

    This is a heuristic, not a learned rule. The ML model (phase 5) will
    learn a better decision boundary from these same features.
    """
    # ----- Spatial coordinates (uniform within bbox) ---------------------
    lats = RNG.uniform(SOUTH, NORTH, n)
    lons = RNG.uniform(WEST,  EAST,  n)

    # ----- Time features --------------------------------------------------
    hour_weights = np.array(cfg.HOUR_RISK_WEIGHTS)
    hour_weights = hour_weights / hour_weights.sum()
    hours = RNG.choice(np.arange(24), size=n, p=hour_weights)

    day_weights = np.array(_WEEKDAY_WEIGHTS) / sum(_WEEKDAY_WEIGHTS)
    days = RNG.choice(np.arange(7), size=n, p=day_weights)

    # ----- Incident type --------------------------------------------------
    types  = list(cfg.INCIDENT_TYPES.keys())
    tprobs = np.array(list(cfg.INCIDENT_TYPES.values()))
    tprobs = tprobs / tprobs.sum()
    incident_types = RNG.choice(types, size=n, p=tprobs)

    # ----- Environmental features (synthetic) ----------------------------
    # Isolated lane: higher probability in residential/footway areas
    near_isolated = RNG.binomial(1, 0.35, n).astype(bool)

    # Lighting: 40% of points in pilot area have no or poor lighting
    near_low_light = RNG.binomial(1, 0.40, n).astype(bool)

    # Distance to nearest police station (Gamma: most are 1-3 km away)
    dist_police = RNG.gamma(shape=2.5, scale=600, size=n)       # metres
    dist_police = np.clip(dist_police, 100, 8000)

    # Distance to nearest metro station (Gamma: most are 0.5-2 km)
    dist_metro  = RNG.gamma(shape=2.0, scale=550, size=n)
    dist_metro  = np.clip(dist_metro, 50, 6000)

    # Distance to nearest hospital/pharmacy
    dist_hospital = RNG.gamma(shape=2.5, scale=500, size=n)
    dist_hospital = np.clip(dist_hospital, 100, 7000)

    # Road type
    road_types_list = list(ROAD_TYPE_PROBS.keys())
    road_probs      = np.array(list(ROAD_TYPE_PROBS.values()))
    road_probs      = road_probs / road_probs.sum()
    road_types      = RNG.choice(road_types_list, size=n, p=road_probs)

    # ----- Risk label (heuristic sum of risk factors) --------------------
    hour_high_risk = (hour_weights * 24)[hours] > (1.2 / 24)   # vectorized check

    risk_factors = (
        hour_high_risk.astype(int)
        + near_isolated.astype(int)
        + near_low_light.astype(int)
        + (dist_police   > 2000).astype(int)
        + (dist_metro    > 1500).astype(int)
        + np.isin(road_types, ["footway", "service"]).astype(int)
        + np.isin(days, [4, 5]).astype(int)
    )
    risk_label = (risk_factors >= 3).astype(int)

    # ----- Assemble DataFrame --------------------------------------------
    df = pd.DataFrame({
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

    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 68)
    print("MAHILA SURAKSHA MARG — Phase 2: Generate Synthetic Incident Data")
    print("=" * 68)
    print()

    # Print Kaggle inspection
    print(_load_kaggle_summary())
    print()

    if cfg.SYNTHETIC_DATA_PATH.exists():
        answer = input(
            f"⚠️  Synthetic data already exists "
            f"({cfg.SYNTHETIC_DATA_PATH.stat().st_size // 1024} KB). "
            "Regenerate? [y/N] "
        ).strip().lower()
        if answer != "y":
            print("Skipped.")
            return 0

    print(f"\nGenerating {N:,} synthetic incidents (seed={cfg.SYNTHETIC_RANDOM_SEED})…")
    from core.synthetic import generate_synthetic_incidents
    df = generate_synthetic_incidents(N)

    # Print summary statistics
    print(f"\n--- Summary ---")
    print(f"  Shape   : {df.shape}")
    print(f"  High-risk rows (label=1): {df['risk_label'].sum():,}  "
          f"({df['risk_label'].mean()*100:.1f}%)")
    print(f"  Incident types:")
    for t, c in df["incident_type"].value_counts().items():
        print(f"    {t:25s}: {c:5,}  ({c/N*100:.1f}%)")
    print(f"  Hour distribution (high-risk hours 21-05):")
    night = df[df["hour_of_day"].isin(range(21, 24)) | df["hour_of_day"].isin(range(0, 6))]
    day_  = df[~df.index.isin(night.index)]
    print(f"    Night (21-05): {len(night):,}  ({len(night)/N*100:.1f}%)")
    print(f"    Day   (06-20): {len(day_):,}  ({len(day_)/N*100:.1f}%)")

    # Save
    cfg.SYNTHETIC_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(str(cfg.SYNTHETIC_DATA_PATH), index=False)
    size_kb = cfg.SYNTHETIC_DATA_PATH.stat().st_size // 1024
    print(f"\n✅  Saved {N:,} rows → {cfg.SYNTHETIC_DATA_PATH}  ({size_kb} KB)")
    print()
    print("Next step:  python scripts/04_init_db.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
