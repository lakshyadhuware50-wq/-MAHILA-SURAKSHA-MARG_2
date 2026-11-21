"""
scripts/02_fetch_osm_features.py
=================================
Download safety-relevant OSM features (police stations, hospitals,
pharmacies, metro stations, bus stops, lit roads) for the Delhi pilot
area and save them to data/processed/.

This is a one-time setup step. Run after 01_download_graph.py.

Run from the project root:
    python scripts/02_fetch_osm_features.py

Output:
    data/processed/safe_spots.geojson   – police/hospital/pharmacy/metro
    data/processed/osm_features.geojson – lit/unlit road segments

Time: 30-90 seconds (5 Overpass requests, 2-second pause between each).
No API key required.
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
from core.osm_features import build_osm_features


def main() -> int:
    print("=" * 68)
    print("MAHILA SURAKSHA MARG — Phase 2: Fetch OSM safety features")
    print("=" * 68)
    print(f"Pilot area : {cfg.AREA_LABEL}")
    print()

    force = False
    if cfg.SAFE_SPOTS_PATH.exists() or cfg.OSM_FEATURES_PATH.exists():
        answer = input(
            "⚠️  Some feature files already exist. Re-download? [y/N] "
        ).strip().lower()
        force = answer == "y"
        if not force:
            print("Using existing files.")

    print("Querying Overpass API (please wait ~60 seconds)…")
    print("  Categories: police, hospital, pharmacy, metro, bus_stop, lit roads")
    print()

    try:
        result = build_osm_features(force=force)
    except Exception as exc:
        print(f"\n❌  Failed: {exc}")
        print(
            "\nCommon causes:\n"
            "  - No internet connection\n"
            "  - Overpass API overloaded — wait 5 min and retry\n"
        )
        return 1

    spots  = result.get("safe_spots")
    lit    = result.get("lit_roads")

    print("\n✅  Done!")
    if spots is not None and len(spots) > 0:
        print(f"   Safe spots: {len(spots):,} features")
        counts = spots["category"].value_counts()
        for cat, n in counts.items():
            print(f"      {cat:15s}: {n}")
        print(f"   File: {cfg.SAFE_SPOTS_PATH}")
    else:
        print("   ⚠️  No safe spots found — Overpass may be unreachable or area is too small.")

    if lit is not None and len(lit) > 0:
        print(f"\n   Lit roads: {len(lit):,} tagged segments")
        print(f"   File: {cfg.OSM_FEATURES_PATH}")
    else:
        print("\n   ⚠️  No lit-road data — will use neutral lighting score (0.5).")

    print()
    print("Next step:  python scripts/03_generate_synthetic_data.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
