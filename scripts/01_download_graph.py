"""
scripts/01_download_graph.py
============================
Download the Delhi pilot-area road graph from OpenStreetMap and save it
as data/processed/delhi_pilot.graphml.

This is a one-time setup step. After it finishes the app works offline.

Run from the project root:
    python scripts/01_download_graph.py

Expected output:
    Downloading OSM graph for the pilot area...
    ✅ Graph saved: 12 345 nodes, 28 901 edges
    File: data/processed/delhi_pilot.graphml  (~ 15 MB)

Time: 30-120 seconds on a typical broadband connection.
Requires: osmnx (which calls the Overpass API — free, no key needed).
"""

from __future__ import annotations

import sys
import time
import logging
from pathlib import Path

# ---------------------------------------------------------------------------
# Make "import config" work when run as a script
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

import config as cfg


def main() -> int:
    print("=" * 68)
    print("MAHILA SURAKSHA MARG — Phase 2: Download OSM graph")
    print("=" * 68)
    print(f"Pilot area : {cfg.AREA_LABEL}")
    print(f"Bounding box (N,S,E,W): {cfg.PILOT_BBOX}")
    print(f"Output file: {cfg.GRAPH_PATH}")
    print()

    if cfg.GRAPH_PATH.exists():
        answer = input(
            f"⚠️  Graph file already exists ({cfg.GRAPH_PATH.stat().st_size // 1024} KB). "
            "Re-download? [y/N] "
        ).strip().lower()
        if answer != "y":
            print("Skipped. Using existing file.")
            return 0

    try:
        import osmnx as ox
    except ImportError:
        print("❌  osmnx not found. Run:  pip install osmnx")
        return 1

    north, south, east, west = cfg.PILOT_BBOX
    print(f"Calling Overpass API … this takes 30-120 seconds …")
    t0 = time.monotonic()

    try:
        # osmnx 2.x uses bbox=(west, south, east, north); osmnx 1.x uses north, south, east, west
        try:
            G = ox.graph_from_bbox(
                bbox=(west, south, east, north),
                network_type="drive",
                retain_all=False,
                truncate_by_edge=True,
                simplify=True,
            )
        except TypeError:
            G = ox.graph_from_bbox(
                north=north,
                south=south,
                east=east,
                west=west,
                network_type="drive",
                retain_all=False,
                truncate_by_edge=True,
                simplify=True,
            )
    except Exception as exc:
        print(f"\n❌  Graph download failed: {exc}")
        print(
            "\nCommon causes:\n"
            "  - No internet connection\n"
            "  - Overpass API is temporarily overloaded (try again in 5 min)\n"
            "  - The bounding box is too large (reduce PILOT_BBOX in config.py)\n"
        )
        return 1

    # Enrich edges with speed and travel-time attributes
    print("Calculating edge speeds and travel times…")
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)

    elapsed = time.monotonic() - t0
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()

    print(f"\n✅  Graph downloaded in {elapsed:.0f} s")
    print(f"   Nodes : {n_nodes:,}")
    print(f"   Edges : {n_edges:,}")

    # Save
    cfg.GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nSaving to {cfg.GRAPH_PATH} …")
    ox.save_graphml(G, str(cfg.GRAPH_PATH))
    size_kb = cfg.GRAPH_PATH.stat().st_size // 1024
    print(f"✅  Saved ({size_kb:,} KB)")
    print()
    print("Next step:  python scripts/02_fetch_osm_features.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
