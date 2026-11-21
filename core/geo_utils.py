"""
core/geo_utils.py
=================
Geocoding helpers that wrap geopy's free Nominatim service.

Key design choices:
- Results are cached to a JSON file so the same address is never looked
  up twice (Nominatim has a 1-request-per-second rate limit).
- If the network is unavailable the cache still works.
- Returns None instead of raising so callers can show a friendly error.

Usage:
    from core.geo_utils import geocode, distance_m

    lat, lon = geocode("Connaught Place, Delhi")
    dist = distance_m((28.63, 77.22), (28.56, 77.24))  # metres
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

import config as cfg

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory + disk cache so we never hammer Nominatim
# ---------------------------------------------------------------------------
_cache: dict[str, tuple[float, float]] = {}
_cache_path: Path = cfg.GEOCODE_CACHE_PATH
_RATE_LIMIT_SECONDS = 1.1   # Nominatim TOS: max 1 req / second


def _load_cache() -> None:
    """Load the disk cache into memory (called once at import time)."""
    global _cache
    if _cache_path.exists():
        try:
            with _cache_path.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)
            # stored as {"address": [lat, lon]}
            _cache = {k: tuple(v) for k, v in raw.items()}  # type: ignore[assignment]
            log.debug("Geocode cache loaded: %d entries", len(_cache))
        except Exception:
            log.warning("Could not read geocode cache; starting fresh.")
            _cache = {}


def _save_cache() -> None:
    """Persist the in-memory cache to disk."""
    try:
        _cache_path.parent.mkdir(parents=True, exist_ok=True)
        with _cache_path.open("w", encoding="utf-8") as fh:
            json.dump(_cache, fh, indent=2)
    except Exception as exc:
        log.warning("Could not save geocode cache: %s", exc)


_load_cache()

# One shared Nominatim instance (do NOT create one per call — it leaks sockets)
_geolocator = Nominatim(user_agent=cfg.NOMINATIM_USER_AGENT, timeout=10)
_last_request_time: float = 0.0


def geocode(address: str, city_hint: str = "Delhi, India") -> Optional[tuple[float, float]]:
    """
    Return (lat, lon) for *address*, or None on failure.

    Parameters
    ----------
    address   : Free-text address, landmark or neighbourhood.
    city_hint : Appended if the query does not already contain it, to
                bias Nominatim toward the pilot area.

    Examples
    --------
    >>> geocode("Connaught Place")
    (28.6315, 77.2167)   # approximately
    >>> geocode("Lajpat Nagar Metro")
    (28.5700, 77.2434)
    """
    # Normalise + bias
    query = address.strip()
    if city_hint.lower() not in query.lower():
        query = f"{query}, {city_hint}"

    cache_key = query.lower()
    if cache_key in _cache:
        return _cache[cache_key]

    # Fast path: prefer Google Maps, then fall back to Geoapify.
    if cfg.GOOGLE_MAPS_API_KEY:
        try:
            import requests
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            resp = requests.get(
                url,
                params={"address": query, "key": cfg.GOOGLE_MAPS_API_KEY},
                timeout=4,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "OK":
                    location = data.get("results", [{}])[0].get("geometry", {}).get("location")
                    if location:
                        coords = (float(location["lat"]), float(location["lng"]))
                        _cache[cache_key] = coords
                        _save_cache()
                        log.info("Geocoded via Google Maps API '%s' → %s", query, coords)
                        return coords
        except Exception as exc:
            log.debug("Google Maps API geocoding fell back: %s", exc)

    if cfg.MAPS_API_KEY:
        try:
            import requests
            url = "https://api.geoapify.com/v1/geocode/search"
            resp = requests.get(
                url,
                params={"text": query, "apiKey": cfg.MAPS_API_KEY, "limit": 1},
                timeout=4,
            )
            if resp.status_code == 200:
                data = resp.json()
                features = data.get("features", [])
                if features:
                    lon, lat = features[0]["geometry"]["coordinates"]
                    coords = (float(lat), float(lon))
                    _cache[cache_key] = coords
                    _save_cache()
                    log.info("Geocoded via Geoapify '%s' → %s", query, coords)
                    return coords
        except Exception as exc:
            log.debug("Geoapify geocoding fell back to Nominatim: %s", exc)

    # Respect Nominatim rate limit
    global _last_request_time
    wait = _RATE_LIMIT_SECONDS - (time.monotonic() - _last_request_time)
    if wait > 0:
        time.sleep(wait)

    try:
        _last_request_time = time.monotonic()
        location = _geolocator.geocode(query)
        if location is None:
            log.warning("Nominatim returned no result for: %s", query)
            return None
        coords: tuple[float, float] = (location.latitude, location.longitude)
        _cache[cache_key] = coords
        _save_cache()
        log.info("Geocoded '%s' → %s", query, coords)
        return coords

    except (GeocoderTimedOut, GeocoderUnavailable) as exc:
        log.error("Geocoding failed for '%s': %s", query, exc)
        return None


def geocode_or_pilot_place(address: str) -> Optional[tuple[float, float]]:
    """
    Try geocoding first; if the address matches a known pilot place
    (Connaught Place, Lajpat Nagar, etc.) return the hard-coded coords
    instead, which are always available offline.
    """
    lower = address.strip().lower()
    for place_name, coords in cfg.PILOT_PLACES.items():
        if place_name.lower() in lower:
            return coords
    return geocode(address)


def distance_m(
    point_a: tuple[float, float],
    point_b: tuple[float, float],
) -> float:
    """
    Geodesic (great-circle) distance in **metres** between two (lat, lon) points.

    Uses the WGS-84 ellipsoid via geopy — accurate to within a few cm for
    distances below 1 000 km.

    Example
    -------
    >>> distance_m((28.63, 77.22), (28.57, 77.24))
    ~6950.0
    """
    return geodesic(point_a, point_b).meters


if __name__ == "__main__":
    # Quick test: python -m core.geo_utils
    logging.basicConfig(level=logging.INFO)
    for place, expected in cfg.PILOT_PLACES.items():
        result = geocode(place)
        ok = "✅" if result else "❌"
        print(f"{ok} {place:25s}  expected≈{expected}  got={result}")
