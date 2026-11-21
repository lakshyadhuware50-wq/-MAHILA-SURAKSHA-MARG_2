"""
core/osm_features.py
====================
Fetch safety-relevant features from OpenStreetMap via the Overpass API
and save them as GeoJSON files.

Features extracted:
  - Street lighting  (highway=* + lit=yes/no)
  - Police stations  (amenity=police)
  - Hospitals        (amenity=hospital)
  - Pharmacies       (amenity=pharmacy)
  - Metro stations   (railway=station OR station=subway)
  - Bus stops        (highway=bus_stop)

All results are cached as GeoJSON in data/processed/ so the app works
offline after the first download.

Usage
-----
    from core.osm_features import (
        load_safe_spots,
        get_lighting_index,
        nearest_feature_distance,
    )

    spots = load_safe_spots()          # GeoDataFrame of police/hospital/metro
    lit   = get_lighting_index(G)      # dict edge_id -> 0.0 or 1.0
    d     = nearest_feature_distance(lat, lon, spots, "police")  # metres
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Point

import config as cfg

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Overpass API endpoint (free, no key)
# ---------------------------------------------------------------------------
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# A polite delay between successive Overpass requests (seconds)
_REQUEST_DELAY = 2.0


def _overpass_query(query: str, retries: int = 3) -> dict:
    """
    POST a query to the Overpass API and return the parsed JSON.
    Retries up to `retries` times on network errors.
    """
    for attempt in range(retries):
        try:
            resp = requests.post(
                OVERPASS_URL,
                data={"data": query},
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            log.warning("Overpass attempt %d/%d failed: %s", attempt + 1, retries, exc)
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
    raise RuntimeError("Overpass API unreachable after retries")


def _bbox_filter() -> str:
    """Return an Overpass bounding-box filter for the pilot area."""
    north, south, east, west = cfg.PILOT_BBOX
    return f"({south},{west},{north},{east})"


# ---------------------------------------------------------------------------
# 1. Fetch individual feature layers
# ---------------------------------------------------------------------------

def fetch_police_stations() -> gpd.GeoDataFrame:
    """Return GeoDataFrame of police stations in the pilot area."""
    bbox = _bbox_filter()
    query = f"""
    [out:json][timeout:60];
    (
      node["amenity"="police"]{bbox};
      way["amenity"="police"]{bbox};
    );
    out center;
    """
    data = _overpass_query(query)
    return _elements_to_gdf(data["elements"], category="police")


def fetch_hospitals() -> gpd.GeoDataFrame:
    """Return GeoDataFrame of hospitals in the pilot area."""
    bbox = _bbox_filter()
    query = f"""
    [out:json][timeout:60];
    (
      node["amenity"="hospital"]{bbox};
      way["amenity"="hospital"]{bbox};
    );
    out center;
    """
    data = _overpass_query(query)
    return _elements_to_gdf(data["elements"], category="hospital")


def fetch_pharmacies() -> gpd.GeoDataFrame:
    """Return GeoDataFrame of pharmacies in the pilot area."""
    bbox = _bbox_filter()
    query = f"""
    [out:json][timeout:60];
    (
      node["amenity"="pharmacy"]{bbox};
      way["amenity"="pharmacy"]{bbox};
    );
    out center;
    """
    data = _overpass_query(query)
    return _elements_to_gdf(data["elements"], category="pharmacy")


def fetch_fire_stations() -> gpd.GeoDataFrame:
    """Return GeoDataFrame of fire stations in the pilot area."""
    bbox = _bbox_filter()
    query = f"""
    [out:json][timeout:60];
    (
      node["amenity"="fire_station"]{bbox};
      way["amenity"="fire_station"]{bbox};
    );
    out center;
    """
    data = _overpass_query(query)
    return _elements_to_gdf(data["elements"], category="fire_station")


def fetch_metro_stations() -> gpd.GeoDataFrame:
    """Return GeoDataFrame of metro/subway stations in the pilot area."""
    bbox = _bbox_filter()
    query = f"""
    [out:json][timeout:60];
    (
      node["railway"="station"]{bbox};
      node["station"="subway"]{bbox};
      node["railway"="subway_entrance"]{bbox};
    );
    out;
    """
    data = _overpass_query(query)
    return _elements_to_gdf(data["elements"], category="metro")


def fetch_bus_stops() -> gpd.GeoDataFrame:
    """Return GeoDataFrame of bus stops in the pilot area."""
    bbox = _bbox_filter()
    query = f"""
    [out:json][timeout:60];
    (
      node["highway"="bus_stop"]{bbox};
    );
    out;
    """
    data = _overpass_query(query)
    return _elements_to_gdf(data["elements"], category="bus_stop")


def fetch_lit_roads() -> gpd.GeoDataFrame:
    """
    Return GeoDataFrame of road segments tagged lit=yes or lit=no.

    OSM tagging is sparse — most roads have no lit tag at all.
    We treat "no tag" as "unknown" (not the same as unlit).
    """
    bbox = _bbox_filter()
    query = f"""
    [out:json][timeout:90];
    (
      way["highway"]["lit"]{bbox};
    );
    out geom;
    """
    data = _overpass_query(query)
    rows = []
    for el in data.get("elements", []):
        if el["type"] != "way":
            continue
        tags = el.get("tags", {})
        # centroid of the way's nodes
        geometry = el.get("geometry", [])
        if not geometry:
            continue
        lats = [pt["lat"] for pt in geometry]
        lons = [pt["lon"] for pt in geometry]
        lat = sum(lats) / len(lats)
        lon = sum(lons) / len(lons)
        rows.append({
            "osm_id":   el["id"],
            "category": "road",
            "lit":      tags.get("lit", "unknown"),
            "highway":  tags.get("highway", ""),
            "name":     tags.get("name", ""),
            "lat":      lat,
            "lon":      lon,
            "geometry": Point(lon, lat),
        })
    if not rows:
        return gpd.GeoDataFrame(columns=["osm_id", "category", "lit", "highway",
                                          "name", "lat", "lon", "geometry"],
                                 crs="EPSG:4326")
    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    return gdf


# ---------------------------------------------------------------------------
# 2. Build and save the combined "safe spots" layer
# ---------------------------------------------------------------------------

def build_safe_spots(force: bool = False) -> gpd.GeoDataFrame:
    """
    Download police, hospital, pharmacy and metro layers, combine them,
    and save to data/processed/safe_spots.geojson.

    Parameters
    ----------
    force : Re-download even if the file already exists.

    Returns
    -------
    GeoDataFrame with columns: category, name, lat, lon, geometry
    """
    if not force and cfg.SAFE_SPOTS_PATH.exists():
        log.info("Loading safe spots from cache: %s", cfg.SAFE_SPOTS_PATH)
        return gpd.read_file(str(cfg.SAFE_SPOTS_PATH))

    log.info("Downloading safe spots from Overpass API…")
    parts: list[gpd.GeoDataFrame] = []

    fetchers = [
        ("police", fetch_police_stations),
        ("hospital", fetch_hospitals),
        ("pharmacy", fetch_pharmacies),
        ("fire_station", fetch_fire_stations),
        ("metro", fetch_metro_stations),
        ("bus_stop", fetch_bus_stops),
    ]

    for category, fn in fetchers:
        log.info("  Fetching %s…", category)
        try:
            gdf = fn()
            log.info("    → %d features", len(gdf))
            parts.append(gdf)
            time.sleep(_REQUEST_DELAY)
        except Exception as exc:
            log.warning("  Could not fetch %s: %s", category, exc)

    if not parts:
        log.warning("No safe spots downloaded — Overpass may be unreachable.")
        return gpd.GeoDataFrame(crs="EPSG:4326")

    combined = gpd.GeoDataFrame(
        pd.concat(parts, ignore_index=True),
        crs="EPSG:4326",
    )
    # Keep only the essential columns
    keep = [c for c in ["osm_id", "category", "name", "lat", "lon", "geometry"]
            if c in combined.columns]
    combined = combined[keep]

    cfg.SAFE_SPOTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.to_file(str(cfg.SAFE_SPOTS_PATH), driver="GeoJSON")
    log.info("Safe spots saved: %d features → %s", len(combined), cfg.SAFE_SPOTS_PATH)
    return combined


def build_osm_features(force: bool = False) -> dict:
    """
    Build and save the full OSM features file (lit roads + safe spots).

    Returns a dict with keys 'safe_spots' and 'lit_roads'.
    """
    result = {}

    # Safe spots (police / hospital / pharmacy / metro)
    result["safe_spots"] = build_safe_spots(force=force)

    # Lit roads (for edge weights in phase 3)
    if force or not cfg.OSM_FEATURES_PATH.exists():
        log.info("Fetching lit road data…")
        try:
            time.sleep(_REQUEST_DELAY)
            lit = fetch_lit_roads()
            lit.to_file(str(cfg.OSM_FEATURES_PATH), driver="GeoJSON")
            log.info("OSM features saved: %d lit-road segments → %s",
                     len(lit), cfg.OSM_FEATURES_PATH)
            result["lit_roads"] = lit
        except Exception as exc:
            log.warning("Could not fetch lit roads: %s", exc)
            result["lit_roads"] = gpd.GeoDataFrame(crs="EPSG:4326")
    else:
        result["lit_roads"] = gpd.read_file(str(cfg.OSM_FEATURES_PATH))

    return result


# ---------------------------------------------------------------------------
# 3. Query helpers (used by the scoring engine in phase 3)
# ---------------------------------------------------------------------------

def load_safe_spots() -> Optional[gpd.GeoDataFrame]:
    """
    Load the cached safe-spots GeoDataFrame, or None if not yet built.
    Call build_safe_spots() first (via scripts/02_fetch_osm_features.py).
    """
    if not cfg.SAFE_SPOTS_PATH.exists():
        return None
    return gpd.read_file(str(cfg.SAFE_SPOTS_PATH))


def nearest_feature_distance(
    lat: float,
    lon: float,
    spots: gpd.GeoDataFrame,
    category: Optional[str] = None,
) -> float:
    """
    Return the distance in metres from (lat, lon) to the nearest feature
    in *spots*.

    Parameters
    ----------
    lat, lon : Query point.
    spots    : GeoDataFrame from load_safe_spots().
    category : If given, filter to only that category (e.g. 'police').

    Returns
    -------
    Distance in metres, or 9999 if no features found.
    """
    if spots is None or len(spots) == 0:
        return 9999.0

    subset = spots if category is None else spots[spots["category"] == category]
    if len(subset) == 0:
        return 9999.0

    # Project to a metric CRS for distance calculation
    point_wgs = gpd.GeoDataFrame(
        [{"geometry": Point(lon, lat)}], crs="EPSG:4326"
    )
    # Use UTM zone 43N — good for Delhi
    proj_crs = "EPSG:32643"
    subset_m = subset.to_crs(proj_crs)
    point_m  = point_wgs.to_crs(proj_crs)

    distances = subset_m.geometry.distance(point_m.geometry.iloc[0])
    return float(distances.min())


def get_lighting_index(lat: float, lon: float, radius_m: float = 150.0) -> float:
    """
    Return a lighting score 0–1 for the area near (lat, lon).

    1.0 = well-lit (lit=yes tags within radius_m metres)
    0.0 = unlit or no data

    If the OSM features file has not been built yet, returns 0.5 (neutral).
    """
    if not cfg.OSM_FEATURES_PATH.exists():
        return 0.5  # neutral when data is missing

    try:
        lit_gdf = gpd.read_file(str(cfg.OSM_FEATURES_PATH))
        if len(lit_gdf) == 0:
            return 0.5

        point = gpd.GeoDataFrame(
            [{"geometry": Point(lon, lat)}], crs="EPSG:4326"
        ).to_crs("EPSG:32643")

        lit_m = lit_gdf.to_crs("EPSG:32643")
        nearby = lit_m[lit_m.geometry.distance(point.geometry.iloc[0]) <= radius_m]

        if len(nearby) == 0:
            return 0.5  # no data nearby → neutral

        n_lit   = (nearby.get("lit", pd.Series(dtype=str)) == "yes").sum()
        n_unlit = (nearby.get("lit", pd.Series(dtype=str)) == "no").sum()

        if n_lit + n_unlit == 0:
            return 0.5
        return float(n_lit / (n_lit + n_unlit))

    except Exception as exc:
        log.warning("get_lighting_index failed: %s", exc)
        return 0.5


# ---------------------------------------------------------------------------
# 4. Internal helper
# ---------------------------------------------------------------------------

def _elements_to_gdf(elements: list, category: str) -> gpd.GeoDataFrame:
    """Convert a list of Overpass JSON elements to a GeoDataFrame."""
    rows = []
    for el in elements:
        # Nodes have lat/lon directly; ways have a "center" field
        if el["type"] == "node":
            lat, lon = el["lat"], el["lon"]
        elif el["type"] == "way" and "center" in el:
            lat, lon = el["center"]["lat"], el["center"]["lon"]
        else:
            continue

        tags = el.get("tags", {})
        rows.append({
            "osm_id":   el["id"],
            "category": category,
            "name":     tags.get("name", ""),
            "lat":      lat,
            "lon":      lon,
            "geometry": Point(lon, lat),
        })

    if not rows:
        return gpd.GeoDataFrame(
            columns=["osm_id", "category", "name", "lat", "lon", "geometry"],
            crs="EPSG:4326",
        )
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = build_osm_features(force=False)
    spots = result.get("safe_spots", gpd.GeoDataFrame())
    print(f"Safe spots: {len(spots)} features")
    if len(spots) > 0:
        print(spots["category"].value_counts().to_string())
