"""
scripts/04_init_db.py
======================
Create all SQLite database tables for MAHILA SURAKSHA MARG.

This is safe to re-run: it uses CREATE TABLE IF NOT EXISTS so it will
not delete existing data.

Run from the project root:
    python scripts/04_init_db.py

Output:
    data/mahila_suraksha.db  (or wherever DB_PATH points in .env)
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

import config as cfg
from core.db import get_engine, init_db, add_report


def main() -> int:
    print("=" * 68)
    print("MAHILA SURAKSHA MARG — Phase 2: Initialise SQLite database")
    print("=" * 68)
    print(f"Database path: {cfg.DB_PATH}")
    print()

    engine = get_engine()
    init_db(engine)

    print(f"✅  Tables created (or already exist):")
    print(f"   - trusted_contacts  (SOS contacts, stored only with consent)")
    print(f"   - trip_shares       (live trip-sharing status)")
    print(f"   - community_reports (anonymous safety reports)")

    # Seed a few demo reports so the Community Reports page has something to show
    if cfg.DEMO_MODE:
        print("\nDemo mode is ON — seeding sample community reports…")
        demo_reports = [
            (28.6315, 77.2167, "poor_lighting", "Street lights not working near CP metro", 22),
            (28.6280, 77.2200, "felt_safe",     "Police patrol visible here", 20),
            (28.5677, 77.2433, "harassment",    "Auto stand with no lighting", 23),
            (28.5494, 77.2507, "isolated_area", "Underpass feels unsafe at night", 21),
            (28.5245, 77.2066, "felt_safe",     "Well lit main road", 19),
        ]
        for lat, lon, cat, desc, hour in demo_reports:
            add_report(engine, lat=lat, lon=lon, category=cat,
                       description=desc, hour_of_day=hour, is_demo=True)
        print(f"   Seeded {len(demo_reports)} demo reports.")

    print()
    print("✅  Database ready.")
    print()
    print("Phase 2 complete! All data files:")
    print(f"   Graph (after step 1) : {cfg.GRAPH_PATH.exists()} — {cfg.GRAPH_PATH.name}")
    print(f"   Safe spots (step 2)  : {cfg.SAFE_SPOTS_PATH.exists()} — {cfg.SAFE_SPOTS_PATH.name}")
    print(f"   OSM features (step 2): {cfg.OSM_FEATURES_PATH.exists()} — {cfg.OSM_FEATURES_PATH.name}")
    print(f"   Synthetic data (step 3): {cfg.SYNTHETIC_DATA_PATH.exists()} — {cfg.SYNTHETIC_DATA_PATH.name}")
    print(f"   Database (step 4)    : {cfg.DB_PATH.exists()} — {cfg.DB_PATH.name}")
    print()
    print("Next step:  Phase 3 — Safety scoring module")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
