"""
scripts/run_checks.py
=====================
"Did I set up the project correctly?" - run this after installing
requirements. It checks your Python version, every package, the folder
structure, and your .env setup.

Run it from the project root:
    python scripts/run_checks.py

Exit code 0 = everything is ready. Exit code 1 = something is missing
(the message tells you what to do).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

# Make "import config" work even when the script is run from another folder.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

OK = "\u2705"
BAD = "\u274c"
WARN = "\u26a0\ufe0f"

# (import name, friendly name, why we need it)
PACKAGES = [
    ("streamlit", "streamlit", "web app"),
    ("streamlit_folium", "streamlit-folium", "maps inside Streamlit"),
    ("folium", "folium", "map drawing"),
    ("osmnx", "osmnx", "OSM road graph + routing"),
    ("networkx", "networkx", "shortest paths"),
    ("geopandas", "geopandas", "spatial data"),
    ("shapely", "shapely", "geometry / distances"),
    ("pyproj", "pyproj", "map projection"),
    ("pandas", "pandas", "tables"),
    ("numpy", "numpy", "numbers"),
    ("geopy", "geopy", "free geocoding"),
    ("sklearn", "scikit-learn", "risk model"),
    ("shap", "shap", "explanations"),
    ("joblib", "joblib", "save/load model"),
    ("matplotlib", "matplotlib", "charts"),
    ("sqlalchemy", "SQLAlchemy", "database"),
    ("dotenv", "python-dotenv", ".env file"),
    ("requests", "requests", "HTTP calls"),
]


def check_python() -> list[str]:
    problems = []
    major, minor = sys.version_info[:2]
    print(f"Python {major}.{minor}.{sys.version_info.micro}  ({sys.executable})")
    if (major, minor) < (3, 10):
        problems.append(
            f"Python {major}.{minor} is too old. Install Python 3.11 or 3.12."
        )
    elif (major, minor) > (3, 12):
        problems.append(
            f"Python {major}.{minor} may break shap/numba. Use 3.11 or 3.12 if "
            "you see install errors."
        )
    return problems


def check_packages() -> list[str]:
    from importlib import metadata

    problems = []
    print("\nPackages:")
    for module_name, friendly, purpose in PACKAGES:
        try:
            importlib.import_module(module_name)
            try:
                version = metadata.version(friendly)
            except metadata.PackageNotFoundError:
                version = "?"
            print(f"  {OK} {friendly:<18} {version:<10} ({purpose})")
        except Exception as exc:  # ImportError or a broken binary wheel
            print(f"  {BAD} {friendly:<18} MISSING     ({purpose})")
            problems.append(f"{friendly} failed to import: {exc.__class__.__name__}")

    # Twilio is optional, so it gets a softer message.
    try:
        importlib.import_module("twilio")
        print(f"  {OK} {'twilio':<18} {'':<10} (optional SMS)")
    except Exception:
        print(f"  {WARN} {'twilio':<18} {'':<10} (optional SMS - app still works)")
    return problems


def check_folders() -> list[str]:
    print("\nFolders:")
    problems = []
    expected = [
        "app.py",
        "config.py",
        "requirements.txt",
        "core/__init__.py",
        "core/ui.py",
        "pages",
        "scripts",
        "data/raw",
        "data/processed",
        "models",
        "tests",
    ]
    for relative in expected:
        path = PROJECT_ROOT / relative
        if path.exists():
            print(f"  {OK} {relative}")
        else:
            print(f"  {BAD} {relative} (missing)")
            problems.append(f"Missing {relative}")
    return problems


def check_config() -> list[str]:
    print("\nConfig:")
    try:
        import config as cfg
    except Exception as exc:
        print(f"  {BAD} config.py could not be imported: {exc}")
        return ["config.py import failed"]

    print(f"  {OK} project root : {cfg.PROJECT_ROOT}")
    print(f"  {OK} database     : {cfg.DB_PATH}")
    print(f"  {OK} pilot centre : {cfg.pilot_center()}")
    print(f"  {OK} twilio ready : {cfg.twilio_is_configured()}")

    if not (PROJECT_ROOT / ".env").exists():
        print(f"  {WARN} .env not found - that is fine, but copy .env.example to .env")
        print("      (Windows: Copy-Item .env.example .env | Mac: cp .env.example .env)")
    else:
        print(f"  {OK} .env found")
    return []


def check_data_files() -> None:
    """Not an error yet - data is created in Phase 2/5."""
    import config as cfg

    print("\nData files (built in later phases):")
    for label, path in [
        ("road graph", cfg.GRAPH_PATH),
        ("osm features", cfg.OSM_FEATURES_PATH),
        ("synthetic data", cfg.SYNTHETIC_DATA_PATH),
        ("risk model", cfg.RISK_MODEL_PATH),
    ]:
        mark = OK if path.exists() else "\u23f3"
        print(f"  {mark} {label:<15} {path.name}")


def main() -> int:
    print("=" * 68)
    print("MAHILA SURAKSHA MARG — setup check")
    print("=" * 68)

    problems: list[str] = []
    problems += check_python()
    problems += check_packages()
    problems += check_folders()
    problems += check_config()
    check_data_files()

    print("\n" + "=" * 68)
    if problems:
        print(f"{BAD} {len(problems)} problem(s) found:\n")
        for item in problems:
            print("  -", item)
        print("\nFix: upgrade pip, then reinstall:")
        print("  python -m pip install --upgrade pip setuptools wheel")
        print("  pip install -r requirements.txt")
        print("=" * 68)
        return 1

    print(f"{OK} Setup looks good. Start the app with:  streamlit run app.py")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
