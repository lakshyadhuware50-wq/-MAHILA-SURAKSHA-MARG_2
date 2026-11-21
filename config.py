"""
config.py
=========
One single place for every path, setting and secret used by
MAHILA SURAKSHA MARG.

Why one file?
- A beginner only has to look here to change the pilot area, a file
  location, or an API key.
- Every other module does `import config as cfg` and reuses these values,
  so nothing is hard-coded twice.

How to use:
    import config as cfg
    print(cfg.DISCLAIMER)
    print(cfg.GRAPH_PATH)

Nothing here needs an API key. Twilio keys are optional (see .env.example).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------
# 1. Project paths
# ---------------------------------------------------------------------
# Path(__file__) is the location of THIS file, so paths keep working no
# matter which folder you run the app from.
PROJECT_ROOT = Path(__file__).resolve().parent

# Read .env if it exists. If it does not exist, the app still runs and
# simply has no Twilio credentials.
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR       = PROJECT_ROOT / "data"
RAW_DIR        = DATA_DIR / "raw"               # Kaggle or other raw downloads
PROCESSED_DIR  = DATA_DIR / "processed"         # graphml, features, synthetic CSV
EXTERNAL_DIR   = DATA_DIR / "external"          # optional manual downloads
MODEL_DIR      = PROJECT_ROOT / "models"        # trained .joblib models
DOCS_DIR       = PROJECT_ROOT / "docs"

# Create the folders on first import so no script ever crashes on a
# missing directory.
for _folder in (DATA_DIR, RAW_DIR, PROCESSED_DIR, EXTERNAL_DIR, MODEL_DIR, DOCS_DIR):
    _folder.mkdir(parents=True, exist_ok=True)


def _project_path(value: str, default: Path) -> Path:
    """Turn a value from .env into an absolute path inside the project."""
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


# ---------------------------------------------------------------------
# 2. Data files (created by the scripts in scripts/)
# ---------------------------------------------------------------------
GRAPH_PATH          = PROCESSED_DIR / "delhi_pilot.graphml"         # phase 2
OSM_FEATURES_PATH   = PROCESSED_DIR / "osm_features.geojson"        # phase 2
SAFE_SPOTS_PATH     = PROCESSED_DIR / "safe_spots.geojson"          # phase 2/7
SYNTHETIC_DATA_PATH = PROCESSED_DIR / "synthetic_incidents.csv"     # phase 2
ADVANCED_TRAINING_DATA_PATH = PROCESSED_DIR / "delhi_advanced_training_12000.csv"  # 12,000 synthetic Delhi corridor rows
NLP_REPORTS_DATA_PATH       = PROCESSED_DIR / "delhi_nlp_reports_synthetic_1800.csv" # 1,800 synthetic English/Hinglish reports
RISK_MODEL_PATH     = MODEL_DIR / "risk_model.joblib"               # phase 5
RISK_MODEL_METRICS  = MODEL_DIR / "risk_model_metrics.json"         # phase 5
NLP_MODEL_PATH      = MODEL_DIR / "nlp_filter_model.joblib"
NLP_MODEL_METRICS   = MODEL_DIR / "nlp_model_metrics.json"
DB_PATH = _project_path(os.getenv("DB_PATH", ""), DATA_DIR / "mahila_suraksha.db")

# ---------------------------------------------------------------------
# 3. Pilot area (Delhi-NCR)
# ---------------------------------------------------------------------
# Change these values to expand the project later.
# Format: (north, south, east, west) — the order osmnx expects.
PILOT_BBOX = (28.650, 28.500, 77.280, 77.170)

PILOT_PLACES = {
    "Connaught Place": (28.6315, 77.2167),
    "Lajpat Nagar":   (28.5677, 77.2433),
    "Nehru Place":    (28.5494, 77.2507),
    "Saket":          (28.5245, 77.2066),
}

CITY_NAME  = "Delhi"
AREA_LABEL = "Connaught Place / Lajpat Nagar / Nehru Place / Saket (pilot zone)"

# ---------------------------------------------------------------------
# 4. Demo / prototype mode
# ---------------------------------------------------------------------
# Set DEMO_MODE = True here (or DEMO_MODE=1 in .env) to show a banner
# on every page, suppress real Twilio sends, and label reports as demo.
_demo_env = os.getenv("DEMO_MODE", "0").strip()
DEMO_MODE: bool = _demo_env in ("1", "true", "yes", "True")

DEMO_BANNER = (
    "⚠️ PROTOTYPE / DEMO DATA — This is a student project using "
    "computer-generated (synthetic) safety data. It is not a real "
    "safety service. Always call 112 in an emergency."
)

# ---------------------------------------------------------------------
# 5. Responsible-design text (shown on EVERY results page)
# ---------------------------------------------------------------------
DISCLAIMER = (
    "Safer does not mean safe. This supports, not replaces, 112 and "
    "official services."
)

SYNTHETIC_DATA_NOTICE = (
    "🧪 Risk scores come from a SYNTHETIC (computer-generated) training "
    "dataset, not real crime records. They are for a student project and "
    "must not be treated as a factual statement about any place or person."
)

HELPLINES = [
    # (label, number, description)
    ("Police / all emergencies",  "112",  "One number for police, fire and ambulance."),
    ("Women Helpline (Delhi)",    "1091", "Delhi Police women's helpline."),
    ("Women Helpline (national)", "181",  "National women's helpline."),
]

# ---------------------------------------------------------------------
# 6. Community reports: spam limits + time decay (phase 8)
# ---------------------------------------------------------------------
MAX_REPORTS_PER_SESSION_PER_HOUR = 5    # simple per-browser-session rate limit
REPORT_DECAY_HALF_LIFE_DAYS      = 90   # weight halves every 90 days
MIN_REPORT_CLASSIFIER_CONFIDENCE = 0.5  # below this, report is flagged as spam

# ---------------------------------------------------------------------
# 7. Optional Twilio SMS (no-key fallback still works)
# ---------------------------------------------------------------------
TWILIO_ACCOUNT_SID   = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_AUTH_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_FROM_NUMBER   = os.getenv("TWILIO_FROM_NUMBER", "").strip()
TWILIO_TO_NUMBER     = os.getenv("TWILIO_TO_NUMBER", "").strip()


def twilio_is_configured() -> bool:
    """True only when all three required Twilio values are present in .env."""
    return all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER])


# ---------------------------------------------------------------------
# 8. Maps & Geocoding APIs (Google / Geoapify / Nominatim)
# ---------------------------------------------------------------------
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
MAPS_API_KEY = os.getenv("MAPS_API_KEY", "").strip()

# Nominatim asks every client to identify itself; a generic user-agent
# can get throttled.  Put your own contact string in .env.
NOMINATIM_USER_AGENT = os.getenv(
    "NOMINATIM_USER_AGENT",
    "mahila-suraksha-marg/1.0 (student project)",
)
GEOCODE_CACHE_PATH = PROCESSED_DIR / "geocode_cache.json"


def get_map_tile_layer() -> tuple[str, str | None]:
    """
    Returns (tiles_param, attribution).
    Uses Geoapify Dark Matter Purple roads if MAPS_API_KEY is present,
    otherwise CartoDB dark_matter.
    """
    if MAPS_API_KEY:
        tile_url = f"https://maps.geoapify.com/v1/tile/dark-matter-purple-roads/{{z}}/{{x}}/{{y}}.png?apiKey={MAPS_API_KEY}"
        attribution = 'Powered by <a href="https://www.geoapify.com/" target="_blank">Geoapify</a> | &copy; OpenStreetMap'
        return tile_url, attribution
    return "CartoDB dark_matter", None


# ---------------------------------------------------------------------
# 9. App settings
# ---------------------------------------------------------------------
APP_TITLE          = "MAHILA SURAKSHA MARG"
APP_SUBTITLE       = "AI-powered women's safety route advisor for Delhi-NCR"
APP_ICON           = "🛡️"
MAP_ZOOM_START     = 12
DEFAULT_TRAVEL_HOUR = 21   # 9 PM — the high-risk hour (makes the demo compelling)

# PWA (Add-to-Home-Screen) metadata written into the Streamlit HTML head
PWA_SHORT_NAME   = "MahilaMarg"
PWA_THEME_COLOR  = "#BB86FC"   # Electric lavender / purple for dark mode
PWA_BG_COLOR     = "#0E1117"

# ---------------------------------------------------------------------
# 10. Safety-score formula weights (phase 3 uses these)
# ---------------------------------------------------------------------
# These are intentionally surfaced here so a researcher can tune them
# in one place without touching the formula code.
WEIGHT_INCIDENT_DENSITY = 0.35   # nearby historical incidents (time-decayed)
WEIGHT_LIGHTING         = 0.20   # street-lighting (lit=yes/no OSM tag)
WEIGHT_POLICE_PROXIMITY = 0.15   # distance to nearest police station
WEIGHT_TRANSIT_PROXIMITY= 0.10   # distance to metro / bus
WEIGHT_HOSPITAL_PROX    = 0.08   # distance to hospital or pharmacy
WEIGHT_ROAD_TYPE        = 0.07   # primary/secondary/residential/footway
WEIGHT_TIME_OF_DAY      = 0.05   # day (06-21) vs night (21-06) multiplier

# night multiplier applied on top of the base score (06-21 = 1.0, else 1.3)
NIGHT_RISK_MULTIPLIER = 1.30     # 30 % higher risk weight after 9 PM

# ---------------------------------------------------------------------
# 11. Synthetic data generation parameters (phase 2 calibration)
# ---------------------------------------------------------------------
# These numbers are informed by published Delhi NCRB summaries
# (city/state level aggregates — NOT street-level ground truth).
SYNTHETIC_N_INCIDENTS   = 5_000  # number of rows to generate
SYNTHETIC_RANDOM_SEED   = 42

# Hour-of-day risk weights (index 0 = midnight, 23 = 11 PM)
# Source: published patterns in NCRB reports + transport research literature
HOUR_RISK_WEIGHTS = [
    1.8, 2.0, 2.0, 1.9, 1.5, 0.9,  # 00-05
    0.5, 0.4, 0.4, 0.4, 0.4, 0.4,  # 06-11
    0.4, 0.4, 0.4, 0.5, 0.6, 0.8,  # 12-17
    1.0, 1.2, 1.5, 1.7, 1.8, 1.8,  # 18-23
]

# Crime-type mix (approximate, from published Delhi NCRB summaries)
INCIDENT_TYPES = {
    "harassment":       0.38,
    "stalking":         0.18,
    "poor_lighting":    0.14,
    "isolated_area":    0.12,
    "eve_teasing":      0.10,
    "unsafe_transport": 0.08,
}


# ---------------------------------------------------------------------
# 12. Helper functions
# ---------------------------------------------------------------------
def pilot_center() -> tuple[float, float]:
    """Return the (lat, lon) centre of the pilot box, for centring maps."""
    north, south, east, west = PILOT_BBOX
    return ((north + south) / 2, (east + west) / 2)


if __name__ == "__main__":
    # Quick manual check:  python config.py
    print("Project root  :", PROJECT_ROOT)
    print("Database      :", DB_PATH)
    print("Graph file    :", GRAPH_PATH)
    print("Pilot centre  :", pilot_center())
    print("Twilio ready  :", twilio_is_configured())
    print("Demo mode     :", DEMO_MODE)
    print("App title     :", APP_TITLE)
