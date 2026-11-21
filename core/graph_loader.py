"""
core/graph_loader.py
====================
Download and cache the Delhi pilot-area road graph from OpenStreetMap.

The graph is saved as a .graphml file (XML, human-readable).
On subsequent runs the cached file is loaded in ~1 second instead of
downloading again (~30-120 s depending on connection).

This module is imported by the route engine (phase 4) and by the
graph-download script (scripts/01_download_graph.py).

Usage
-----
    from core.graph_loader import get_graph

    G = get_graph()          # returns a networkx MultiDiGraph
    print(G.number_of_nodes(), "nodes,", G.number_of_edges(), "edges")
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

import networkx as nx
import streamlit as st

import config as cfg

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_graph(force_download: bool = False) -> Optional[nx.MultiDiGraph]:
    """
    Return the cached road graph, downloading it if necessary.

    Parameters
    ----------
    force_download : Re-download even if the .graphml file already exists.

    Returns
    -------
    networkx.MultiDiGraph or None if the download fails.

    Notes
    -----
    osmnx is imported *inside* this function so that the app starts fast
    even before osmnx is installed (the import takes ~1 s on first use).
    """
    if not force_download and cfg.GRAPH_PATH.exists():
        return _load_cached()

    return _download_and_cache()


def graph_node_count(G: nx.MultiDiGraph) -> int:
    return G.number_of_nodes()


def graph_edge_count(G: nx.MultiDiGraph) -> int:
    return G.number_of_edges()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_cached() -> Optional[nx.MultiDiGraph]:
    """Load the .graphml from disk."""
    try:
        import osmnx as ox
        log.info("Loading graph from cache: %s", cfg.GRAPH_PATH)
        t0 = time.monotonic()
        G = ox.load_graphml(str(cfg.GRAPH_PATH))
        log.info(
            "Graph loaded in %.1f s  (%d nodes, %d edges)",
            time.monotonic() - t0,
            G.number_of_nodes(),
            G.number_of_edges(),
        )
        return G
    except Exception as exc:
        log.error("Failed to load cached graph: %s", exc)
        return None


def _download_and_cache() -> Optional[nx.MultiDiGraph]:
    """
    Download the drive graph for the pilot bounding box and save it.

    osmnx.graph_from_bbox downloads all drivable road geometry inside
    the box from the Overpass API (a free OSM mirror).

    Why 'drive'?  We want real road geometry for routing.  Footways are
    an add-on feature (phase 3+).
    """
    try:
        import osmnx as ox

        north, south, east, west = cfg.PILOT_BBOX
        log.info(
            "Downloading OSM graph for bbox N=%.4f S=%.4f E=%.4f W=%.4f",
            north, south, east, west,
        )
        t0 = time.monotonic()

        # network_type="drive" gets roads for cars — we also want pedestrian paths.
        # We download 'all_private=False' to skip private roads.
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

        # Add speed / travel time attributes (osmnx built-in)
        G = ox.add_edge_speeds(G)
        G = ox.add_edge_travel_times(G)

        elapsed = time.monotonic() - t0
        log.info(
            "Graph downloaded in %.1f s  (%d nodes, %d edges)",
            elapsed,
            G.number_of_nodes(),
            G.number_of_edges(),
        )

        cfg.GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
        ox.save_graphml(G, str(cfg.GRAPH_PATH))
        log.info("Graph saved to %s", cfg.GRAPH_PATH)
        return G

    except Exception as exc:
        log.error("Graph download failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Streamlit-cached wrapper (used in pages so the graph loads only once)
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Loading road graph…")
def get_graph_cached() -> Optional[nx.MultiDiGraph]:
    """
    Streamlit-cached version of get_graph().
    Call this from Streamlit pages so the graph is loaded only once per
    app restart.

    Example (inside a page):
        from core.graph_loader import get_graph_cached
        G = get_graph_cached()
        if G is None:
            st.error("Road graph not ready. Run scripts/01_download_graph.py first.")
            st.stop()
    """
    return get_graph()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    G = get_graph()
    if G:
        print(f"✅ Graph ready: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    else:
        print("❌ Graph not available")
